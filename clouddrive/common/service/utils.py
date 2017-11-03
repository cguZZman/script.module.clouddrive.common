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
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.ui.logger import Logger
import time
import uuid
from threading import Thread
from clouddrive.common.remote.request import Request

class ServiceUtil(object):
    @staticmethod
    def run(services):
        if type(services) != list:
            services = [services]
        for service in services:
            thread = Thread(target=service.start, name='service-%s' % service.name)
            thread.daemon = True
            thread.start()
        monitor = KodiUtils.get_system_monitor()
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):
                break
        for service in services:
            service.stop()

class DownloadServiceUtil(object):
    @staticmethod
    def build_download_url(addonid, driveid, item_driveid, item_id, name):
        #return 'http://127.0.0.1:%s/download/%s/%s/%s/%s/%s' % (KodiUtils.get_service_port('download', 'script.module.clouddrive.common'), addonid, driveid, item_driveid, item_id, name)
        return 'http://127.0.0.1:%s/%s/%s/%s/%s/%s' % (KodiUtils.get_service_port('download', 'script.module.clouddrive.common'), addonid, driveid, item_driveid, item_id, name)
    
class RpcUtil(object):
    
    @staticmethod
    def rpc(addonid, method, args=None, kwargs=None, request_id=None):
        if not request_id:
            request_id = str(uuid.uuid4())
        cmd = {'method': method}
        if args:
            cmd.update({'args': args})
        if kwargs:
            cmd.update({'kwargs': kwargs})
        cmd = repr(cmd)
        result = eval(Request('http://localhost:' + KodiUtils.get_service_port('rpc', addonid), cmd, {'content-length': len(cmd), 'request-id': request_id}, tries=1).request())
        return result

    '''
    @staticmethod
    def execute_remote_method(addonid, method, args=[], kwargs={}, exec_id=None):
        if not exec_id:
            exec_id = uuid.uuid4()
        Logger.notice('Executing remote method with script %s...' % method)
        KodiUtils.run_script(addonid, {
            'action' : 'on_execute_method',
            'method' : method,
            'exec_id' : exec_id,
            'args' : repr(args),
            'kwargs' : repr(kwargs)
        }, True)
        Logger.notice('executed')
        key = '%s-%s' % (addonid, exec_id)
        status_key = '%s.status' % key
        home_window = KodiUtils.get_window(10000)
        timeout = time.time() + 15
        Logger.notice('waiting to start...')
        while timeout > time.time():
            if home_window.getProperty(status_key):
                break
        Logger.notice('started')
        status = home_window.getProperty(status_key)
        if status:
            timeout = time.time() + 60
            Logger.notice('waiting to finish...')
            while status == 'in-progress' and timeout > time.time():
                status = home_window.getProperty('%s.status' % key)
            if status != 'in-progress':
                result = home_window.getProperty('%s.result' % key)
                if status == 'success':
                    return eval(result)
                else:
                    raise Exception(result)
            else:
                raise Exception('MethodExecution: Finish timeout')
        else:
            raise Exception('MethodExecution: Start timeout')
    '''