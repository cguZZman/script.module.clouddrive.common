import unittest
from unittest import mock

import kodistubs
from clouddrive.common.redaction import redact
from clouddrive.common.ui.addon import CloudDriveAddon
from clouddrive.common.utils import Utils


class RedactionTest(unittest.TestCase):
    def test_tokens_are_removed(self):
        text = redact('url?access_token=abc&x=1 {"refresh_token": "def"} Authorization: Bearer ghi tempauth=jkl')
        for secret in ('abc', 'def', 'ghi', 'jkl'):
            self.assertNotIn(secret, text)
        self.assertIn('x=1', text)

    def test_revocation_requests_are_removed(self):
        text = redact('token=1%2F%2Fsecret-refresh&page_token=next')
        self.assertNotIn('secret-refresh', text)
        self.assertIn('page_token=next', text)


class SourceIdTest(unittest.TestCase):
    def test_ipv4_and_ipv6(self):
        self.assertEqual(Utils.get_source_id('203.0.113.10'), 326)
        self.assertEqual(Utils.get_source_id('2001:db8:1:2::1'), 0x2001 + 0xdb8 + 1 + 2)
        self.assertEqual(Utils.get_source_id('nonsense'), -1)


class Addon(CloudDriveAddon):
    # Built without the constructor, which needs Kodi: nothing to release.
    def __del__(self):
        pass


class RemoveAccountTest(unittest.TestCase):
    STRINGS = {32022: "Remove '%s'?", 32089: 'Remove from this Kodi only', 32090: 'Remove and revoke at %s', 32091: 'Not revoked at %s', 32092: "Remove account '%s'"}

    def remove(self, revoke_supported=True, select=0, yesno=True, revoke_error=None):
        addon = object.__new__(Addon)
        addon._addon_name = 'Test'
        addon._account_manager = mock.MagicMock()
        addon._account_manager.get_by_driveid.return_value = {'id': 'account-1', 'name': 'User'}
        addon._get_display_name = lambda account, with_format=False: account['name']
        addon._common_addon = mock.MagicMock()
        addon._common_addon.getLocalizedString.side_effect = lambda n: self.STRINGS[n]
        addon._dialog = mock.MagicMock()
        addon._dialog.select.return_value = select
        addon._dialog.yesno.return_value = yesno
        addon._provider = mock.MagicMock(revoke_supported=revoke_supported, signin_company='Google')
        if revoke_error:
            addon._provider.revoke_access.side_effect = revoke_error
        with mock.patch('clouddrive.common.ui.addon.KodiUtils.executebuiltin'):
            addon._remove_account('drive-1')
        return addon

    def test_asks_whether_to_revoke(self):
        addon = self.remove(select=0)
        addon._dialog.select.assert_called_once_with("Remove account 'User'", ['Remove from this Kodi only', 'Remove and revoke at Google'])
        addon._provider.revoke_access.assert_not_called()
        addon._account_manager.remove_account.assert_called_once_with('account-1')

    def test_revokes_when_chosen(self):
        addon = self.remove(select=1)
        addon._provider.configure.assert_called_once_with(addon._account_manager, 'drive-1')
        addon._provider.revoke_access.assert_called_once_with()
        addon._account_manager.remove_account.assert_called_once_with('account-1')

    def test_cancel_keeps_the_account(self):
        addon = self.remove(select=-1)
        addon._provider.revoke_access.assert_not_called()
        addon._account_manager.remove_account.assert_not_called()

    def test_removes_even_when_revoking_fails(self):
        addon = self.remove(select=1, revoke_error=Exception('offline'))
        addon._dialog.ok.assert_called_once_with('Test', 'Not revoked at Google')
        addon._account_manager.remove_account.assert_called_once_with('account-1')

    def test_providers_without_revoke_just_confirm(self):
        addon = self.remove(revoke_supported=False, yesno=True)
        addon._dialog.select.assert_not_called()
        addon._dialog.yesno.assert_called_once_with('Test', "Remove 'User'?")
        addon._account_manager.remove_account.assert_called_once_with('account-1')


class RoutingTest(unittest.TestCase):
    def route(self, params, cls=Addon):
        addon = object.__new__(cls)
        addon._addon_params = params
        addon._progress_dialog = mock.MagicMock()
        addon._progress_dialog_bg = mock.MagicMock()
        calls = []
        for name in ('play', 'list_accounts', '_handle_exception'):
            setattr(addon, name, (lambda n: lambda **kw: calls.append(n))(name))
        addon.route()
        return calls

    def test_known_actions_run(self):
        self.assertEqual(self.route({'action': 'play'}), ['play'])
        self.assertEqual(self.route({}), ['list_accounts'])

    def test_other_methods_cannot_be_called_from_urls(self):
        self.assertEqual(self.route({'action': 'route'}), [])
        self.assertEqual(self.route({'action': '_handle_exception'}), [])


if __name__ == '__main__':
    unittest.main()
