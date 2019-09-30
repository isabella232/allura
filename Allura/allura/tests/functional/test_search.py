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
from mock import patch

from allura.tests import TestController
from allura.tests.decorators import with_tool


class TestSearch(TestController):

    @patch('allura.lib.search.search')
    def test_global_search_controller(self, search):
        self.app.get('/search/')
        assert not search.called, search.called
        self.app.get('/search/', params=dict(q='Root'))
        assert search.called, search.called

    # use test2 project since 'test' project has a subproject and MockSOLR can't handle "OR" (caused by subproject)
    @with_tool('test2', 'Wiki', 'wiki')
    def test_project_search_controller(self):
        self.app.get('/p/test2/search/')
        resp = self.app.get('/p/test2/search/', params=dict(q='wiki'))
        resp.mustcontain('Welcome to your wiki! This is the default page')
