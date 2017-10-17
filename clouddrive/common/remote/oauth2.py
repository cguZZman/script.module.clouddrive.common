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

import re
import time
import urllib
import urllib2

from clouddrive.common.exception import ExceptionUtils, RequestException
from clouddrive.common.remote.request import Request
from clouddrive.common.utils import Utils


class OAuth2(object):
    
    def _get_api_url(self):
        raise NotImplementedError()

    def _get_request_headers(self):
        raise NotImplementedError()
    
    def get_access_tokens(self):
        raise NotImplementedError()
    
    def refresh_access_tokens(self, request_params={}):
        raise NotImplementedError()
    
    def persist_access_tokens(self, access_tokens):
        raise NotImplementedError()
    
    def _on_exception(self, request, e, original_on_exception):
        ex = ExceptionUtils.extract_exception(e, urllib2.HTTPError)
        if ex and ex.code >= 400 and ex.code <= 599 and ex.code != 503:
            request.tries = request.current_tries
        if original_on_exception:
            original_on_exception(request, e)
            
    def _wrap_on_exception(self, request_params={}):
        original_on_exception = Utils.get_safe_value(request_params, 'on_exception', None)
        request_params['on_exception'] = lambda request, e: self._on_exception(request, e, original_on_exception)
    
    def _validate_access_tokens(self, access_tokens, url, data, request_headers):
        if not access_tokens or not 'access_token' in access_tokens or not 'refresh_token' in access_tokens or not 'expires_in' in access_tokens or not 'date' in access_tokens:
            raise RequestException('Access tokens provided are not valid: ' + Utils.str(access_tokens), None, 'Request URL: '+Utils.str(url)+'\nRequest data: '+Utils.str(data)+'\nRequest headers: '+Utils.str(request_headers), None)
    
    def _build_url(self, method, path, parameters):
        url = self._get_api_url()
        if re.search("^https?://", path):
            url = path
        else:
            if not (re.search("^\/", path)):
                path = '/' + path
            url += path
        if method == 'get' and parameters:
            url += '?' + parameters
        return url
    
    def request(self, method, path, parameters={}, request_params={}, access_tokens={}):
        encoded_parameters = urllib.urlencode(parameters)
        url = self._build_url(method, path, encoded_parameters)
        self._wrap_on_exception(request_params)
        data = None if method == 'get' else encoded_parameters
        request_headers = Utils.default(self._get_request_headers(), {})
        if not access_tokens:
            access_tokens = self.get_access_tokens()
        self._validate_access_tokens(access_tokens, url, data, request_headers)
        if time.time() > (access_tokens['date'] + access_tokens['expires_in']):
            access_tokens = self.refresh_access_tokens(request_params)
            self._validate_access_tokens(access_tokens, 'refresh_access_tokens', 'Unknown', 'Unknown')
            self.persist_access_tokens(access_tokens)
        request_headers['authorization'] = 'bearer ' + access_tokens['access_token']
        return Request(url, data, request_headers, **request_params).request_json()
    
    def get(self, path, **kwargs):
        return self.request('get', path, **kwargs)
    
    def post(self, path, **kwargs):
        return self.request('post', path, **kwargs)