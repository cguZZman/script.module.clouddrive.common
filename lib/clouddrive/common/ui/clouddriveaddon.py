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

import sys
import time
import urllib
import urlparse

from clouddrive.common.account import AccountManager
from clouddrive.common.exception import UIException, ExceptionUtils, RequestException
from clouddrive.common.remote.signin import Signin
from clouddrive.common.ui.dialog import DialogProgress, DialogProgressBG
from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin


class CloudDriveAddon(object):
    _DEFAULT_SIGNIN_TIMEOUT = 120
    _account_manager = None
    _addon = xbmcaddon.Addon()
    _addon_handle = None
    _addon_id = _addon.getAddonInfo('id')
    _addon_name = _addon.getAddonInfo('name')
    _addon_params = None
    _addon_url = None
    _common_addon = xbmcaddon.Addon('script.module.clouddrive.common')
    _cancel_operation = False
    _content_type = None
    _dialog = xbmcgui.Dialog()
    _progress_dialog = DialogProgress(_addon_name)
    _progress_dialog_bg = DialogProgressBG(_addon_name)
    _system_monitor = xbmc.Monitor()
    
    def __init__(self):
        self._addon_url = sys.argv[0]
        self._addon_handle = int(sys.argv[1])
        self._addon_params = urlparse.parse_qs(sys.argv[2][1:])
        self._account_manager = AccountManager(Utils.unicode(xbmc.translatePath(self._addon.getAddonInfo('profile'))))
        try:
            self._content_type = self._addon_params.get('content_type')[0]
        except:
            wid = xbmcgui.getCurrentWindowId()
            if wid == 10005 or wid == 10500 or wid == 10501 or wid == 10502:
                self._content_type = 'audio'
            elif wid == 10002:
                self._content_type = 'image'
            else:
                self._content_type = 'video'
    
    def provider(self):
        raise NotImplementedError()
    
    def cancel_operation(self):
        return self._system_monitor.abortRequested() or self._progress_dialog.iscanceled() or self._cancel_operation

    def accounts(self):
        accounts = self._account_manager.load()
        listing = []
        for account_id in accounts:
            account = accounts[account_id]
            size = len(account['drives'])
            for drive in account['drives']:
                display = account['name']
                if 'type' in drive and drive['type']:
                    display += ' | ' + self.provider().drive_type_name(drive['type'])
                if 'name' in drive and drive['name']:
                    display += ' | ' + drive['name']
                list_item = xbmcgui.ListItem(display)
                params = {'action':'open_drive', 'content_type': self._content_type, 'driveid': drive['id']}
                url = self._addon_url + '?' + urllib.urlencode(params)
                params = {'action':'remove_account', 'content_type': self._content_type, 'driveid': drive['id']}
                context_options = [(self._common_addon.getLocalizedString(32006), 'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')')]
                if size > 1:
                    params['action'] = 'remove_drive'
                    cmd =  'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')'
                    context_options.append((self._common_addon.getLocalizedString(32007), cmd))
                params['action'] = 'search'
                params['c'] = time.time()
                cmd = 'ActivateWindow(%d,%s?%s,return)' % (xbmcgui.getCurrentWindowId(), self._addon_url, urllib.urlencode(params))
                context_options.append((self._common_addon.getLocalizedString(32039), cmd))
                list_item.addContextMenuItems(context_options)
                listing.append((url, list_item, True))
        list_item = xbmcgui.ListItem(self._common_addon.getLocalizedString(32005))
        params = {'action':'add_account', 'content_type': self._content_type}
        url = self._addon_url + '?' + urllib.urlencode(params)
        listing.append((url, list_item))
        xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(self._addon_handle, True)
    
    def add_account(self):
        request_params = {
            'waiting_retry': lambda request, remaining: self._progress_dialog_bg.update(
                int((request.current_delay - remaining)/request.current_delay*100),
                heading=self._common_addon.getLocalizedString(32043) % ('' if request.current_tries == 1 else ' again'),
                message=self._common_addon.getLocalizedString(32044) % str(int(remaining)) + ' ' +
                        self._common_addon.getLocalizedString(32045) % (str(request.current_tries + 1), str(request.tries))
            ),
            'on_complete': lambda request: (self._progress_dialog.close(), self._progress_dialog_bg.close()),
            'cancel_operation': self.cancel_operation,
            'wait': self._system_monitor.waitForAbort
        }
        provider = self.provider()
        self._progress_dialog.update(0, self._common_addon.getLocalizedString(32008))
        pin_info = provider.create_pin(request_params)
        if self.cancel_operation():
            return
        if not pin_info:
            raise Exception('Unable to retrieve a pin code')

        tokens_info = {}
        request_params['on_complete'] = lambda request: self._progress_dialog_bg.close()
        self._progress_dialog.update(100, self._common_addon.getLocalizedString(32009), self._common_addon.getLocalizedString(32010) % pin_info['pin'])
        current_time = time.time()
        max_waiting_time = current_time + self._DEFAULT_SIGNIN_TIMEOUT
        while not self.cancel_operation() and max_waiting_time > current_time:
            remaining = round(max_waiting_time-current_time)
            percent = int(remaining/self._DEFAULT_SIGNIN_TIMEOUT*100)
            self._progress_dialog.update(percent, line3=self._common_addon.getLocalizedString(32011) % str(int(remaining)))
            if int(remaining) % 5 == 0 or remaining == 1:
                tokens_info = provider.retrieve_tokens_info(pin_info, request_params = request_params)
                if self.cancel_operation() or tokens_info:
                    break
            self._system_monitor.waitForAbort(1)
            current_time = time.time()
        
        if self.cancel_operation() or current_time >= max_waiting_time:
            return
        if not tokens_info:
            raise Exception('Unable to retrieve the auth2 tokens')
        
        self._progress_dialog.update(60, self._common_addon.getLocalizedString(32064))
        try:
            account = provider.account(request_params = request_params, access_tokens = tokens_info)
        except Exception as e:
            raise UIException(32065, e)
        if self.cancel_operation():
            return
        
        self._progress_dialog.update(90, self._common_addon.getLocalizedString(32017))
        try:
            account['drives'] = provider.drives(request_params = request_params, access_tokens = tokens_info)
        except Exception as e:
            raise UIException(32018, e)
        if self.cancel_operation():
            return
        
        self._progress_dialog.update(95, self._common_addon.getLocalizedString(32020))
        try:
            account['access_tokens'] = tokens_info
            self._account_manager.add_account(account)
        except Exception as e:
            raise UIException(32021, e)
        if self.cancel_operation():
            return
        
        self._progress_dialog.close()
        xbmc.executebuiltin('Container.Refresh')
    
    def remove_drive(self):
        self._account_manager.load()
        driveid = self._addon_params.get('driveid', [None])[0]
        account = self._account_manager.account_by_driveid(driveid)
        drive = self._account_manager.drive_by_driveid(driveid)
        display = account['name']
        if 'type' in drive and drive['type']:
            display += ' | ' + self.provider().drive_type_name(drive['type'])
        if 'name' in drive and drive['name']:
            display += ' | ' + drive['name']
        if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32023) % display, None):
            self._account_manager.remove_drive(driveid)
        xbmc.executebuiltin('Container.Refresh')
    
    def remove_account(self):
        self._account_manager.load()
        driveid = self._addon_params.get('driveid', [None])[0]
        account = self._account_manager.account_by_driveid(driveid)
        if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32022) % account['name'], None):
            self._account_manager.remove_account(account['id'])
        xbmc.executebuiltin('Container.Refresh')
        
    def open_drive(self):
        driveid = self._addon_params.get('driveid', [None])[0]
        list_item = xbmcgui.ListItem(self._common_addon.getLocalizedString(32052))
        params = {'action':'open_drive_folder', 'folder':'root', 'content_type': self._content_type, 'driveid': driveid}
        url = self._addon_url + '?' + urllib.urlencode(params)
        xbmcplugin.addDirectoryItem(self._addon_handle, url, list_item, True)
        list_item = xbmcgui.ListItem(self._common_addon.getLocalizedString(32053))
        params['action'] = 'open_simple_folder'
        params['folder'] = 'recent'
        url = self._addon_url + '?' + urllib.urlencode(params)
        xbmcplugin.addDirectoryItem(self._addon_handle, url, list_item, True)
        if self._content_type == 'image':
            list_item = xbmcgui.ListItem(self._common_addon.getLocalizedString(32055))
            params['action'] = 'open_drive_folder'
            params['folder'] = 'special/photos'
            url = self._addon_url + '?' + urllib.urlencode(params)
            xbmcplugin.addDirectoryItem(self._addon_handle, url, list_item, True)
        if self._content_type == 'audio':
            list_item = xbmcgui.ListItem(self._common_addon.getLocalizedString(32056))
            params['action'] = 'open_drive_folder'
            params['folder'] = 'special/music'
            url = self._addon_url + '?' + urllib.urlencode(params)
            xbmcplugin.addDirectoryItem(self._addon_handle, url, list_item, True)
        #list_item = xbmcgui.ListItem(addon.getLocalizedString(32057))
        #params['action'] = 'open_simple_folder'
        #params['folder'] = 'shared'
        #url = base_url + '?' + urllib.urlencode(params)
        #xbmcplugin.addDirectoryItem(addon_handle, url, list_item, True)
        list_item = xbmcgui.ListItem(self._common_addon.getLocalizedString(32058))
        params['action'] = 'open_shared_with_me'
        params['folder'] = ''
        url = self._addon_url + '?' + urllib.urlencode(params)
        xbmcplugin.addDirectoryItem(self._addon_handle, url, list_item, True)
        xbmcplugin.endOfDirectory(self._addon_handle)
    
    '''
    def open_drive_folder(self):
        driveid = self._addon_params.get('driveid', [None])[0]
        item_driveid = self._addon_params.get('item_driveid', [driveid])[0]
        folder = self._addon_params.get('folder')[0]
        
        root = onedrive.get('/drives/'+item_driveid+'/' + folder, params=extra_parameters)
        if not cancelOperation(onedrive):
            child_count = int(root['folder']['childCount'])
            big_folder = child_count > big_folder_min
            if big_folder:
                if pg_bg_created:
                    progress_dialog_bg.close()
                progress_dialog_bg.create(addonname, addon.getLocalizedString(32049) % Utils.str(child_count))
                pg_bg_created = True
                progress_dialog_bg.update(0)
            files = onedrive.get('/drives/'+item_driveid+'/' + folder + '/children', params=extra_parameters)
            if not cancelOperation(onedrive):
                process_files(files, driveid, child_count, 0, big_folder)
            if not cancelOperation(onedrive):
                xbmcplugin.endOfDirectory(addon_handle)
                if big_folder:
                    progress_dialog_bg.close()
                    pg_bg_created = False
    '''
    def route(self):
        try:
            if self._addon_params:
                action = self._addon_params.get('action', [None])[0]
                if action:
                    getattr(self, action)();
                else:
                    self.accounts()
            else:
                self.accounts()
        except Exception as ex:
            Logger.notice(ExceptionUtils.full_stacktrace(ex))
            rex = ExceptionUtils.extract_exception(ex, RequestException)
            uiex = ExceptionUtils.extract_exception(ex, UIException)
            
            line1 = self._common_addon.getLocalizedString(32027)
            line2 = Utils.unicode(ex)
            line3 = self._common_addon.getLocalizedString(32016)
            
            if uiex:
                line1 = self._common_addon.getLocalizedString(int(Utils.str(uiex)))
                line2 = Utils.unicode(uiex.root_exception)
            elif rex and rex.response:
                line1 += ' ' + Utils.unicode(rex)
                line2 = Utils.str(rex.response)
                Logger.notice('Response from provider: ' + line2)
                    
            self._dialog.ok(self._addon_name, line1, line2, line3)
        finally:
            self._progress_dialog.close()
            self._progress_dialog_bg.close()


