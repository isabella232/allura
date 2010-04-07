from urllib import urlencode

from tg import config
from nose.tools import assert_true

from forgetracker.tests import TestController

class TestRootController(TestController):

    def test_index(self):
        response = self.app.get('/tickets/')
        assert_true('ForgeTracker for' in response)
