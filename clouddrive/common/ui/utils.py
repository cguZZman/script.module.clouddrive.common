'''
    OneDrive for Kodi
    Copyright (C) 2015 - Carlos Guzman

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License along
    with this program; if not, write to the Free Software Foundation, Inc.,
    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

    Created on Mar 1, 2015
    @author: Carlos Guzman (cguZZman) carlosguzmang@hotmail.com
'''
import xbmc
import xbmcgui
import xbmcaddon
import json
from clouddrive.common.utils import Utils
import urllib
from clouddrive.common.ui.logger import Logger

class KodiUtils:
    
    @staticmethod
    def get_addon(addonid=None):
        if addonid:
            return xbmcaddon.Addon(addonid)
        else:
            return xbmcaddon.Addon()
    
    @staticmethod
    def get_system_monitor():
        return xbmc.Monitor()
    
    @staticmethod
    def get_window(window_id):
        return xbmcgui.Window(window_id)
    
    @staticmethod
    def execute_json_rpc(method, params=None, request_id=1):
        cmd = {'jsonrpc': '2.0', 'method': method, 'id': request_id}
        if params:
            cmd['params'] = params
        return json.loads(xbmc.executeJSONRPC(json.dumps(cmd)))
    
    @staticmethod
    def run_plugin(addonid, params=None):
        url = 'plugin://%s/' % addonid
        if params:
            url += '?%s' % urllib.urlencode(params)
        cmd = 'RunPlugin(%s)' % url
        xbmc.executebuiltin(cmd, True)
        Logger.notice(cmd)
    
    @staticmethod
    def is_addon_enabled(addonid):
        response = KodiUtils.execute_json_rpc('Addons.GetAddonDetails', {'addonid': addonid})
        return response["result"]["addon"]["enabled"]

    @staticmethod
    def get_addon_setting(setting_id, addonid=None):
        addon = KodiUtils.get_addon(addonid)
        setting = addon.getSetting(setting_id)
        del addon
        return setting
    
    @staticmethod
    def set_addon_setting(setting_id, value, addonid=None):
        addon = KodiUtils.get_addon(addonid)
        setting = addon.setSetting(setting_id, Utils.str(value))
        del addon
        return setting
    
    @staticmethod
    def get_addon_info(info_id, addonid=None):
        addon = KodiUtils.get_addon(addonid)
        info = addon.getAddonInfo(info_id)
        del addon
        return info