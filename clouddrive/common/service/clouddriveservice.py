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
import SocketServer
import socket
import threading

from clouddrive.common.service.download import Download
from clouddrive.common.service.source import Source
from clouddrive.common.ui.logger import Logger
import xbmc
import xbmcaddon


class CloudDriveService(object):
    _interface = '127.0.0.1'
    _common_addon = xbmcaddon.Addon('script.module.clouddrive.common')
    
    def __init__(self):
        SocketServer.TCPServer.allow_reuse_address = True
    
    def unused_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self._interface, 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    def start_download_server(self):
        download_service_port = self.unused_port()
        self._common_addon.setSetting('download.service.port', str(download_service_port))
        Logger.notice('Cloud Drive Common Download Service Port: ' + str(download_service_port))
        download_server = SocketServer.TCPServer((self._interface, download_service_port), Download)
        download_server.server_activate()
        download_server.timeout = 1
        download_service_thread = threading.Thread(target=download_server.serve_forever)
        download_service_thread.daemon = True
        download_service_thread.start()
        return download_server

    def start_source_server(self):
        if self._common_addon.getSetting('allow_directory_listing') == 'true':
            source_service_port = int(self._common_addon.getSetting('port_directory_listing'))
            source_server = SocketServer.TCPServer((self._interface, source_service_port), Source)
            source_server.server_activate()
            source_server.timeout = 1
            source_service_thread = threading.Thread(target=source_server.serve_forever)
            source_service_thread.daemon = True
            source_service_thread.start()
            Logger.notice('Cloud Drive Common Source Service Port: ' + str(source_service_port))
            return source_server
        
    def main(self):
        download_server = self.start_download_server()
        source_server = self.start_source_server()
        monitor = xbmc.Monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(2):
                download_server.shutdown()
                if source_server:
                    source_server.shutdown()
                break
        download_server.server_close()
        download_server.socket.close()
        download_server.shutdown()
        if source_server:
            source_server.server_close()
            source_server.socket.close()
            source_server.shutdown()
        Logger.notice('Cloud Drive Common Services Stopped.')
