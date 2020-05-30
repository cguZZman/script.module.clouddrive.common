# coding: utf-8
# Module: tests
# Created on: 27.01.2016
# Author: Roman Miroshnychenko aka Roman V.M. (romanvm@yandex.ua)

from __future__ import print_function
import os
import sys
import unittest
import shutil
import time
from collections import defaultdict
import mock

cwd = os.path.dirname(os.path.abspath(__file__+"/../"))
configdir = os.path.join(cwd, 'config')


# Fake test objects

def fake_log(msg, level=0):
    if not isinstance(msg, str):
        raise TypeError('log message must be of str type!')


class FakeAddon(object):
    def __init__(self, id_='test.addon'):
        self._id = id_
        self._settings = {}

    def getAddonInfo(self, info_id):
        if info_id == 'path':
            return cwd
        elif info_id == 'profile':
            return configdir
        elif info_id == 'id':
            return self._id
        elif info_id == 'version':
            return '0.0.1'
        else:
            return ''

    def getSetting(self, setting_id):
        return self._settings.get(setting_id, '')

    def setSetting(self, setting_id, value):
        self._settings[setting_id] = value

    def getLocalizedString(self, id_):
        return {32000: u'Привет, мир!', 32001: u'Я тебя люблю.'}[id_]


class FakeWindow(object):
    def __init__(self, id_=-1):
        self._contents = defaultdict(str)

    def getProperty(self, key):
        return self._contents[key]

    def setProperty(self, key, value):
        self._contents[key] = value

    def clearProperty(self, key):
        del self._contents[key]

# Mock Kodi Python API

mock_xbmcaddon = mock.MagicMock()
mock_xbmcaddon.Addon.side_effect = FakeAddon

mock_xbmc = mock.MagicMock()
mock_xbmc.LOGDEBUG = 0
mock_xbmc.LOGNOTICE = 2
mock_xbmc.translatePath.side_effect = lambda path: path
mock_xbmc.log = fake_log

mock_xbmcgui = mock.MagicMock()
mock_xbmcgui.Window = FakeWindow

sys.modules['xbmcaddon'] = mock_xbmcaddon
sys.modules['xbmc'] = mock_xbmc
sys.modules['xbmcgui'] = mock_xbmcgui

# Import our module being tested
sys.path.append(cwd)

class AddonTestCase(unittest.TestCase):
    """
    Test Addon class
    """
    def tearDown(self):
        shutil.rmtree(configdir, True)
        try:
            os.remove('icon.png')
            os.remove('fanart.jpg')
        except OSError:
            pass

    def test_addon_instance_creation(self):
        from IPython import embed; embed(colors="neutral")
        addon = Addon('test.addon')
        self.assertEqual(addon.id, 'test.addon')
        self.assertTrue(os.path.exists(os.path.join(cwd, 'config')))

if __name__ == '__main__':
    unittest.main()
