import unittest
from unittest import mock

import kodistubs  # noqa: F401
from clouddrive.common.service.source import Source
from clouddrive.common.ui.utils import KodiUtils


class SourceRedirectTest(unittest.TestCase):
    def source(self, item):
        s = Source.__new__(Source)  # No HTTP request: only the URL logic is tested.
        s._addonid = 'plugin.googledrive'
        s.path = '/source/Google%20Drive/me/Movies/My%20Movie.mkv'
        s.get_item = lambda driveid, path: item
        return s

    def test_files_go_through_the_local_download_service(self):
        item = {'id': 'f1', 'name': 'My Movie.mkv', 'download_info': {'url': 'https://www.googleapis.com/drive/v3/files/f1?alt=media'}}
        with mock.patch.object(KodiUtils, 'get_service_port', staticmethod(lambda service, addonid=None: {('download', 'plugin.googledrive'): '8588'}[(service, addonid)])):
            url = self.source(item).get_download_url('me', '/Movies/My Movie.mkv')
        self.assertEqual(url, 'http://127.0.0.1:8588/download/me/me/f1/My%20Movie.mkv')
        self.assertNotIn('googleapis', url)

    def test_items_of_another_drive_keep_their_drive(self):
        item = {'id': 'f2', 'name': 'a.mp4', 'drive_id': 'shared', 'download_info': {'url': 'x'}}
        with mock.patch.object(KodiUtils, 'get_service_port', staticmethod(lambda service, addonid=None: '8588')):
            self.assertEqual(self.source(item).get_download_url('me', '/a.mp4'), 'http://127.0.0.1:8588/download/me/shared/f2/a.mp4')

    def test_folders_redirect_to_their_listing(self):
        self.assertEqual(self.source({'id': 'd', 'name': 'Movies', 'folder': {}}).get_download_url('me', '/Movies'), '/source/Google%20Drive/me/Movies/My%20Movie.mkv/')
