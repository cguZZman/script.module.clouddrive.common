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
import traceback



class WrappedException(Exception):
    root_exception = None
    root_tb = None
    def __init__(self, message, root_exception):
        super(WrappedException, self).__init__(message)
        self.root_exception = root_exception
        if root_exception:
            self.root_tb = traceback.format_exc()

class RequestException(WrappedException):
    request = None
    response = None
    def __init__(self, message, root_exception, request, response):
        super(RequestException, self).__init__(message, root_exception)
        self.request = request
        self.response = response
        
class UIException(WrappedException):
    def __init__(self, message_id, root_exception):
        super(UIException, self).__init__(message_id, root_exception)

class ExceptionUtils:
    @staticmethod
    def full_stacktrace(e):
        tb = traceback.format_exc()
        while e and isinstance(e, WrappedException):
            if e.root_tb:
                tb += 'Root cause:\n' + e.root_tb
            e = e.root_exception
        return tb
    
    @staticmethod
    def extract_exception(e, exception_type):
        exception = None
        while e:
            if isinstance(e, exception_type):
                exception = e
                break
            e = None if not isinstance(e, WrappedException) else e.root_exception
        return exception