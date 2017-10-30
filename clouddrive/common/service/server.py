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
from SocketServer import ThreadingTCPServer
import socket

import cherrypy
from clouddrive.common.ui.logger import Logger
from clouddrive.common.ui.utils import KodiUtils

class ServerService(object):
    apps = None
    
    def __init__(self, apps=[]):
        self.name = 'server'
        self.apps = apps
        if type(self.apps) != list:
            self.apps = [self.apps]
    
    def get_free_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((self._interface, 0))
        port = sock.getsockname()[1]
        sock.close()
        return port
    
    def get_port(self):
        return int(KodiUtils.get_addon_setting('port_directory_listing'))
    
    def start(self):
        port = self.get_port()
        KodiUtils.set_addon_setting(self.name + '.service.port', str(port))
        cherrypy.config.update({'server.socket_port': port})
        for app in self.apps:
            cherrypy.tree.mount(app, '/%s' % app.name, {'/' : app.app_config})
        cherrypy.engine.signals.subscribe()
        cherrypy.engine.start()
        Logger.notice('Server Service started in port %s' % (port))
        cherrypy.engine.block()
    
    def stop(self):
        cherrypy.engine.exit()
        Logger.notice('Server Service stopped')
    

class BaseServer(ThreadingTCPServer):
    data = None
    service = None
    version = None
    def __init__(self, server_address, RequestHandlerClass, service, data=None):
        self.data = data
        self.service = service
        self.daemon_threads = True
        ThreadingTCPServer.__init__(self, server_address, RequestHandlerClass)
        
    
