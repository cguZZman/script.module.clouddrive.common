import unittest
import urllib.parse
from unittest import mock

import kodistubs
from clouddrive.common.remote.provider import Provider
from clouddrive.common.ui.addon import CloudDriveAddon
from clouddrive.common.ui.utils import KodiUtils

kodistubs.use_temp_profile()


class FakeProvider(Provider):
    folder_paging_supported = True

    def __init__(self, pages):
        super(FakeProvider, self).__init__('fake')
        self.pages = pages
        self.calls = []

    def configure(self, account_manager, driveid):
        pass

    def cancel_operation(self):
        return False

    def get_folder_page(self, item_driveid=None, item_id=None, path=None, page_size=500, page_token=None, on_items_page_completed=None):
        self.calls.append(('page', item_id, page_size, page_token))
        return self.pages[page_token]

    def get_folder_items(self, item_driveid=None, item_id=None, path=None, on_items_page_completed=None, include_download_info=False, on_before_add_item=None):
        self.calls.append(('all', item_id))
        items = []
        token = None
        while True:
            page, token = self.pages[token]
            items.extend(page)
            if not token:
                return items


def item(item_id, **extra):
    i = {'id': item_id, 'name': item_id + '.jpg', 'name_extension': 'jpg', 'size': 1, 'last_modified_date': '2026-10-01T10:00:00Z'}
    i.update(extra)
    return i


class Addon(CloudDriveAddon):
    # Built without the constructor, which needs Kodi: nothing to release.
    def __del__(self):
        pass


class ListingTest(unittest.TestCase):
    PAGES = {None: ([item('a'), item('folder', folder={'child_count': 1})], 'next'), 'next': ([item('b')], None)}

    def setUp(self):
        self.settings = {'page_size': '500'}
        self.cache_minutes = 5
        patches = [mock.patch.object(KodiUtils, 'get_addon_setting', side_effect=lambda setting_id, addonid=None: self.settings.get(setting_id, '')),
                   mock.patch.object(KodiUtils, 'get_cache_expiration_time', side_effect=lambda addonid=None: self.cache_minutes)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.provider = FakeProvider(self.PAGES)
        # One cache database for every test: each one lists its own drive.
        self.drive = 'drive-' + self._testMethodName

    def list_folder(self, **params):
        addon = object.__new__(Addon)
        addon._addonid = 'test'
        addon._addon_url = 'plugin://test/'
        addon._content_type = 'image'
        addon._child_count_supported = False
        addon._account_manager = None
        addon._progress_dialog_bg = mock.MagicMock()
        addon._cancel_operation = False
        addon.cancel_operation = lambda: False
        addon.get_provider = lambda: self.provider
        shown = {}
        addon._process_items = lambda items, driveid, next_page_url=None: shown.update(items=[i['id'] for i in items], next=next_page_url)
        addon._list_folder(self.drive, item_id='f', **params)
        return shown

    def next_page_params(self, url):
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))

    def test_big_folders_are_listed_a_page_at_a_time(self):
        shown = self.list_folder()
        self.assertEqual(shown['items'], ['a', 'folder'])
        self.assertEqual(self.provider.calls, [('page', 'f', 500, None)])
        params = self.next_page_params(shown['next'])
        self.assertEqual((params['action'], params['item_id'], params['page_token'], params['driveid']), ('_list_folder', 'f', 'next', self.drive))
        shown = self.list_folder(page_token='next')
        self.assertEqual((shown['items'], shown['next']), (['b'], None))

    def test_page_size_is_a_setting(self):
        self.settings['page_size'] = '100'
        self.list_folder()
        self.assertEqual(self.provider.calls, [('page', 'f', 100, None)])

    def test_page_size_zero_lists_the_whole_folder(self):
        self.settings['page_size'] = '0'
        shown = self.list_folder()
        self.assertEqual((shown['items'], shown['next']), (['a', 'folder', 'b'], None))
        self.assertEqual(self.provider.calls, [('all', 'f')])

    def test_providers_without_pages_list_the_whole_folder(self):
        self.provider.folder_paging_supported = False
        self.assertEqual(self.list_folder()['items'], ['a', 'folder', 'b'])

    def test_going_back_to_a_folder_uses_the_cache(self):
        first = self.list_folder()
        self.assertEqual(self.list_folder(), first)
        self.assertEqual(len(self.provider.calls), 1)
        self.list_folder(page_token='next')
        self.assertEqual(len(self.provider.calls), 2, 'each page is cached on its own')

    def test_cache_time_zero_always_lists(self):
        self.cache_minutes = 0
        self.list_folder()
        self.list_folder()
        self.assertEqual(len(self.provider.calls), 2)

    def test_slideshow_lists_whole_and_fresh(self):
        self.list_folder()
        shown = self.list_folder(fresh='true')
        self.assertEqual((shown['items'], shown['next']), (['a', 'folder', 'b'], None))
        self.assertEqual(self.provider.calls[-1], ('all', 'f'))


class NextPageItemTest(unittest.TestCase):
    def process(self, fresh=False, next_page_url=None):
        addon = object.__new__(Addon)
        addon._addon_url = 'plugin://test/'
        addon._content_type = 'image'
        addon._addon_handle = 1
        addon._common_addon = kodistubs.FakeAddon()
        addon._fresh_listing = fresh
        addon._auto_refreshed_slideshow_supported = False
        addon._image_file_extensions = ['jpg']
        addon._get_item_play_url = lambda *args: 'plugin://test/?action=play'
        with mock.patch('clouddrive.common.ui.addon.xbmcplugin') as xbmcplugin, mock.patch('clouddrive.common.ui.addon.xbmcgui') as xbmcgui:
            xbmcgui.ListItem.side_effect = lambda label: mock.MagicMock(label=label)
            addon._process_items([item('folder', folder={'child_count': 1}), item('a')], 'drive', next_page_url)
        return xbmcplugin.addDirectoryItems.call_args[0][1]

    def test_next_page_is_the_last_item(self):
        listing = self.process(next_page_url='plugin://test/?page_token=next')
        url, list_item, is_folder = listing[-1]
        self.assertEqual((url, list_item.label, is_folder), ('plugin://test/?page_token=next', '#32094', True))
        list_item.setProperty.assert_called_with('SpecialSort', 'bottom')
        self.assertEqual(len(self.process()), 2)

    def test_slideshow_subfolders_are_listed_fresh(self):
        folder_url = self.process(fresh=True)[0][0]
        self.assertEqual(self.next_params(folder_url).get('fresh'), 'true')
        self.assertNotIn('fresh', self.next_params(self.process()[0][0]))

    def next_params(self, url):
        return dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))


if __name__ == '__main__':
    unittest.main()


class ExportsMenuTest(unittest.TestCase):
    EXPORTS = {'e1': {'id': 'e1', 'name': 'Movies', 'driveid': 'kept', 'item_driveid': 'kept', 'content_type': 'video'},
               'e2': {'id': 'e2', 'name': 'Old', 'driveid': 'removed', 'item_driveid': 'removed', 'content_type': 'video'},
               'e3': {'id': 'e3', 'name': 'Music', 'driveid': 'removed', 'item_driveid': 'removed', 'content_type': 'audio'}}

    def addon(self, content_type='video'):
        addon = object.__new__(Addon)
        addon._addon_url = 'plugin://test/'
        addon._content_type = content_type
        addon._addon_handle = 1
        addon._profile_path = '/profile'
        addon._common_addon = kodistubs.FakeAddon()
        addon._account_manager = mock.MagicMock()
        addon._account_manager.get_accounts.return_value = {'a': {'id': 'a', 'drives': [{'id': 'kept'}]}}
        addon._get_display_name = lambda account, drive=None, with_format=False: 'User'
        addon.cancel_operation = lambda: False
        return addon

    def run(self, result=None):
        with mock.patch('clouddrive.common.ui.addon.ExportManager') as manager:
            manager.return_value.get_exports.return_value = self.EXPORTS
            with mock.patch('clouddrive.common.ui.addon.xbmcplugin') as self.xbmcplugin, mock.patch('clouddrive.common.ui.addon.xbmcgui') as xbmcgui:
                xbmcgui.ListItem.side_effect = lambda label: mock.MagicMock(label=label)
                return super(ExportsMenuTest, self).run(result)

    def listing(self):
        return [(item.label, dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))) for url, item, *rest in self.xbmcplugin.addDirectoryItems.call_args[0][1]]

    def test_exports_of_removed_accounts_can_be_removed(self):
        addon = self.addon()
        addon.list_accounts()
        labels = [label for label, params in self.listing()]
        self.assertEqual(labels, ['User', '#32096', '#32005'])
        addon._list_exports()
        [(label, params)] = self.listing()
        self.assertEqual((label, params['action'], params['item_id']), ('Old', '_remove_export', 'e2'))

    def test_no_entry_without_removed_accounts(self):
        addon = self.addon()
        addon._account_manager.get_accounts.return_value['b'] = {'id': 'b', 'drives': [{'id': 'removed'}]}
        addon.list_accounts()
        self.assertNotIn('#32096', [label for label, params in self.listing()])

    def test_drives_without_their_own_folders_have_the_menu(self):
        for content_type, labels in (('video', ['[B]#32052[/B]', '#32000', '#32039']), ('image', ['[B]#32052[/B]', '#32039'])):
            addon = self.addon(content_type)
            addon.get_custom_drive_folders = lambda driveid: []
            addon._list_drive('kept')
            self.assertEqual([label for label, params in self.listing()], labels)
