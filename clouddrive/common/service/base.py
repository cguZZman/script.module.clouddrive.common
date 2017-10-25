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
from clouddrive.common.utils import Utils
import threading


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
    version = None
    def __init__(self, server_address, RequestHandlerClass, service, data=None):
        self.data = data
        self.service = service
        self.daemon_threads = True
        ThreadingTCPServer.__init__(self, server_address, RequestHandlerClass)
        
    
class BaseHandler(BaseHTTPRequestHandler):
    content_type = 'text/html; charset=UTF-8'
    response_code_sent = False
    response_headers_block_sent = False
    
    def __init__(self, request, client_address, server):
        self.protocol_version = 'HTTP/1.1'
        self.server_version = KodiUtils.get_addon_info('id') + '/' + KodiUtils.get_addon_info('version')
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
    
    def write_response(self, code, message=None, content='', headers={}):
        if not isinstance(content, basestring):
            content = str(content)
        content_length = len(content)
        self.send_response(code, message)
        self.send_header('content-length', content_length)
        self.send_header('content-type', self.content_type)
        self.send_header('connection', 'close')
        message_id = self.headers.getheader('message-id')
        if message_id:
            self.send_header('message-id', message_id)
        for key in headers:
            self.send_header(key, headers[key])
        self.end_headers()
        if self.command != 'HEAD' and code >= 200 and code not in (204, 304):
            self.wfile.write(content)
            Logger.notice('[%s][%s][%s][%s][%s] [write_response]:\n%s\n%s' % (self.server.service._service_name, message_id, threading.current_thread().name, self, content_length, content,self.wfile._wbuf))
    
    def send_response(self, code, message=None):
        if self.response_code_sent:
            raise InvalidResponseException('response code already sent')
        BaseHTTPRequestHandler.send_response(self, code, message)
        self.response_code_sent = True
        
    def send_header(self, keyword, value):
        if self.response_headers_block_sent:
            raise InvalidResponseException('Response headers block already sent')
        BaseHTTPRequestHandler.send_header(self, keyword, value)
    
    def end_headers(self):
        BaseHTTPRequestHandler.end_headers(self)
        self.response_headers_block_sent = True
     
    def log_message(self, format, *args):
        #Logger.notice("[%s.service] %s\n" % (self.server.service._service_name, format%args))
        return
        
    def log_error(self, format, *args):
        Logger.error("[%s.service] %s\n" % (self.server.service._service_name, format%args))
        
    def do_HEAD(self):
        self.do_GET()

class InvalidResponseException(Exception):
    pass