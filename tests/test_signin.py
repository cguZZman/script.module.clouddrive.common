import unittest
from unittest import mock

import kodistubs
from clouddrive.common.ui import signin
from clouddrive.common.ui.signin import AccountSignin


class FakeProvider(object):
    def __init__(self, tokens_after=1):
        self.polls = 0
        self.tokens_after = tokens_after

    def create_pin(self, request_params):
        return {'pin': 'ABC123', 'password': 'secret'}

    def register_networks(self, pin_info):
        return ['571 (IPv4)']

    def fetch_tokens_info(self, pin_info, request_params=None):
        self.polls += 1
        return {'access_token': 'AT', 'refresh_token': 'RT', 'expires_in': 3600, 'date': 1} if self.polls >= self.tokens_after else None

    def get_account(self, request_params=None, access_tokens=None):
        return {'id': 'acc', 'name': 'Name'}

    def get_drives(self, request_params=None, access_tokens=None):
        return [{'id': 'drive', 'name': '', 'type': 'personal'}]


class AccountSigninTest(unittest.TestCase):
    def setUp(self):
        self.accounts = mock.MagicMock()
        self.accounts.get_accounts.return_value = {}
        self.monitor = mock.MagicMock(abortRequested=lambda: False, waitForAbort=lambda s=0: False)
        self.progress = mock.MagicMock(iscanceled=lambda: False)
        self.dialog = mock.MagicMock(iscanceled=lambda: False)
        self.patches = [mock.patch.object(signin, 'QRDialogProgress', mock.MagicMock(create=mock.MagicMock(return_value=self.dialog))),
                        mock.patch.object(signin.KodiUtils, 'get_signin_server', return_value='https://drive.signinserver.com'),
                        mock.patch.object(signin, 'Request')]
        for p in self.patches:
            p.start()
        signin.Request.return_value.request.return_value = '1.2.3.4'

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def run_signin(self, provider):
        flow = AccountSignin(provider, self.accounts, kodistubs.FakeAddon(), 'Add-on', self.progress, mock.MagicMock(), self.monitor)
        return flow, flow.run()

    def test_signs_in_and_saves_the_account(self):
        flow, account = self.run_signin(FakeProvider())
        self.assertEqual(account['drives'][0]['id'], 'drive')
        self.assertEqual(account['access_tokens']['refresh_token'], 'RT')
        self.accounts.save_account.assert_called_once_with(account)
        self.assertEqual(flow.ip_before_pin, '1.2.3.4')
        self.dialog.close.assert_called()
        self.assertIn('571 (IPv4)', self.dialog.update.call_args[1]['line3'])

    def test_cancelled_code_dialog_saves_nothing(self):
        self.dialog.iscanceled = lambda: True
        flow, account = self.run_signin(FakeProvider(tokens_after=99))
        self.assertIsNone(account)
        self.accounts.save_account.assert_not_called()
        self.dialog.close.assert_called()


if __name__ == '__main__':
    unittest.main()


class SigninHeadersTest(unittest.TestCase):
    def test_requests_say_which_versions_are_in_use(self):
        import platform
        import sys
        from clouddrive.common.remote import signin as remote_signin
        info = {('id', None): 'plugin.googledrive', ('version', None): '1.6.3', ('version', 'script.module.clouddrive.common'): '1.5.5'}
        sent = []

        class FakeRequest(object):
            def __init__(self, url, data, headers=None, **kwargs):
                sent.append((url, headers))

            def request_json(self):
                return {}

        with mock.patch.object(remote_signin.KodiUtils, 'get_addon_info', staticmethod(lambda info_id, addonid=None: info[(info_id, addonid)])), \
                mock.patch.object(remote_signin.KodiUtils, 'get_signin_server', staticmethod(lambda: 'https://signin.example.com')), \
                mock.patch.object(remote_signin, 'Request', FakeRequest), \
                mock.patch.object(sys.modules['xbmc'], 'getInfoLabel', lambda label: '21.2 (21.2.0) Git:20241011-dbaab1ab2a'):
            client = remote_signin.Signin()
            client.create_pin('googledrive')
            client.refresh_tokens('googledrive', 'token')
            client.fetch_tokens_info({'pin': 'ABC123', 'password': 'secret'})
        python = '.'.join(platform.python_version_tuple()[:2])
        for url, headers in sent:
            self.assertEqual(headers['addon'], 'plugin.googledrive 1.6.3/1.5.5', url)
            self.assertEqual(headers['user-agent'], 'plugin.googledrive/1.6.3 clouddrive.common/1.5.5 Kodi/21.2 Python/%s' % python, url)
        self.assertTrue(sent[2][1]['authorization'].startswith('Basic '))
        self.assertEqual(len(sent), 3)
