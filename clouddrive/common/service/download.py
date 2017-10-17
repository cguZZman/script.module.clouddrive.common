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
from urlparse import urlparse

from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils
import xbmc
import xbmcaddon
import SocketServer
import socket
import threading
from clouddrive.common.remote.request import Request
import urllib2
import json


class DownloadService(object):
    _interface = '127.0.0.1'
    _addon = None
    _addon_name = None
    
    def __init__(self):
        SocketServer.TCPServer.allow_reuse_address = True
        self._addon = xbmcaddon.Addon()
        self._addon_name = self._addon.getAddonInfo('name')
    
    def get_unused_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self._interface, 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    def start_download_server(self):
        download_service_port = self.get_unused_port()
        self._addon.setSetting('download.sourceservice.port', str(download_service_port))
        Logger.notice('Download Service Port: ' + str(download_service_port))
        download_server = SocketServer.TCPServer((self._interface, download_service_port), Download)
        download_server.server_activate()
        download_server.timeout = 1
        download_service_thread = threading.Thread(target=download_server.serve_forever)
        download_service_thread.daemon = True
        download_service_thread.start()
        return download_server
        
    def start(self):
        download_server = self.start_download_server()
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                download_server.shutdown()
                break
        download_server.server_close()
        download_server.socket.close()
        download_server.shutdown()
        Logger.notice('Download Service Stopped.')

class Download(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.do_GET()
        
    def do_GET(self):
        path = urlparse(self.path).path
        Logger.notice('download requested = ' + path)
        data = path.split('/')
        addon = xbmcaddon.Addon(data[1])
        message = json.dumps({
            'action' : 'retrieve_download_url',
            'driveid' : data[2],
            'item_driveid' : data[3],
            'item_id' : data[4]
        })
        req = urllib2.Request('http://localhost:' + addon.getSetting('messaging.sourceservice.port'), message, {})
        response = urllib2.urlopen(req).read()
        response = json.loads(response)
        self.send_response(307)
        self.send_header('location', response['url'])
        self.end_headers()
        return

        