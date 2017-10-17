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
import xbmcvfs
import os


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
    _exporting = False
    _exporting_target = 0
    _exporting_percent = 0
    _exporting_count = 0
    _profile_path = None
    _progress_dialog = None
    _progress_dialog_bg = None
    _export_progress_dialog_bg = None
    _system_monitor = None
    _video_file_extensions = ['mkv', 'mp4', 'avi', 'iso', 'nut', 'ogg', 'vivo', 'pva', 'nuv', 'nsv', 'nsa', 'fli', 'flc', 'wtv', 'flv']
    _audio_file_extensions = ['mp3', 'wav', 'flac', 'alac', 'aiff', 'amr', 'ape', 'shn', 's3m', 'nsf', 'spc']
    _account_manager = None
    _home_window = None
    
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
        self._export_progress_dialog_bg = DialogProgressBG(self._addon_name)
        self._system_monitor = xbmc.Monitor()
        self._account_manager = AccountManager(self._profile_path)
        self._home_window = xbmcgui.Window(10000)
        
        if len(sys.argv) > 1:
            self._addon_handle = int(sys.argv[1])
            self._addon_params = urlparse.parse_qs(sys.argv[2][1:])
            for param in self._addon_params:
                self._addon_params[param] = self._addon_params.get(param)[0]
            self._content_type = Utils.get_safe_value(self._addon_params, 'content_type')
            if not self._content_type:
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
    
    def get_folder_items(self, driveid=None, item_driveid=None, item_id=None, folder=None):
        raise NotImplementedError()
    
    def search(self, query, driveid=None, item_driveid=None, item_id=None):
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
                context_options = []
                params = {'action':'_search', 'content_type': self._content_type, 'driveid': drive['id']}
                cmd = 'ActivateWindow(%d,%s?%s)' % (xbmcgui.getCurrentWindowId(), self._addon_url, urllib.urlencode(params))
                context_options.append((self._common_addon.getLocalizedString(32039), cmd))
                params['action'] = '_remove_account'
                context_options.append((self._common_addon.getLocalizedString(32006), 'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')'))
                if size > 1:
                    params['action'] = '_remove_drive'
                    cmd =  'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')'
                    context_options.append((self._common_addon.getLocalizedString(32007), cmd))
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
    
    def _remove_drive(self, driveid=None, **kwargs):
        self._account_manager.load()
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
    
    def _remove_account(self, driveid=None, **kwargs):
        self._account_manager.load()
        account = self._account_manager.get_account_by_driveid(driveid)
        if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32022) % account['name'], None):
            self._account_manager.remove_account(account['id'])
        xbmc.executebuiltin('Container.Refresh')
        
    def _list_drive(self, driveid=None, **kwargs):
        drive_folders = self.get_custom_drive_folders()
        if self.cancel_operation():
            return
        if drive_folders:
            listing = []
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

    def _list_folder(self, driveid=None, item_driveid=None, item_id=None, folder=None, **kwargs):
        self.get_provider().configure(self._account_manager, driveid)
        items = self.get_folder_items(driveid, item_driveid, item_id, folder)
        if self.cancel_operation():
            return
        self._process_items(items, driveid)
        
    def _process_items(self, items, driveid=None):
        listing = []
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
                params['action'] = '_search'
                cmd = 'ActivateWindow(%d,%s?%s)' % (xbmcgui.getCurrentWindowId(), self._addon_url, urllib.urlencode(params))
                context_options.append((self._common_addon.getLocalizedString(32039), cmd))
                if self._content_type == 'audio' or self._content_type == 'video':
                    params['action'] = '_export_folder'
                    context_options.append((self._common_addon.getLocalizedString(32004), 'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')'))
                elif self._content_type == 'image':
                    params['action'] = '_slideshow'
                    context_options.append((self._common_addon.getLocalizedString(32032), 'RunPlugin('+self._addon_url + '?' + urllib.urlencode(params)+')'))
                list_item.addContextMenuItems(context_options)
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
    
    def _search(self, driveid=None, item_driveid=None, item_id=None, **kwargs):
        query = self._dialog.input(self._addon_name + ' - ' + self._common_addon.getLocalizedString(32042))
        Logger.notice('query = ' + query)
        if query:
            Logger.notice('searching... [%d]' % self._addon_handle)
            items = self.search(query, driveid, item_driveid, item_id)
            Logger.notice('result size = %d ' % len(items))
            if self.cancel_operation():
                return
            self._process_items(items, driveid)
        
    def _export_folder(self, driveid=None, item_driveid=None, item_id=None, **kwargs):
        if self._home_window.getProperty(self._addon_id + 'exporting'):
            self._dialog.ok(self._addon_name, self._common_addon.getLocalizedString(32059) + ' ' + self._common_addon.getLocalizedString(32038))
        else:
            string_id = 32002 if self._content_type == 'audio' else 32001
            string_config = 'music_library_folder' if self._content_type == 'audio' else 'video_library_folder'
            export_folder = self._addon.getSetting(string_config)
            if not export_folder or not xbmcvfs.exists(export_folder):
                export_folder = self._dialog.browse(0, self._common_addon.getLocalizedString(string_id), 'files', '', False, False, '')
            if xbmcvfs.exists(export_folder):
                self._export_progress_dialog_bg.create(self._addon_name + ' ' + self._common_addon.getLocalizedString(32024), self._common_addon.getLocalizedString(32025))
                self._export_progress_dialog_bg.update(0)
                self._addon.setSetting(string_config, export_folder)
                item = self.get_item(driveid, item_driveid, item_id)
                if self.cancel_operation():
                    return
                self._exporting_target = int(item['folder']['child_count']) + 1
                folder_name = Utils.unicode(item['name']).encode('ascii', 'ignore')
                folder_path = export_folder + folder_name + '/'
                if self._addon.getSetting('clean_folder') != 'true' or not xbmcvfs.exists(folder_path) or xbmcvfs.rmdir(folder_path, True):
                    self._exporting = True
                    self._home_window.setProperty(self._addon_id + 'exporting', 'true')
                    self.__export_folder(driveid, item, export_folder)
                else:
                    self._dialog.ok(self._addon_name, self._common_addon.getLocalizedString(32066) % folder_path)
                self._export_progress_dialog_bg.close()
            else:
                self._dialog.ok(self._addon_name, export_folder + ' ' + self._common_addon.getLocalizedString(32026))
    
    def __export_folder(self, driveid, folder, export_folder):
        folder_name = Utils.unicode(folder['name']).encode('ascii', 'ignore')
        folder_path = os.path.join(os.path.join(export_folder, folder_name), '')
        if not xbmcvfs.exists(folder_path):
            try:
                xbmcvfs.mkdirs(folder_path)
            except:
                self._system_monitor.waitForAbort(3)
                xbmcvfs.mkdirs(folder_path)
        items = self.get_folder_items(driveid, Utils.default(Utils.get_safe_value(folder, 'drive_id'), driveid), folder['id'])
        if self.cancel_operation():
            return
        for item in items:
            if 'folder' in item:
                self._exporting_target += int(item['folder']['child_count'])
        string_config = 'music_library_folder' if self._content_type == 'audio' else 'video_library_folder'
        base_export_folder = self._addon.getSetting(string_config)
        for item in items:
            is_folder = 'folder' in item
            item_name = Utils.ascii(item['name'])
            item_name_extension = item['name_extension']
            file_path = os.path.join(folder_path, item_name)
            if is_folder:
                self.__export_folder(driveid, item, folder_path)
            elif (('video' in item or item_name_extension in self._video_file_extensions) and self._content_type == 'video') or ('audio' in item and self._content_type == 'audio'):
                item_id = Utils.ascii(item['id'])
                item_drive_id = Utils.default(Utils.get_safe_value(item, 'drive_id'), driveid)
                params = {'action':'play', 'content_type': self._content_type, 'item_driveid': item_drive_id, 'item_id': item_id, 'driveid': driveid}
                url = self._addon_url + '?' + urllib.urlencode(params)
                file_path += '.strm'
                f = xbmcvfs.File(file_path, 'w')
                f.write(url)
                f.close()
            self._exporting_count += 1
            p = int(self._exporting_count/float(self._exporting_target)*100)
            if self._exporting_percent < p:
                self._exporting_percent = p
            self._export_progress_dialog_bg.update(self._exporting_percent, self._addon_name + ' ' + self._common_addon.getLocalizedString(32024), file_path[len(base_export_folder):])        
    
    def play(self, driveid=None, item_driveid=None, item_id=None, **kwargs):
        find_subtitles = self._addon.getSetting('set_subtitle') == 'true' and self._content_type == 'video'
        item = self.get_item(driveid, item_driveid, item_id, find_subtitles)
        file_name = Utils.unicode(item['name'])
        list_item = xbmcgui.ListItem(file_name)
        if 'audio' in item:
            list_item.setInfo('music', item['audio'])
        elif 'video' in item:
            list_item.addStreamInfo('video', item['video'])
        list_item.select(True)
        base_url = 'http://localhost:%s/%s/%s' % (self._common_addon.getSetting('download.sourceservice.port'), self._addon_id, driveid)
        list_item.setPath(base_url+'/'+item_driveid+'/'+item_id+'/'+urllib.quote(file_name))
        list_item.setProperty('mimetype', Utils.get_safe_value(item, 'mimetype'))
        if find_subtitles and 'subtitles' in item:
            subtitles = []
            for subtitle in item['subtitles']:
                subtitles.append(base_url+'/'+Utils.default(Utils.get_safe_value(subtitle, 'drive_id'), driveid)+'/'+subtitle['id']+'/'+urllib.quote(subtitle['name']))
            list_item.setSubtitles(subtitles)
        xbmcplugin.setResolvedUrl(self._addon_handle, True, list_item)
    
    def route(self):
        try:
            Logger.notice(self._addon_params)
            if self._addon_params and 'action' in self._addon_params:
                getattr(self, self._addon_params['action'])(**self._addon_params);
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
            self._export_progress_dialog_bg.close()
            if self._exporting:
                self._home_window.clearProperty(self._addon_id + 'exporting')


