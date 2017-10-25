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

import inspect
import os
import sys
import threading
import time
import urllib
from urllib2 import HTTPError
import urlparse

from clouddrive.common.account import AccountManager, AccountNotFoundException, \
    DriveNotFoundException
from clouddrive.common.exception import UIException, ExceptionUtils, RequestException
from clouddrive.common.remote.errorreport import ErrorReport
from clouddrive.common.remote.signin import Signin
from clouddrive.common.service.download import DownloadServiceUtil
from clouddrive.common.service.rpc import RemoteProcessCallable
from clouddrive.common.ui.dialog import DialogProgress, DialogProgressBG
from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs


class CloudDriveAddon(RemoteProcessCallable):
    _DEFAULT_SIGNIN_TIMEOUT = 120
    _addon = None
    _addon_handle = None
    _addonid = None
    _addon_name = None
    _addon_params = None
    _addon_url = None
    _addon_version = None
    _cache = None
    _common_addon = None
    _cancel_operation = False
    _content_type = None
    _dialog = None
    _exporting = False
    _exporting_target = 0
    _exporting_percent = 0
    _exporting_count = 0
    _load_target = 0
    _load_count = 0
    _profile_path = None
    _progress_dialog = None
    _progress_dialog_bg = None
    _export_progress_dialog_bg = None
    _system_monitor = None
    _video_file_extensions = ['mkv', 'mp4', 'avi', 'iso', 'nut', 'ogg', 'vivo', 'pva', 'nuv', 'nsv', 'nsa', 'fli', 'flc', 'wtv', 'flv']
    _audio_file_extensions = ['mp3', 'wav', 'flac', 'alac', 'aiff', 'amr', 'ape', 'shn', 's3m', 'nsf', 'spc']
    _account_manager = None
    _home_window = None
    _action = None
    
    def __init__(self):
        self._addon = xbmcaddon.Addon()
        self._addonid = self._addon.getAddonInfo('id')
        self._addon_name = self._addon.getAddonInfo('name')
        self._addon_url = sys.argv[0]
        self._addon_version = self._addon.getAddonInfo('version')
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
    
    def get_custom_drive_folders(self, driveid):
        return
    
    def get_folder_items(self, driveid, item_driveid=None, item_id=None, path=None, on_items_page_completed=None):
        raise NotImplementedError()
    
    def search(self, query, driveid, item_driveid=None, item_id=None, before_pagination=None):
        raise NotImplementedError()
    
    def cancel_operation(self):
        return self._system_monitor.abortRequested() or self._progress_dialog.iscanceled() or self._cancel_operation

    def _get_display_name(self, account, drive):
        display = account['name']
        if 'type' in drive and drive['type']:
            display += ' | ' + self.get_provider().get_drive_type_name(drive['type'])
        if 'name' in drive and drive['name']:
            display += ' | ' + drive['name']
        return display
    
    def get_accounts(self):
        accounts = self._account_manager.load()
        for account_id in accounts:
            account = accounts[account_id]
            for drive in account['drives']:
                drive['display_name'] = self._get_display_name(account, drive)
        return accounts
                    
    def list_accounts(self):
        accounts = self.get_accounts()
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
                list_item = xbmcgui.ListItem(drive['display_name'])
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
        self._progress_dialog.update(100, self._common_addon.getLocalizedString(32009) % Signin._signin_url, self._common_addon.getLocalizedString(32010) % pin_info['pin'])
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
    
    def _remove_drive(self, driveid):
        self._account_manager.load()
        account = self._account_manager.get_account_by_driveid(driveid)
        drive = self._account_manager.get_drive_by_driveid(driveid)
        if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32023) % self._get_display_name(account, drive), None):
            self._account_manager.remove_drive(driveid)
        xbmc.executebuiltin('Container.Refresh')
    
    def _remove_account(self, driveid):
        self._account_manager.load()
        account = self._account_manager.get_account_by_driveid(driveid)
        if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32022) % account['name'], None):
            self._account_manager.remove_account(account['id'])
        xbmc.executebuiltin('Container.Refresh')
        
    def _list_drive(self, driveid):
        drive_folders = self.get_custom_drive_folders(driveid)
        if self.cancel_operation():
            return
        if drive_folders:
            listing = []
            url = self._addon_url + '?' + urllib.urlencode({'action':'_list_folder', 'path': '/', 'content_type': self._content_type, 'driveid': driveid})
            listing.append((url, xbmcgui.ListItem(self.get_my_files_menu_name()), True))
            for folder in drive_folders:
                params = {'action':'_list_folder', 'path': folder['path'], 'content_type': self._content_type, 'driveid': driveid}
                if 'params' in folder:
                    params.update(folder['params'])
                url = self._addon_url + '?' + urllib.urlencode(params)
                list_item = xbmcgui.ListItem(folder['name'])
                if 'context_options' in folder:
                    list_item.addContextMenuItems(folder['context_options'])
                listing.append((url, list_item, True))
            xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
            xbmcplugin.endOfDirectory(self._addon_handle, True)
        else:
            self._list_folder(driveid, path='/')

    def on_items_page_completed(self, items):
        self._load_count += len(items)
        if self._load_target > self._load_count:
            percent = int(round(float(self._load_count)/self._load_target*100))
            self._progress_dialog_bg.update(percent, self._addon_name, self._common_addon.getLocalizedString(32047) % (Utils.str(self._load_count), Utils.str(self._load_target)))
        else:
            self._progress_dialog_bg.update(100, self._addon_name, self._common_addon.getLocalizedString(32048) % Utils.str(self._load_count))
            
    def _list_folder(self, driveid, item_driveid=None, item_id=None, path=None):
        item = self.get_item(driveid, item_driveid, item_id, path)
        if item:
            self._load_target = item['folder']['child_count']
            self._progress_dialog_bg.create(self._addon_name, self._common_addon.getLocalizedString(32049) % Utils.str(self._load_target))
        items = self.get_folder_items(driveid, item_driveid, item_id, path, on_items_page_completed = self.on_items_page_completed)
        if self.cancel_operation():
            return
        self._process_items(items, driveid)
        
    def _process_items(self, items, driveid):
        listing = []
        for item in items:
            item_id = item['id']
            item_name = item['name']
            item_name_extension = item['name_extension']
            item_driveid = Utils.default(Utils.get_safe_value(item, 'drive_id'), driveid)
            list_item = xbmcgui.ListItem(item_name)
            url = None
            is_folder = 'folder' in item
            params = {'content_type': self._content_type, 'item_driveid': item_driveid, 'item_id': item_id, 'driveid': driveid}
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
                url = DownloadServiceUtil.build_download_url(self._addonid, driveid, item_driveid, item_id, urllib.quote(item_name))
                list_item.setInfo('pictures', item['image'])
                if 'thumbnail' in item:
                    list_item.setIconImage(item['thumbnail'])
                    list_item.setThumbnailImage(item['thumbnail'])
            if url:
                list_item.setProperty('mimetype', Utils.get_safe_value(item, 'mimetype'))
                listing.append((url, list_item, is_folder))
        xbmcplugin.addDirectoryItems(self._addon_handle, listing, len(listing))
        xbmcplugin.endOfDirectory(self._addon_handle, True)
    
    def _search(self, driveid, item_driveid=None, item_id=None):
        query = self._dialog.input(self._addon_name + ' - ' + self._common_addon.getLocalizedString(32042))
        Logger.notice('query = ' + query)
        if query:
            self._progress_dialog_bg.create(self._addon_name, self._common_addon.getLocalizedString(32041))
            items = self.search(query, driveid, item_driveid, item_id, on_items_page_completed = self.on_items_page_completed)
            Logger.notice('result size = %d ' % len(items))
            if self.cancel_operation():
                return
            self._process_items(items, driveid)
    
    def _slideshow(self, driveid, item_driveid=None, item_id=None, path=None, old_child_count=0):
        item = self.get_item(driveid, item_driveid, item_id, path)
        if self.cancel_operation():
            return
        if item:
            wait_for_slideshow = False
            child_count = item['folder']['child_count']
            if old_child_count != child_count:
                if child_count >= 0:
                    Logger.debug('Slideshow child count changed. Refreshing slideshow...')
                params = {'action':'_list_folder', 'content_type': self._content_type,
                          'item_driveid': Utils.default(item_driveid, ''), 'item_id': Utils.default(item_id, ''), 'driveid': driveid, 'path' : Utils.default(path, ''),
                          'child_count': child_count}
                extra_params = ',recursive' if self._addon.getSetting('slideshow_recursive') == 'true' else ''
                xbmc.executebuiltin('SlideShow('+self._addon_url + '?' + urllib.urlencode(params) + extra_params + ')')
                wait_for_slideshow = True
            else:
                Logger.debug('Slideshow child count is the same, nothing to refresh...')
            t = threading.Thread(target=self._refresh_slideshow, args=(driveid, item_driveid, item_id, path, child_count, wait_for_slideshow,))
            t.setDaemon(True)
            t.start()
    
    def _refresh_slideshow(self, driveid, item_driveid, item_id, path, child_count, wait_for_slideshow):
        if wait_for_slideshow:
            Logger.debug('Waiting up to 10 minutes until the slideshow for folder %s starts...' % Utils.default(item_id, path))
            current_time = time.time()
            max_waiting_time = current_time + 10 * 60
            while not self.cancel_operation() and not xbmc.getCondVisibility('Slideshow.IsActive') and max_waiting_time > current_time:
                if self._system_monitor.waitForAbort(2):
                    break
                current_time = time.time()
            self._print_slideshow_info()
        interval = self._addon.getSetting('slideshow_refresh_interval')
        Logger.debug('Waiting up to %s minute(s) to check if it is needed to refresh the slideshow of folder %s...' % (interval, Utils.default(item_id, path)))
        current_time = time.time()
        target_time = current_time + int(interval) * 60
        while not self.cancel_operation() and target_time > current_time and xbmc.getCondVisibility('Slideshow.IsActive'):
            if self._system_monitor.waitForAbort(10):
                break
            current_time = time.time()
        self._print_slideshow_info()
        if not self.cancel_operation() and xbmc.getCondVisibility('Slideshow.IsActive'):
            try:
                self._slideshow(driveid, item_driveid, item_id, path, child_count)
            except Exception as e:
                Logger.error('Slideshow failed to auto refresh. Will be restarted when possible. Error: ')
                Logger.error(ExceptionUtils.full_stacktrace(e))
                self._refresh_slideshow(driveid, item_driveid, item_id, path, -1, wait_for_slideshow)
        else:
            Logger.notice('Slideshow is not running anymore or abort requested.')
        
    def _print_slideshow_info(self):
        if xbmc.getCondVisibility('Slideshow.IsActive'):
            Logger.debug('Slideshow is there...')
        elif self.cancel_operation():
            Logger.debug('Abort requested...')
        
    def _export_folder(self, driveid, item_driveid=None, item_id=None):
        if self._home_window.getProperty(self._addonid + 'exporting'):
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
                    self._home_window.setProperty(self._addonid + 'exporting', 'true')
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
    
    def play(self, driveid, item_driveid=None, item_id=None):
        find_subtitles = self._addon.getSetting('set_subtitle') == 'true' and self._content_type == 'video'
        item = self.get_item(driveid, item_driveid, item_id, find_subtitles=find_subtitles)
        file_name = Utils.unicode(item['name'])
        list_item = xbmcgui.ListItem(file_name)
        if 'audio' in item:
            list_item.setInfo('music', item['audio'])
        elif 'video' in item:
            list_item.addStreamInfo('video', item['video'])
        list_item.select(True)
        list_item.setPath(DownloadServiceUtil.build_download_url(self._addonid, driveid, item_driveid, item_id, urllib.quote(file_name)))
        list_item.setProperty('mimetype', Utils.get_safe_value(item, 'mimetype'))
        if find_subtitles and 'subtitles' in item:
            subtitles = []
            for subtitle in item['subtitles']:
                subtitles.append(DownloadServiceUtil.build_download_url(self._addonid, driveid, Utils.default(Utils.get_safe_value(subtitle, 'drive_id'), driveid), subtitle['id'], urllib.quote(subtitle['name'])))
            list_item.setSubtitles(subtitles)
        xbmcplugin.setResolvedUrl(self._addon_handle, True, list_item)
    
    def _handle_exception(self, ex):
        stacktrace = ExceptionUtils.full_stacktrace(ex)
        rex = ExceptionUtils.extract_exception(ex, RequestException)
        uiex = ExceptionUtils.extract_exception(ex, UIException)
        httpex = ExceptionUtils.extract_exception(ex, HTTPError)
        
        line1 = self._common_addon.getLocalizedString(32027)
        line2 = Utils.unicode(ex)
        line3 = self._common_addon.getLocalizedString(32016)
        
        if uiex:
            line1 = self._common_addon.getLocalizedString(int(Utils.str(uiex)))
            line2 = Utils.unicode(uiex.root_exception)
        elif rex and rex.response:
            line1 += ' ' + Utils.unicode(rex)
            line2 = ExceptionUtils.extract_error_message(rex.response)
        
        show_error_dialog = True
        send_report = self._common_addon.getSetting('report_error') == 'true'
        add_account_cmd = 'RunPlugin('+self._addon_url + '?' + urllib.urlencode({'action':'_add_account', 'content_type': self._content_type})+')'
        if isinstance(ex, AccountNotFoundException) or isinstance(ex, DriveNotFoundException):
            show_error_dialog = False
            if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32063) % '\n'):
                xbmc.executebuiltin(add_account_cmd)
        elif rex and httpex:
            if httpex.code >= 500:
                line1 = self._common_addon.getLocalizedString(32035)
                line3 = self._common_addon.getLocalizedString(32038)
            elif httpex.code >= 400:
                driveid = self._addon_params['driveid']
                self._account_manager.load()
                account = self._account_manager.get_account_by_driveid(driveid)
                drive = self._account_manager.get_drive_by_driveid(driveid)
                if Signin._signin_url in rex.request or httpex.code == 401:
                    send_report = False
                    show_error_dialog = False
                    if self._dialog.yesno(self._addon_name, self._common_addon.getLocalizedString(32046) % (self._get_display_name(account, drive), '\n')):
                        xbmc.executebuiltin(add_account_cmd)
                elif httpex.code == 403:
                    line1 = self._common_addon.getLocalizedString(32019)
                    line2 = line3 = None
                elif httpex.code == 404:
                    line1 = self._common_addon.getLocalizedString(32037)
                    line2 = line2 = None
                else:
                    line1 = self._common_addon.getLocalizedString(32036)
                    line3 = self._common_addon.getLocalizedString(32038)
        report = '[%s] [%s]\n\n%s\n%s\n%s\n\n%s' % (self._addonid, self._addon_version, line1, line2, line3, stacktrace)
        if rex:
            report += '\n\n%s\nResponse:\n%s' % (rex.request, rex.response)
        report += '\n\nshow_error_dialog: %s' % show_error_dialog
        Logger.error(report)
        if send_report:
            self._send_report(report)
        if show_error_dialog:
            self._dialog.ok(self._addon_name, line1, line2, line3)
    
    def _send_report(self, report):
        t = threading.Thread(target=ErrorReport().send_report, args=(report,))
        t.setDaemon(True)
        t.start()
    
    def _open_common_settings(self):
        self._common_addon.openSettings()
        
    def route(self):
        try:
            Logger.notice(self._addon_params)
            self._action = Utils.get_safe_value(self._addon_params, 'action')
            if self._action:
                method = getattr(self, self._action)
                arguments = {}
                for name in inspect.getargspec(method)[0]:
                    if name in self._addon_params:
                        arguments[name] = self._addon_params[name]
                method(**arguments)
            else:
                self.list_accounts()
        except Exception as ex:
            self._handle_exception(ex)
        finally:
            self._progress_dialog.close()
            self._progress_dialog_bg.close()
            self._export_progress_dialog_bg.close()
            if self._exporting:
                self._home_window.clearProperty(self._addonid + 'exporting')


