import time
import unittest
import urllib.parse
from unittest import mock

import kodistubs
from clouddrive.common.remote import provider as provider_module
from clouddrive.common.remote import signin as remote_signin
from clouddrive.common.remote.provider import Provider
from clouddrive.common.ui.errors import ErrorMessage, ErrorMessages
from test_errors import request_error

TOKEN_URL = 'https://oauth2.example.com/token'
OWN_TOKENS = {'access_token': 'old', 'refresh_token': 'RT', 'expires_in': 3600, 'date': 0,
              'client_id': '123-abc.apps.example.com', 'client_secret': 'own-secret'}


class OwnClientProvider(Provider):
    own_client_token_url = TOKEN_URL

    def __init__(self, tokens):
        super(OwnClientProvider, self).__init__('googledrive')
        self.account = {'id': 'a', 'access_tokens': dict(tokens)}
        self.saved = []
        self._account_manager = mock.MagicMock(get_by_driveid=lambda kind, driveid: self.account,
                                               save_account=lambda account: self.saved.append(dict(account['access_tokens'])))
        self._driveid = 'drive'

    def _get_api_url(self):
        return 'https://api.example.com'

    def _get_request_headers(self):
        return {}


class FakeRequest(object):
    sent = []

    def __init__(self, url, data, headers=None, **kwargs):
        FakeRequest.sent.append((url, data))

    def request_json(self):
        return {'access_token': 'new', 'expires_in': 3599}


class RefreshTest(unittest.TestCase):
    def setUp(self):
        FakeRequest.sent = []
        self.signin = mock.MagicMock()
        self.signin.refresh_tokens.return_value = {'access_token': 'from-server', 'expires_in': 3599}

    def refresh(self, provider):
        provider._signin = self.signin
        with mock.patch.object(provider_module, 'Request', FakeRequest):
            return provider.refresh_access_tokens()

    def test_own_app_accounts_refresh_with_the_provider(self):
        self.assertEqual(self.refresh(OwnClientProvider(OWN_TOKENS))['access_token'], 'new')
        self.assertFalse(self.signin.refresh_tokens.called, 'not through the sign-in server')
        url, data = FakeRequest.sent[0]
        self.assertEqual(url, TOKEN_URL)
        self.assertEqual(urllib.parse.parse_qs(data), {'client_id': ['123-abc.apps.example.com'], 'client_secret': ['own-secret'],
                                                       'grant_type': ['refresh_token'], 'refresh_token': ['RT']})

    def test_other_accounts_refresh_through_the_sign_in_server(self):
        tokens = dict((k, v) for k, v in OWN_TOKENS.items() if not k.startswith('client_'))
        self.assertEqual(self.refresh(OwnClientProvider(tokens))['access_token'], 'from-server')
        unsupported = OwnClientProvider(OWN_TOKENS)
        unsupported.own_client_token_url = None
        self.assertEqual(self.refresh(unsupported)['access_token'], 'from-server', 'providers without own apps ignore them')
        self.assertEqual(FakeRequest.sent, [])

    def test_the_own_app_is_kept_after_a_refresh(self):
        provider = OwnClientProvider(OWN_TOKENS)
        provider._signin = self.signin
        with mock.patch.object(provider_module, 'Request', FakeRequest):
            provider.prepare_request('get', '/files')
        self.assertEqual(provider.saved[-1]['access_token'], 'new')
        self.assertEqual((provider.saved[-1]['client_id'], provider.saved[-1]['client_secret'], provider.saved[-1]['refresh_token']),
                         ('123-abc.apps.example.com', 'own-secret', 'RT'))


class CreatePinTest(unittest.TestCase):
    def test_says_whether_the_add_on_supports_own_apps(self):
        sent = []

        class PinRequest(FakeRequest):
            def __init__(self, url, data, headers=None, **kwargs):
                sent.append(urllib.parse.parse_qs(data))

        with mock.patch.object(remote_signin, 'Request', PinRequest), \
                mock.patch.object(remote_signin.KodiUtils, 'get_signin_server', staticmethod(lambda: 'https://signin.example.com')), \
                mock.patch.object(remote_signin.Signin, '_headers', lambda self: {}):
            OwnClientProvider(OWN_TOKENS).create_pin()
            Provider('onedrive').create_pin()
        self.assertEqual(sent, [{'provider': ['googledrive'], 'own_client': ['1']}, {'provider': ['onedrive']}])


class ErrorTest(unittest.TestCase):
    def test_a_refused_own_app_refresh_asks_to_sign_in_again(self):
        error = request_error(TOKEN_URL, 400)
        self.assertEqual(ErrorMessages(kodistubs.FakeAddon(), 'https://signin.example.com', TOKEN_URL).describe(error, True).ask,
                         ErrorMessage.SIGN_IN_AGAIN)
        self.assertIsNone(ErrorMessages(kodistubs.FakeAddon(), 'https://signin.example.com').describe(error, True).ask)


class RefusedRefreshTest(unittest.TestCase):
    SERVER = 'https://signin.example.com'

    def setUp(self):
        self.signin = mock.MagicMock()
        self.patches = [mock.patch.object(provider_module.KodiUtils, 'get_signin_server', staticmethod(lambda: self.SERVER)),
                        mock.patch.object(provider_module, 'Request', FakeRequest)]
        for patch in self.patches:
            patch.start()
        FakeRequest.sent = []

    def tearDown(self):
        for patch in self.patches:
            patch.stop()

    def provider(self, tokens):
        provider = OwnClientProvider(tokens)
        provider._signin = self.signin
        return provider

    def refuse(self, code, body):
        self.signin.refresh_tokens.side_effect = request_error(self.SERVER + '/refresh', code, body)

    def test_a_refused_token_is_not_sent_again(self):
        self.refuse(401, '{"status":401,"error":"unauthorized_client"}')
        provider = self.provider(dict((k, v) for k, v in OWN_TOKENS.items() if not k.startswith('client_')))
        for _ in range(3):
            with self.assertRaises(Exception) as raised:
                provider.prepare_request('get', '/files')
            self.assertEqual(ErrorMessages(kodistubs.FakeAddon(), self.SERVER).describe(raised.exception, True).ask,
                             ErrorMessage.SIGN_IN_AGAIN, 'asks to sign in again')
        self.assertEqual(self.signin.refresh_tokens.call_count, 1)
        self.assertEqual((provider.saved[-1]['refresh_refused']['error'], provider.saved[-1]['refresh_refused']['status']),
                         ('unauthorized_client', 401))

    def test_asks_again_a_day_later_and_a_refresh_that_works_clears_the_refusal(self):
        self.refuse(400, '{"status":400,"error":"invalid_grant"}')
        provider = self.provider(dict((k, v) for k, v in OWN_TOKENS.items() if not k.startswith('client_')))
        with self.assertRaises(Exception):
            provider.prepare_request('get', '/files')
        self.signin.refresh_tokens.side_effect = None
        self.signin.refresh_tokens.return_value = {'access_token': 'new', 'expires_in': 3599}
        later = time.time() + Provider.REFUSED_RETRY_S
        with mock.patch.object(provider_module.time, 'time', lambda: later):
            provider.prepare_request('get', '/files')
        self.assertEqual(self.signin.refresh_tokens.call_count, 2)
        self.assertIsNone(provider.saved[-1]['refresh_refused'])
        self.assertEqual(provider.saved[-1]['access_token'], 'new')

    def test_other_errors_are_not_remembered(self):
        provider = self.provider(dict((k, v) for k, v in OWN_TOKENS.items() if not k.startswith('client_')))
        for code, body in ((401, '{"error":"invalid_client"}'), (503, '{"error":"unavailable"}'), (400, 'Bad request'),
                           (403, '{"error":"invalid_grant"}')):
            self.refuse(code, body)
            with self.assertRaises(Exception):
                provider.prepare_request('get', '/files')
        self.assertEqual(self.signin.refresh_tokens.call_count, 4)
        self.assertEqual(provider.saved, [])

    def test_own_app_refusals_are_remembered(self):
        class RefusingRequest(FakeRequest):
            def request_json(self):
                raise request_error(TOKEN_URL, 400, '{"error": "invalid_grant", "error_description": "Bad Request"}')

        provider = self.provider(OWN_TOKENS)
        with mock.patch.object(provider_module, 'Request', RefusingRequest):
            for _ in range(2):
                with self.assertRaises(Exception) as raised:
                    provider.prepare_request('get', '/files')
        self.assertEqual(len(FakeRequest.sent), 1)
        self.assertEqual(ErrorMessages(kodistubs.FakeAddon(), self.SERVER, TOKEN_URL).describe(raised.exception, True).ask,
                         ErrorMessage.SIGN_IN_AGAIN)
