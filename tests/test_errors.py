import re
import unittest
from unittest import mock
from urllib.error import HTTPError, URLError

import kodistubs
from clouddrive.common.account import AccountNotFoundException
from clouddrive.common.exception import RequestException, UIException
from clouddrive.common.ui.addon import CloudDriveAddon
from clouddrive.common.ui.errors import ErrorMessage, ErrorMessages

SERVER = 'https://drive.signinserver.com'


def request_error(url, code, response='{"error": {"code": "x", "message": "y"}}'):
    return RequestException('failed', HTTPError(url, code, 'msg', None, None), 'Request URL: ' + url, response)


class ErrorMessagesTest(unittest.TestCase):
    def setUp(self):
        self.messages = ErrorMessages(kodistubs.FakeAddon(), SERVER)

    def test_missing_account_offers_to_add_one(self):
        self.assertEqual(self.messages.describe(AccountNotFoundException('d'), True).ask, ErrorMessage.ADD_ACCOUNT)

    def test_rejected_token_offers_to_sign_in_again(self):
        self.assertEqual(self.messages.describe(request_error(SERVER + '/refresh', 400), True).ask, ErrorMessage.SIGN_IN_AGAIN)
        self.assertEqual(self.messages.describe(request_error('https://api.example.com/x', 401), True).ask, ErrorMessage.SIGN_IN_AGAIN)

    def test_provider_errors(self):
        self.assertEqual(self.messages.describe(request_error('https://api.example.com/x', 403), True).line1, '#32019')
        not_found = self.messages.describe(request_error('https://api.example.com/x', 404), True)
        self.assertEqual((not_found.line1, not_found.line2), ('#32037', None))
        server = self.messages.describe(request_error('https://api.example.com/x', 503), True)
        self.assertEqual((server.line1, server.line2, server.line3), ('#32035', None, '#32038'))
        other = self.messages.describe(request_error('https://api.example.com/x', 409), True)
        self.assertEqual((other.line1, other.line3, other.ask), ('#32036', '#32038', None))

    def test_rejected_code_explains_a_changed_ip(self):
        changed = self.messages.describe(request_error(SERVER + '/pin/ABC', 404), False, '1.2.3.4', lambda: '5.6.7.8')
        self.assertEqual(changed.line1, '#32072')
        same = self.messages.describe(request_error(SERVER + '/pin/ABC', 404), False, '1.2.3.4', lambda: '1.2.3.4')
        self.assertNotEqual(same.line1, '#32072')

    def test_network_errors(self):
        unreachable = self.messages.describe(RequestException('failed', URLError('[Errno 101] unreachable'), 'r', None), False)
        self.assertEqual((unreachable.line1, unreachable.line3), ('#32076', '#32074'))
        certificate = self.messages.describe(RequestException('failed', URLError('CERTIFICATE_VERIFY_FAILED'), 'r', None), False)
        self.assertEqual(certificate.line1, '#32078')

    def test_ui_exceptions_use_their_message(self):
        message = self.messages.describe(UIException(32065, ValueError('boom')), True)
        self.assertEqual((message.line1, message.line2), ('#32065', 'boom'))


if __name__ == '__main__':
    unittest.main()


class EnglishAddon(kodistubs.FakeAddon):
    # The real English texts: their %s must match what the code passes.
    with open('resources/language/resource.language.en_gb/strings.po', encoding='utf-8') as po:
        TEXTS = {int(m.group(1)): m.group(2) for m in re.finditer(r'msgctxt "#(\d+)"\s*\nmsgid "((?:[^"\\]|\\.)*)"', po.read())}

    def getLocalizedString(self, string_id):
        return self.TEXTS[string_id]


class Addon(CloudDriveAddon):
    # Built without the constructor, which needs Kodi: nothing to release.
    def __del__(self):
        pass


class ErrorDialogTest(unittest.TestCase):
    def test_rejected_token_asks_to_sign_in_again(self):
        addon = object.__new__(Addon)
        addon._common_addon = EnglishAddon()
        addon._addon_params = {'driveid': 'd'}
        addon._addon_url = 'plugin://test/'
        addon._addon_name = addon._addonid = 'test'
        addon._addon_version = addon._common_addon_version = '1'
        addon._content_type = 'video'
        addon._signin = None
        addon._dialog = mock.MagicMock()
        addon._dialog.yesno.return_value = False
        addon._account_manager = mock.MagicMock()
        addon._get_display_name = lambda account, drive=None, with_format=False: 'Carlos'
        with mock.patch('clouddrive.common.ui.addon.KodiUtils.get_signin_server', return_value=SERVER):
            addon._handle_exception(request_error('https://api.example.com/x', 401))
        text = addon._dialog.yesno.call_args[0][1]
        self.assertEqual(text, "The credentials for 'Carlos' are no longer valid. You need to sign in again.\nDo you want to start the process?")
        addon._dialog.ok.assert_not_called()
