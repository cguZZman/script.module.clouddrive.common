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

from threading import Thread

from clouddrive.common.ui.utils import KodiUtils


class ServiceUtil(object):
    
    @staticmethod
    def run(services):
        if type(services) != list:
            services = [services]
        for service in services:
            thread = Thread(target=service.start, name='thread-%s' % service.name)
            thread.daemon = True
            thread.start()
        monitor = KodiUtils.get_system_monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                break
        for service in services:
            service.stop()