# Stand-ins for Kodi's Python modules, so the add-on code can be imported and tested outside Kodi.
# Import this module before anything from clouddrive.
import os
import sys
import tempfile
from unittest import mock

for name in ('xbmc', 'xbmcaddon', 'xbmcgui', 'xbmcplugin', 'xbmcvfs', 'pyqrcode'):
    sys.modules.setdefault(name, mock.MagicMock())
try:
    import dateutil  # noqa: F401  (installed in CI; Kodi ships it)
except ImportError:
    for name in ('dateutil', 'dateutil.parser', 'dateutil.tz'):
        sys.modules.setdefault(name, mock.MagicMock())

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clouddrive.common.ui.utils import KodiUtils  # noqa: E402


def use_temp_profile():
    """Points the add-on's data folder to a new temporary directory and returns it."""
    path = tempfile.mkdtemp()
    KodiUtils.file_exists = staticmethod(os.path.exists)
    KodiUtils.mkdirs = staticmethod(lambda p: os.makedirs(p, exist_ok=True))
    KodiUtils.translate_path = staticmethod(lambda p: p)
    KodiUtils.get_addon_info = staticmethod(lambda *args: path)
    KodiUtils.get_system_monitor = staticmethod(lambda: mock.MagicMock(abortRequested=lambda: False, waitForAbort=lambda s=0: False))
    return path


class Text(str):
    """A localized string stand-in: formatting with % appends the arguments instead of filling placeholders."""

    def __mod__(self, args):
        return Text('%s %s' % (self, args if isinstance(args, tuple) else (args,)))


class FakeAddon(object):
    """xbmcaddon.Addon with strings: getLocalizedString(id) returns '#<id>'."""

    def getLocalizedString(self, string_id):
        return Text('#%d' % string_id)

    def getSetting(self, setting_id):
        return ''

    def getAddonInfo(self, info):
        return 'test'
