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
from clouddrive.common.fetchableitem import FetchableItem
from clouddrive.common.ui.dialog import DialogProgress, DialogProgressBG
from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin


class CloudDriveAddon(FetchableItem):
    _DEFAULT_SIGNIN_TIMEOUT = 120
    
    _addon = None
    _addon_handle = None
    _addon_id = None
    _addon_name = None
    _addon_params = None
    _addon_url = None
    _cache = None
    _common_addon = None
    _cancel_operation = False
    _content_type = None
    _dialog = None
    _profile_path = None
    _progress_dialog = None
    _progress_dialog_bg = None
    _system_monitor = None
    _video_file_extensions = ['mkv', 'mp4', 'avi', 'iso', 'nut', 'ogg', 'vivo', 'pva', 'nuv', 'nsv', 'nsa', 'fli', 'flc', 'wtv', 'flv']
    _audio_file_extensions = ['mp3', 'wav', 'flac', 'alac', 'aiff', 'amr', 'ape', 'shn', 's3m', 'nsf', 'spc']
    _account_manager = None
    
    def __init__(self):
        self._addon = xbmcaddon.Addon()
        self._addon_id = self._addon.getAddonInfo('id')
        self._addon_name = self._addon.getAddonInfo('name')
        self._addon_url = sys.argv[0]
        self._common_addon = xbmcaddon.Addon('script.module.clouddrive.common')
        self._dialog = xbmcgui.Dialog()
        self._profile_path = Utils.unicode(xbmc.translatePath(self._addon.getAddonInfo('profile')))
        self._progress_dialog = DialogProgress(self._addon_name)
        self._progress_dialog_bg = DialogProgressBG(self._addon_name)
        self._system_monitor = xbmc.Monitor()
        self._account_manager = AccountManager(self._profile_path)
        
        if len(sys.argv) > 1:
            self._addon_handle = int(sys.argv[1])
            self._addon_params = urlparse.parse_qs(sys.argv[2][1:])
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
    
    def get_provider(self):
        raise NotImplementedError()
    
    def get_my_files_menu_name(self):
        return self._common_addon.getLocalizedString(32052)
    
    def get_custom_drive_folders(self):
        return [{'name' : self._common_addon.getLocalizedString(32058), 'folder' : 'shared_with_me'}]
    
    def get_folder_items(self):
        raise NotImplementedError()
    
    def cancel_operation(self):
        return self._system_monitor.abortRequested() or self._progress_dialog.iscanceled() or self._cancel_operation

    def get_accounts(self):
        accounts = self._account_manager.load()
        listing = []
        for account_id in accounts:
            account = accounts[account_id]
            size = len(account['drives'])
            for drive in account['drives']:
                params = {'action':'_remove_account', 'content_type': self._content_type, 'driveid': drive['id']}
                context_options = [(self._common_addon.getLocalizedString(32006), 'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')')]
                if size > 1:
                    params['action'] = '_remove_drive'
                    cmd =  'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')'
                    context_options.append((self._common_addon.getLocalizedString(32007), cmd))
                params['action'] = '_search'
                params['c'] = time.time()
                cmd = 'ActivateWindow(%d,%s?%s,return)' % (xbmcgui.getCurrentWindowId(), self._addon_url, urllib.urlencode(params))
                context_options.append((self._common_addon.getLocalizedString(32039), cmd))
                
                display = account['name']
                if 'type' in drive and drive['type']:
                    display += ' | ' + self.get_provider().get_drive_type_name(drive['type'])
                if 'name' in drive and drive['name']:
                    display += ' | ' + drive['name']
                list_item = xbmcgui.ListItem(display)
                list_item.addContextMenuItems(context_options)
                params = {'action':'_list_drive', 'content_type': self._content_type, 'driveid': drive['id']}
                url = self._addon_url + '?' + urllib.urlencode(params)
                listing.append((url, list_item, True))
        list_item = xbmcgui.ListItem(self._common_addon.getLocalizedString(32005))
        params = {'action':'_add_account', 'content_type': self._content_type}
        url = self._addon_url + '?' + urllib.urlencode(params)
        listing.append((url, list_item))
        xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(self._addon_handle, True)
    
    def _add_account(self):
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
        provider = self.get_provider()
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
                tokens_info = provider.fetch_tokens_info(pin_info, request_params = request_params)
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
            account = provider.get_account(request_params = request_params, access_tokens = tokens_info)
        except Exception as e:
            raise UIException(32065, e)
        if self.cancel_operation():
            return
        
        self._progress_dialog.update(90, self._common_addon.getLocalizedString(32017))
        try:
            account['drives'] = provider.get_drives(request_params = request_params, access_tokens = tokens_info)
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
    
    def _remove_drive(self):
        self._account_manager.load()
        driveid = self._addon_params.get('driveid', [None])[0]
        account = self._account_manager.get_account_by_driveid(driveid)
        drive = self._account_manager.get_drive_by_driveid(driveid)
        display = account['name']
        if 'type' in drive and drive['type']:
            display += ' | ' + self.get_provider().get_drive_type_name(drive['type'])
        if 'name' in drive and drive['name']:
            display += ' | ' + drive['name']
        if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32023) % display, None):
            self._account_manager.remove_drive(driveid)
        xbmc.executebuiltin('Container.Refresh')
    
    def _remove_account(self):
        self._account_manager.load()
        driveid = self._addon_params.get('driveid', [None])[0]
        account = self._account_manager.get_account_by_driveid(driveid)
        if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32022) % account['name'], None):
            self._account_manager.remove_account(account['id'])
        xbmc.executebuiltin('Container.Refresh')
        
    def _list_drive(self):
        drive_folders = self.get_custom_drive_folders()
        if drive_folders:
            listing = []
            driveid = self._addon_params.get('driveid', [None])[0]
            url = self._addon_url + '?' + urllib.urlencode({'action':'_list_folder', 'folder': 'root', 'content_type': self._content_type, 'driveid': driveid})
            listing.append((url, xbmcgui.ListItem(self.get_my_files_menu_name()), True))
            for folder in drive_folders:
                params = {'action':'_list_folder', 'folder': folder['folder'], 'content_type': self._content_type, 'driveid': driveid}
                if 'params' in folder:
                    params.update(folder['params'])
                url = self._addon_url + '?' + urllib.urlencode(params)
                listing.append((url, xbmcgui.ListItem(folder['name']), True))
                
            xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
            xbmcplugin.endOfDirectory(self._addon_handle, True)
        else:
            self.list_folder()

    def _list_folder(self):
        driveid = self._addon_params.get('driveid', [None])[0]
        self.get_provider().configure(self._account_manager, driveid)
        items = self.get_folder_items()
        if self.cancel_operation():
            return
        self._process_items(items)
        
    def _process_items(self, items):
        listing = []
        driveid = self._addon_params.get('driveid', [None])[0]
        for item in items:
            item_id = item['id']
            item_name = item['name']
            item_name_extension = item['name_extension']
            item_drive_id = Utils.default(Utils.get_safe_value(item, 'drive_id'), driveid)
            list_item = xbmcgui.ListItem(item_name)
            url = None
            is_folder = 'folder' in item
            params = {'content_type': self._content_type, 'item_driveid': item_drive_id, 'item_id': item_id, 'driveid': driveid}
            if is_folder:
                params['action'] = '_list_folder'
                url = self._addon_url + '?' + urllib.urlencode(params)
                context_options = []
                if self._content_type == 'audio' or self._content_type == 'video':
                    params['action'] = '_export_folder'
                    context_options.append((self._common_addon.getLocalizedString(32004), 'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')'))
                elif self._content_type == 'image':
                    params['action'] = '_slideshow'
                    context_options.append((self._common_addon.getLocalizedString(32032), 'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')'))
                params['action'] = '_search'
                params['c'] = time.time()
                cmd = 'ActivateWindow(%d,%s?%s,return)' % (xbmcgui.getCurrentWindowId(), self._addon_url, urllib.urlencode(params))
                context_options.append((self._common_addon.getLocalizedString(32039), cmd))
            elif (('video' in item or item_name_extension in self._video_file_extensions) and self._content_type == 'video') or (('audio' in item or item_name_extension in self._audio_file_extensions) and self._content_type == 'audio'):
                list_item.setProperty('IsPlayable', 'true')
                params['action'] = 'play'
                url = self._addon_url + '?' + urllib.urlencode(params)
                if 'audio' in item:
                    list_item.setInfo('music', item['audio'])
                elif 'video' in item:
                    list_item.addStreamInfo('video', item['video'])
                if 'thumbnail' in item:
                    list_item.setIconImage(item['thumbnail'])
                    list_item.setThumbnailImage(item['thumbnail'])
            elif 'image' in item and self._content_type == 'image' and item_name_extension != 'mp4':
                params['action'] = 'play'
                url = self._addon_url + '?' + urllib.urlencode(params)
                list_item.setInfo('pictures', item['image'])
                if 'thumbnail' in item:
                    list_item.setIconImage(item['thumbnail'])
            if url:
                list_item.setProperty('mimetype', Utils.get_safe_value(item, 'mimetype'))
                listing.append((url, list_item, is_folder))
        xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(self._addon_handle, True)
    
    def play(self):
        driveid = self._addon_params.get('driveid', [None])[0]
        item_id = self._addon_params.get('item_id', [None])[0]
        item_driveid = self._addon_params.get('item_driveid', [driveid])[0]
        find_subtitles = self._common_addon.getSetting('set_subtitle') == 'true' and self._content_type == 'video'
        item = self.get_item(driveid, item_driveid, item_id, find_subtitles)
        file_name = Utils.unicode(item['name'])
        list_item = xbmcgui.ListItem(file_name)
        if 'audio' in item:
            list_item.setInfo('music', item['audio'])
        elif 'video' in item:
            list_item.addStreamInfo('video', item['video'])
        list_item.select(True)
        base_url = 'http://localhost:'+self._common_addon.getSetting('download.sourceservice.port')+'/'+self._addon_id+'/'+driveid
        list_item.setPath(base_url+'/'+item_driveid+'/'+item_id+'/'+file_name)
        list_item.setProperty('mimetype', Utils.get_safe_value(item, 'mimetype'))
        if find_subtitles and 'subtitles' in item:
            subtitles = []
            for subtitle in item['subtitles']:
                subtitles.append(base_url+'/'+Utils.default(Utils.get_safe_value(subtitle, 'drive_id'), driveid)+'/'+subtitle['id']+'/'+subtitle['name'])
            list_item.setSubtitles(subtitles)
        xbmcplugin.setResolvedUrl(self._addon_handle, True, list_item)
    
    def route(self):
        try:
            if self._addon_params:
                action = self._addon_params.get('action', [None])[0]
                if action:
                    getattr(self, action)();
                else:
                    self.get_accounts()
            else:
                self.get_accounts()
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


