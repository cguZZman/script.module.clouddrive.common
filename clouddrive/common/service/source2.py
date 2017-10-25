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

import urllib

from clouddrive.common.html import XHTML
from clouddrive.common.service.base import BaseService, BaseHandler
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
from clouddrive.common.ui.logger import Logger
from clouddrive.common.exception import ExceptionUtils
from urllib2 import HTTPError
import threading
from clouddrive.common.service.rpc import RpcUtil



class SourceService(BaseService):
    def __init__(self):
        super(SourceService, self).__init__()
        self._service_name = 'source'
        self._handler = Source
    
    def get_port(self):
        return int(KodiUtils.get_addon_setting('port_directory_listing'))
    
    def start(self):
        if KodiUtils.get_addon_setting('allow_directory_listing') == 'true':
            super(SourceService, self).start()
    
class Source(BaseHandler):
    account_manager = None
    kilobyte = 1024.0
    megabyte = kilobyte*kilobyte
    gigabyte = megabyte*kilobyte
    
    def open_table(self, title):
        title = urllib.unquote(title)
        html = XHTML('html')
        html.head.title(title)
        body = html.body
        body.h1(title)
        table = body.table()
        row = table.tr
        row.th.a('Name', href='?C=N;O=D')
        row.th.a('Last modified', href='?C=M;O=A')
        row.th.a('Size', href='?C=S;O=A')
        row.th.a('Description', href='?C=D;O=A')
        row = table.tr
        row.th(colspan='4').hr()
        return html, table
    
    def add_row(self, table, file_name, date='  - ', size='  - ', description='&nbsp;'):
        row = table.tr
        row.td.a(file_name, href=urllib.quote(file_name))
        row.td(date, align='right')
        row.td(size, align='right')
        row.td(description, escape=False)
    
    def close_table(self, table):
        table.tr.th(colspan='4').hr()
    
    def get_size(self, size):
        unit = ''
        if size > self.gigabyte:
            size = size / self.gigabyte
            unit = 'G'
        elif size > self.megabyte:
            size = size / self.megabyte
            unit = 'M'
        elif size > self.kilobyte:
            size = size / self.kilobyte
            unit = 'K'
        elif size < 0:
            return '-'
        return ("%.2f" % size) + unit
    
    def get_cloud_drive_addons(self):
        addons = []
        addonid = KodiUtils.get_addon_info('id')
        response = KodiUtils.execute_json_rpc('Addons.GetAddons', {'type':'xbmc.python.pluginsource', 'enabled': True, 'properties': ['dependencies', 'name']})
        for addon in Utils.get_safe_value(Utils.get_safe_value(response, 'result', {}), 'addons', []):
            for dependency in addon['dependencies']:
                if dependency['addonid'] == addonid:
                    addons.append(addon)
                    break
        return addons
        
    def show_addon_list(self):
        html, table = self.open_table('Index of /')
        for addon in self.get_cloud_drive_addons():
            self.add_row(table, addon['name'] + '/')
        self.close_table(table)
        self.write_response(200, content = html)
    
    def get_drive_list(self, addonid):
        drives = []
        accounts = RpcUtil.execute_remote_method(addonid, 'get_accounts')
        for account_id in accounts:
            account = accounts[account_id]
            for drive in account['drives']:
                drives.append(drive)
        return drives
    
    def get_addonid(self, addon_name):
        addons = self.get_cloud_drive_addons()
        addonid = None
        for addon in addons:
            if addon['name'] == addon_name:
                addonid = addon['addonid']
                break
        return addonid
    
    def get_driveid(self, addonid, drive_name):
        driveid = None
        drives = self.get_drive_list(addonid)
        drive_name = urllib.unquote(drive_name)
        for drive in drives:
            if drive['display_name'] == drive_name:
                driveid = drive['id']
                break
        return driveid
                
    
    def show_drives(self, addon_name):
        addonid = self.get_addonid(addon_name)
        response_code = 200
        if addonid:
            html, table = self.open_table('Index of /'+addon_name+'/')
            self.add_row(table, '../')
            drives = self.get_drive_list(addonid)
            for drive in drives:
                self.add_row(table, drive['display_name'] + '/')
            self.close_table(table)
        else:
            response_code = 404
            html = 'Cloud Drive addon "%s" does not exist' % addon_name
        self.write_response(response_code, content=html)
    
    def process_path(self, addon_name, drive_name, path):
        addonid = self.get_addonid(addon_name)
        headers = {}
        if addonid:
            driveid = self.get_driveid(addonid, drive_name)
            if driveid:
                parts = self.path.split('/')
                if parts[len(parts)-1]:
                    response_code = 303
                    headers['location'] = self.get_download_url(addonid, driveid, path)
                else:
                    response_code = 200
                    response = self.show_folder(addonid, driveid, path)
            else:
                response_code = 404
                response = 'Drive "%s" does not exist for addon "%s"' % (drive_name, addon_name)
        else:
            response_code = 404
            response = 'Cloud Drive addon "%s" does not exist' % addon_name
        self.write_response(response_code, content=response, headers=headers)

    def show_folder(self, addonid, driveid, path):
        path_len = len(path)
        if path_len > 1:
            path = path[:path_len-1]
        items = RpcUtil.execute_remote_method(addonid, 'get_folder_items', kwargs={'driveid': driveid, 'path': path})
        html, table = self.open_table('Index of ' + self.path)
        self.add_row(table, '../')
        for item in items:
            file_name = Utils.str(item['name'])
            if 'folder' in item:
                file_name += '/'
            date = Utils.default(Utils.get_safe_value(item, 'last_modified_date'), '  - ')
            size = self.get_size(Utils.default(Utils.get_safe_value(item, 'size'), -1))
            description = Utils.default(Utils.get_safe_value(item, 'description'), '&nbsp;')
            self.add_row(table, file_name, date, size, description)
        self.close_table(table)
        return html
    
    def get_download_url(self, addonid, driveid, path):
        item = RpcUtil.execute_remote_method(addonid, 'get_item', kwargs={'driveid': driveid, 'path': path, 'include_download_info': True})
        return item['download_info']['url']
        
    def do_GET(self):
        try:
            message_id = self.headers.getheader('message-id')
            Logger.notice('[%s][%s][%s][%s] Source request incoming: %s' % (self.server.service._service_name, message_id, threading.current_thread().name, self, self.path))
            parts = self.path.split('/')
            addon_name = parts[1]
            if addon_name:
                size = len(parts)
                if size == 2 or (size == 3 and not parts[2]):
                    self.show_drives(addon_name)
                else:
                    drive_name = parts[2]
                    path = self.path[len(addon_name)+len(drive_name)+2:]
                    self.process_path(addon_name, drive_name, path)
            else:
                self.show_addon_list()
        except Exception as e:
            httpex = ExceptionUtils.extract_exception(e, HTTPError)
            if httpex:
                response_code = httpex.code
            else:
                response_code = 500
            response = ExceptionUtils.full_stacktrace(e)
            Logger.error('[%s][%s][%s][%s][%s]\nException:\n%s' % (self.server.service._service_name, message_id, threading.current_thread().name, self, self.path, response))
            self.write_response(response_code, content=response)
            
        
