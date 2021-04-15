'''This module is added for testing the files model '''
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

from __future__ import unicode_literals
from __future__ import absolute_import
from nose.tools import assert_equal, assert_true, assert_false

from forgefiles.tests.model import FilesTestWithModel
from forgefiles.model.files import UploadFolder
from forgefiles.model.files import UploadFiles



class TestUpload(FilesTestWithModel):
    ''' Test class for UploadFolder & uploadFiles model'''

    def test_upload_folder(self):
        '''Creates an object of the UploadFolder Collction and tests its fields'''
        upload_folder = UploadFolder
        upload_folder.folder_name = 'testFolder'
        upload_folder.published = True
        upload_folder.remark = 'Publishing new Version'
        upload_folder.disabled = False
        assert_equal(upload_folder.folder_name, 'testFolder')
        assert_true(upload_folder.published)
        assert_equal(upload_folder.remark, 'Publishing new Version')
        assert_false(upload_folder.disabled)

    def test_upload_file(self):
        '''Creates an object of the UploadFiles Collction and tests its fields'''

        upload_file = UploadFiles
        upload_file.filename = 'testFile'
        upload_file.filetype = 'project_file'
        upload_file.file_url = 'TestFolder/testFile'
        upload_file.linked_to_download = True
        upload_file.published = False
        assert_equal(upload_file.filename, 'testFile')
        assert_equal(upload_file.filetype, 'project_file')
        assert_true(upload_file.linked_to_download)
        assert_false(upload_file.published)
