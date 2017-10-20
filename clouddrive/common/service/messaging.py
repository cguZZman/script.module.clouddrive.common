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
import urllib2

from clouddrive.common.exception import ExceptionUtils
from clouddrive.common.service.base import BaseService, BaseHandler
from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils


class MessagingService(BaseService):
    def __init__(self, listener):
        super(MessagingService, self).__init__(listener)
        self._service_name = 'messaging'
        self._handler = MessagingRequestHandler
    
class MessagingRequestHandler(BaseHandler):
    def do_POST(self):
        self.send_response(200)
        size = int(self.headers.getheader('content-length', 0))
        message = self.rfile.read(size)
        response = self.server.data.on_message(message, self)
        if type(response) is list or type(response) is dict:
            response = json.dumps(response)
        elif type(response) is not str:
            response = Utils.str(response)
        self.end_headers()
        self.wfile.write(response)
        return

class CloudDriveMessagingListerner(object):
    def on_message(self, message, handler):
        if message:
            msg = json.loads(message)
            args = Utils.get_safe_value(msg, 'args', [])
            kwargs = Utils.get_safe_value(msg, 'kwargs', {})
            try:
                result = repr(getattr(self, msg['method'])(*args, **kwargs))
            except Exception as e:
                result = False
                Logger.error(ExceptionUtils.full_stacktrace(e))
            return result
        return False

class MessagingServiceUtil(object):
    @staticmethod
    def send_message(addon, message):
        try:
            req = urllib2.Request('http://localhost:' + addon.getSetting('messaging.service.port'), message, {'content-length': len(message)})
            result = eval(urllib2.urlopen(req).read())
        except Exception as e:
            result = False
            Logger.error(ExceptionUtils.full_stacktrace(e))
        return result
        
        