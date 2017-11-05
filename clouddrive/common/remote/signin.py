#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
# 
# This file is part of Cloud Drive Common Module for Kodi
# 
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import base64
import urllib

from clouddrive.common.remote.request import Request


class Signin(object):
    _signin_url = 'https://kodi-login.herokuapp.com'
    
    def create_pin(self, provider_name, request_params={}):
        body = urllib.urlencode({'provider': provider_name})
        return Request(self._signin_url + '/pin', body, None, **request_params).request_json()
    
    def fetch_tokens_info(self, pin_info, request_params={}):
        headers = {'authorization': 'Basic ' + base64.b64encode(':' + pin_info['password'])}
        return Request(self._signin_url + '/pin/' + pin_info['pin'], None, headers, **request_params).request_json()

    def refresh_tokens(self, provider_name, refresh_token, request_params={}):
        body = urllib.urlencode({'provider': provider_name, 'refresh_token': refresh_token})
        return Request(self._signin_url + '/refresh', body, None, **request_params).request_json()
