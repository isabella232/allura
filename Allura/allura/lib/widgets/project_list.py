from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals
#       Licensed to the Apache Software Foundation (ASF) under one
#       or more contributor license agreements.  See the NOTICE file
#       distributed with this work for additional information
#       regarding copyright ownership.  The ASF licenses this file
#       to you under the Apache License, Version 2.0 (the
#       "License"); you may not use this file except in compliance
#       with the License.  You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing,
#       software distributed under the License is distributed on an
#       "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#       KIND, either express or implied.  See the License for the
#       specific language governing permissions and limitations
#       under the License.

import ew as ew_core
import ew.jinja2_ew as ew

from pylons import tmpl_context as c
from paste.deploy.converters import asbool

from allura import model as M
from allura.lib.security import Credentials


class ProjectSummary(ew_core.Widget):
    template = 'jinja:allura:templates/widgets/project_summary.html'
    defaults = dict(
        ew_core.Widget.defaults,
        sitemap=None,
        icon=None,
        value=None,
        icon_url=None,
        accolades=None,
        columns=1,
        show_proj_icon=True,
        show_download_button=True,
        show_awards_banner=True,
        grid_view_tools='')

    def prepare_context(self, context):
        response = super(ProjectSummary, self).prepare_context(context)
        value = response['value']
        if response['sitemap'] is None:
            response['sitemap'] = [s for s in value.sitemap() if s.url]

        if response['grid_view_tools'] != '':
            view_tools_list = response['grid_view_tools'].split(',')
            icon_tool_list = ["tool-%s" % vt.lower() for vt in view_tools_list]
            old_sitemap = response['sitemap']
            response['sitemap'] = []
            for sm in old_sitemap:
                if sm.ui_icon is not None and sm.ui_icon.lower() in icon_tool_list:
                    response['sitemap'].append(sm)

        if response['icon_url'] is None:
            if value.icon:
                response['icon_url'] = value.url() + 'icon'
        if response['accolades'] is None:
            response['accolades'] = value.accolades

        if type(response['columns']) == str:
            response['columns'] = int(response['columns'])

        true_list = ['true', 't', '1', 'yes', 'y']
        if type(response['show_proj_icon']) == str:
            if response['show_proj_icon'].lower() in true_list:
                response['show_proj_icon'] = True
            else:
                response['show_proj_icon'] = False
        if type(response['show_download_button']) == str:
            if response['show_download_button'].lower() in true_list:
                response['show_download_button'] = True
            else:
                response['show_download_button'] = False
        if type(response['show_awards_banner']) == str:
            if response['show_awards_banner'].lower() in true_list:
                response['show_awards_banner'] = True
            else:
                response['show_awards_banner'] = False

        return response


class ProjectList(ew_core.Widget):
    template = 'jinja:allura:templates/widgets/project_list_widget.html'
    defaults = dict(
        ew_core.Widget.defaults,
        projects=[],
        project_summary=ProjectSummary(),
        display_mode='list',
        sitemaps=None,
        icon_urls=None,
        accolades_index=None,
        columns=1,
        show_proj_icon=True,
        show_download_button=True,
        show_awards_banner=True,
        grid_view_tools='')

    def prepare_context(self, context):
        response = super(ProjectList, self).prepare_context(context)
        cred = Credentials.get()
        projects = response['projects']
        cred.load_user_roles(c.user._id, *[p._id for p in projects])
        cred.load_project_roles(*[p._id for p in projects])

        for opt in ['show_proj_icon', 'show_download_button', 'show_awards_banner']:
            response[opt] = asbool(response[opt])

        if response['sitemaps'] is None and response['display_mode'] != 'list':
            response['sitemaps'] = M.Project.menus(projects)
        if response['icon_urls'] is None and response['show_proj_icon']:
            response['icon_urls'] = M.Project.icon_urls(projects)
        if response['accolades_index'] is None and response['show_awards_banner']:
            response['accolades_index'] = M.Project.accolades_index(projects)

        if type(response['columns']) == str:
            response['columns'] = int(response['columns'])

        return response

    def resources(self):
        for r in self.project_summary.resources():
            yield r


class ProjectScreenshots(ew_core.Widget):
    template = 'jinja:allura:templates/widgets/project_screenshots.html'
    defaults = dict(
        ew_core.Widget.defaults,
        project=None,
        edit=False,
        draggable=False)

    def resources(self):
        yield ew.JSLink('js/screenshots.js')
        yield ew.CSSLink('css/screenshots.css')
