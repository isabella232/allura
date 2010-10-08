import os
import re
os.environ['HGRCPATH'] = '' # disable loading .hgrc
import stat
import shutil
import errno
import string
import logging
import subprocess
import email as EM
from collections import defaultdict
from hashlib import sha1
from datetime import datetime
from cStringIO import StringIO
from itertools import islice

import tg
from mercurial import ui, hg

from ming.base import Object
from ming.orm import MappedClass, FieldProperty, session
from ming.utils import LazyProperty

from allura import model as M
from allura.lib import helpers as h
from allura.model.repository import topological_sort

log = logging.getLogger(__name__)

class HgRepository(M.Repository):
    repo_id='hg'
    type_s='Hg Repository'
    class __mongometa__:
        name='hg-repository'
    branches = FieldProperty([dict(name=str,object_id=str)])

    def __init__(self, **kw):
        super(HgRepository, self).__init__(**kw)
        self._impl = HgImplementation(self)

    def log(self, branch='default', offset=0, limit=10):
        return super(HgRepository, self).log(branch, offset, limit)

class HgImplementation(M.RepositoryImplementation):
    post_receive_template = string.Template(
        '\n[hooks]\n'
        'changegroup = curl -s $url\n')
    re_hg_user = re.compile('(.*) <(.*)>')

    def __init__(self, repo):
        self._repo = repo

    @LazyProperty
    def _hg(self):
        return hg.repository(ui.ui(), self._repo.full_fs_path)

    def init(self):
        fullname = self._setup_paths()
        log.info('hg init %s', fullname)
        if os.path.exists(fullname):
            shutil.rmtree(fullname)
        repo = hg.repository(
            ui.ui(), self._repo.full_fs_path, create=True)
        self.__dict__['_hg'] = repo
        self._setup_special_files()
        self._repo.status = 'ready'

    def clone_from(self, source_path):
        '''Initialize a repo as a clone of another'''
        fullname = self._setup_paths(create_repo_dir=False)
        if os.path.exists(fullname):
            shutil.rmtree(fullname)
        log.info('Initialize %r as a clone of %s',
                 self._repo, source_path)
        repo = hg.repository(
            ui.ui(), self._repo.full_fs_path, create=True)
        self.__dict__['_hg'] = repo
        repo.clone(source_path)
        self._setup_special_files()
        self._repo.status = 'analyzing'
        session(self._repo).flush()
        log.info('... %r cloned, analyzing', self._repo)
        self._repo.refresh()
        self._repo.status = 'ready'
        log.info('... %s ready', self._repo)
        session(self._repo).flush()

    def commit(self, rev):
        result = M.Commit.query.get(repo_id='hg', object_id=rev)
        if result is None:
            impl = self._hg[str(rev)]
            result = M.Commit.query.get(repo_id='hg', object_id=impl.hex())
        if result is None: return None
        result.set_context(self._repo)
        return result

    def new_commits(self):
        graph = {}
        to_visit = [ self._hg[hd.object_id] for hd in self._repo.heads ]
        while to_visit:
            obj = to_visit.pop()
            if obj.hex() in graph: continue
            graph[obj.hex()] = set(
                p.hex() for p in obj.parents()
                if p.hex() != obj.hex())
            to_visit += obj.parents()
        return [
            oid for oid in topological_sort(graph)
            if M.Commit.query.find(dict(repo_id='hg', object_id=oid)).count() == 0 ]

    def commit_context(self, commit):
        prev_ids = commit.parent_ids
        prev = M.Commit.query.find(dict(
                repo_id='hg',
                object_id={'$in':prev_ids})).all()
        next = M.Commit.query.find(dict(
                repo_id='hg',
                parent_ids=commit.object_id,
                repositories=self._repo._id)).all()
        for ci in prev + next:
            ci.set_context(self._repo)
        return dict(prev=prev, next=next)

    def refresh_heads(self):
        self._repo.heads = [
            Object(name=None, object_id=self._hg[head].hex())
            for head in self._hg.heads() ]
        self._repo.branches = [
            Object(name=name, object_id=self._hg[tag].hex())
            for name, tag in self._hg.branchtags().iteritems() ]
        self._repo.repo_tags = [
            Object(name=name, object_id=self._hg[tag].hex())
            for name, tag in self._hg.tags().iteritems() ]
        session(self._repo).flush()

    def refresh_commit(self, ci):
        log.info('Refresh %r', ci)
        obj = self._hg[ci.object_id]
        # Save commit metadata
        mo = self.re_hg_user.match(obj.user())
        if mo:
            user_name, user_email = mo.groups()
        else:
            user_name = user_email = obj.user()
        ci.committed = Object(
            name=user_name,
            email=user_email,
            date=datetime.fromtimestamp(sum(obj.date())))
        ci.authored=Object(ci.committed)
        ci.message=obj.description() or ''
        ci.parent_ids=[
            p.hex() for p in obj.parents()
            if p.hex() != obj.hex() ]
        # Save commit tree (must build a fake git-like tree from the changectx)
        fake_tree = self._tree_from_changectx(obj)
        ci.tree_id = fake_tree.hex()
        tree, isnew = M.Tree.upsert('hg', fake_tree.hex())
        if isnew:
            tree.set_context(ci)
            tree.set_last_commit(ci)
            self._refresh_tree(tree, fake_tree)

    def log(self, object_id, skip, count):
        obj = self._hg[object_id]
        candidates = [ obj ]
        result = []
        seen = set()
        while count and candidates:
            obj = candidates.pop(0)
            if obj.hex() in seen: continue
            seen.add(obj.hex())
            if skip == 0:
                result.append(obj.hex())
                count -= 1
            else:
                skip -= 1
            candidates += obj.parents()
        return result, [ p.hex() for p in candidates ]

    def open_blob(self, blob):
        fctx = self._hg[blob.commit.object_id][blob.path()[1:]]
        return StringIO(fctx.data())

    def _setup_receive_hook(self):
        'Set up the hg changegroup hook'
        text = self.post_receive_template.substitute(
            url=tg.config.get('base_url', 'localhost:8080')
            + self._repo.url()[1:] + 'refresh')
        fn = os.path.join(self._repo.fs_path, self._repo.name, '.hg', 'hgrc')
        with open(fn, 'ab') as fp:
            fp.write(text)
        os.chmod(fn, 0755)

    def _tree_from_changectx(self, changectx):
        '''Build a fake git-like tree from a changectx and its manifest'''
        class TreeNode(object):
            def __init__(self):
                self.blobs = {}
                self.trees = defaultdict(TreeNode)
                self._hex = None
            def hex(self):
                if self._hex is None:
                    sha_obj = sha1(repr(self))
                    self._hex = sha_obj.hexdigest()
                return self._hex
            def __repr__(self):
                lines = [('t %s %s' % (t.hex(), name))
                          for name, t in self.trees.iteritems() ]
                lines += [('b %s %s' % (oid, name))
                          for name, oid in self.blobs.iteritems() ]
                return '\n'.join(sorted(lines))
        def _bin2hex(binsha):
            return ''.join('%.2x' % ord(x) for x in binsha)
        root = TreeNode()
        for filepath in changectx.manifest():
            path_parts = filepath.split('/')
            dirpath, filename = path_parts[:-1], path_parts[-1]
            cur = root
            for part in dirpath:
                cur = cur.trees[part]
            # This doesn't work
            fctx = changectx[filepath]
            cur.blobs[filename] = sha1(fctx.data()).hexdigest()
        return root

    def _refresh_tree(self, tree, obj):
        tree.trees=Object(
            (o.hex(), name)
            for name, o in obj.trees.iteritems())
        tree.blobs=Object(
            (oid, name)
            for name, oid in obj.blobs.iteritems())
        for name, o in obj.trees.iteritems():
            subtree, isnew = M.Tree.upsert('hg', o.hex())
            if isnew:
                subtree.set_context(tree, name)
                subtree.set_last_commit(tree.commit)
                self._refresh_tree(subtree, o)
        for name, oid in obj.blobs.iteritems():
            blob, isnew = M.Blob.upsert('hg', oid)
            if isnew:
                blob.set_context(tree, name)
                blob.set_last_commit(tree.commit)

MappedClass.compile_all()
