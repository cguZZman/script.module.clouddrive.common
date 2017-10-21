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
    51 Franklin Street, OFifth Floor, Boston, MA 02110-1301 USA.

    Created on Mar 1, 2015
    @author: Carlos Guzman (cguZZman) carlosguzmang@hotmail.com
'''
from BaseHTTPServer import BaseHTTPRequestHandler
from SocketServer import ThreadingTCPServer
import SocketServer
import socket
from threading import Thread

from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils


class BaseService(object):
    _interface = '127.0.0.1'
    _server = None
    _thread = None
    _service_name = ''
    _handler = None
    data = None
    
    def __init__(self, data=None):
        SocketServer.TCPServer.allow_reuse_address = True
        self.data = data
    
    def get_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self._interface, 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    def start(self):
        port = self.get_port()
        KodiUtils.set_addon_setting(self._service_name + '.service.port', str(port))
        self._server = BaseServer((self._interface, port), self._handler, self, self.data)
        self._server.server_activate()
        self._server.timeout = 1
        self._thread = Thread(target=self._server.serve_forever)
        self._thread.daemon = True
        self._thread.start()
        Logger.notice('Service [%s] started in port %s' % (self._service_name, port))
    
    def stop(self):
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            Logger.notice('Service [%s] stopped' % self._service_name)
    
    @staticmethod
    def run(services):
        for service in services:
            service.start()
        monitor = KodiUtils.get_system_monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                break
        for service in services:
            service.stop()

class BaseServer(ThreadingTCPServer):
    data = None
    service = None
    def __init__(self, server_address, RequestHandlerClass, service, data=None):
        self.data = data
        self.service = service
        ThreadingTCPServer.__init__(self, server_address, RequestHandlerClass)
        
class BaseHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        Logger.notice("[%s.service] %s\n" % (self.server.service._service_name, format%args))
        return
        
    def log_error(self, format, *args):
        Logger.error("[%s.service] %s\n" % (self.server.service._service_name, format%args))
        
    def do_HEAD(self):
        self.do_GET()
    