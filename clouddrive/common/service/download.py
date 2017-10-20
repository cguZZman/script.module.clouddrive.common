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

import json
from urlparse import urlparse

from clouddrive.common.service.base import BaseService, BaseHandler
from clouddrive.common.service.messaging import MessagingServiceUtil
from clouddrive.common.ui.utils import UIUtils
from clouddrive.common.ui.logger import Logger
from clouddrive.common.exception import ExceptionUtils


class DownloadService(BaseService):
    def __init__(self):
        super(DownloadService, self).__init__()
        self._service_name = 'download'
        self._handler = Download
    
class Download(BaseHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        data = path.split('/')
        if len(data) > 3:
            try:
                message = json.dumps({
                    'method' : 'get_item',
                    'kwargs' : {
                        'driveid' : data[2],
                        'item_driveid' : data[3],
                        'item_id' : data[4],
                        'include_download_info' : True
                    }
                })
                item = MessagingServiceUtil.send_message(UIUtils.get_addon(data[1]), message)
                if item:
                    url = item['download_info']['url']
                    self.send_response(307)
                    self.send_header('location', url)
                else:
                    self.send_response(404)
            except Exception as e:
                Logger.error(ExceptionUtils.full_stacktrace(e))
                self.send_response(400)
        else:
            self.send_response(400)
        self.end_headers()
        return

class DownloadServiceUtil(object):
    @staticmethod
    def get_download_url(addon, driveid, item_driveid, item_id, name):
        return 'http://localhost:%s/%s/%s/%s/%s/%s' % (UIUtils.get_addon('script.module.clouddrive.common').getSetting('download.service.port'), addon.getAddonInfo('id'), driveid, item_driveid, item_id, name)
        
        