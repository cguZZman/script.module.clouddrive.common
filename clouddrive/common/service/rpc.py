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

import inspect
import time
import uuid

from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.ui.logger import Logger


class RemoteProcessCallable(object):
    def on_execute_method(self, exec_id, method, args='[]', kwargs='{}'):
        Logger.notice('now on_execute_method %s...' % method)
        home_window = KodiUtils.get_window(10000)
        key = '%s-%s' % (self._addonid, exec_id)
        status_key = '%s.status' % key
        result_key = '%s.result' % key
        try:
            home_window.setProperty(status_key, 'in-progress')
            args = eval(args)
            kwargs = eval(kwargs)
            method = getattr(self, method)
            fkwargs = {}
            for name in inspect.getargspec(method)[0]:
                if name in kwargs:
                    fkwargs[name] = kwargs[name]
            home_window.setProperty(result_key, repr(method(*args, **fkwargs)))
            home_window.setProperty(status_key, 'success')
        except Exception as e:
            home_window.setProperty(result_key, repr(e))
            home_window.setProperty(status_key, 'fail')
            raise e
        
class RpcUtil(object):
    @staticmethod
    def execute_remote_method(addonid, method, args=[], kwargs={}, exec_id=None):
        if not exec_id:
            exec_id = uuid.uuid4()
        Logger.notice('Executing remote method with script %s...' % method)
        KodiUtils.run_plugin(addonid, {
            'action' : 'on_execute_method',
            'method' : method,
            'exec_id' : exec_id,
            'args' : repr(args),
            'kwargs' : repr(kwargs)
        })
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
        