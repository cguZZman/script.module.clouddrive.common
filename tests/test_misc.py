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


class SourceIdTest(unittest.TestCase):
    def test_ipv4_and_ipv6(self):
        self.assertEqual(Utils.get_source_id('203.0.113.10'), 326)
        self.assertEqual(Utils.get_source_id('2001:db8:1:2::1'), 0x2001 + 0xdb8 + 1 + 2)
        self.assertEqual(Utils.get_source_id('nonsense'), -1)


class Addon(CloudDriveAddon):
    # Built without the constructor, which needs Kodi: nothing to release.
    def __del__(self):
        pass


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
