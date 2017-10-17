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

import BaseHTTPServer
import SocketServer
import socket
import threading

from clouddrive.common.ui.logger import Logger
import xbmc
import xbmcaddon
import json
from clouddrive.common.utils import Utils


class MessagingService(object):
    _interface = '127.0.0.1'
    _addon = None
    _addon_id = None
    listener = None
    
    def __init__(self, listener):
        SocketServer.TCPServer.allow_reuse_address = True
        self._addon = xbmcaddon.Addon()
        self._addon_id = self._addon.getAddonInfo('id')
        self.listener = listener
    
    def get_unused_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self._interface, 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    def start_message_server(self):
        messaging_service_port = self.get_unused_port()
        self._addon.setSetting('messaging.sourceservice.port', str(messaging_service_port))
        Logger.notice('Messaging Service Port: ' + str(messaging_service_port))
        message_server = MessagingServer((self._interface, messaging_service_port), MessagingRequestHandler, self.listener)
        message_server.server_activate()
        message_server.timeout = 1
        download_service_thread = threading.Thread(target=message_server.serve_forever)
        download_service_thread.daemon = True
        download_service_thread.start()
        return message_server
        
    def start(self):
        message_server = self.start_message_server()
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                message_server.shutdown()
                break
        message_server.server_close()
        message_server.socket.close()
        message_server.shutdown()
        Logger.notice('Messaging Service Stopped.')

class MessagingServer(SocketServer.TCPServer):
    listener = None
    def __init__(self, server_address, RequestHandlerClass, listener):
        self.listener = listener
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
    
class MessagingRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    
    def log_message(self, format, *args):
        #Logger.notice("%s\n" % (format%args))
        return
        
    def log_error(self, format, *args):
        Logger.error("%s\n" % (format%args))
        
    def do_POST(self):
        self.send_response(200)
        size = int(self.headers.getheader('content-length', 0))
        message = self.rfile.read(size)
        response = self.server.listener.on_message(message, self)
        if type(response) is list or type(response) is dict:
            response = json.dumps(response)
        elif type(response) is not str:
            response = Utils.str(response)
        self.end_headers()
        self.wfile.write(response)
        return

class MessagingListerner(object):
    def on_message(self, message, handler):
        raise NotImplementedError()
        