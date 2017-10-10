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
import time

from clouddrive.common.remote.oauth2 import OAuth2
from clouddrive.common.remote.signin import Signin


class Provider(OAuth2):
    name = ''
    _signin = Signin()
    
    def __init__(self, name):
        self.name = name
        
    def create_pin(self, request_params={}):
        return self._signin.create_pin(self.name, request_params)
    
    def retrieve_tokens_info(self, pin_info, request_params={}):
        tokens_info = self._signin.retrieve_tokens_info(pin_info, request_params)
        if tokens_info:
            tokens_info['date'] = time.time()
        return tokens_info
    
    def refresh_access_tokens(self, request_params={}):
        pass
    
    def account(self, request_params={}, access_tokens={}):
        raise NotImplementedError()
    
    def drives(self, request_params={}, access_tokens={}):
        raise NotImplementedError()
    
    def drive_type_name(self, drive_type):
        return drive_type
