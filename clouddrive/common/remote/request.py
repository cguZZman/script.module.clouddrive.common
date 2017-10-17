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

import json
import ssl
import time
import urllib2

from clouddrive.common.exception import RequestException
from clouddrive.common.ui.logger import Logger
from clouddrive.common.utils import Utils


try:
    if hasattr(ssl, '_create_unverified_context'):
        ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass

class Request(object):
    _DEFAULT_RESPONSE = '{}'
    url = None
    data = None
    headers = None
    tries = 1
    current_tries = 0
    delay = 0
    current_delay = 0
    backoff = 0
    before_request = None
    on_exception = None
    on_failure = None
    on_success = None
    on_complete = None
    exceptions = None
    cancel_operation = None
    waiting_retry = None
    wait = None
    success = False
    response_url = None
    response_code = None
    response_info = None
    response_text = None
    
    def __init__(self, url, data, headers, tries=3, delay=5, backoff=2, exceptions=None, before_request=None, on_exception=None, on_failure=None, on_success=None, on_complete=None, cancel_operation=None, waiting_retry=None, wait=None):
        self.url = url
        self.data = data
        self.headers = headers
        self.tries = tries
        self.current_tries = tries
        self.delay = delay
        self.current_delay = delay
        self.backoff = backoff
        self.before_request = before_request
        self.on_exception = on_exception
        self.on_failure = on_failure
        self.on_success = on_success
        self.on_complete = on_complete
        self.exceptions = exceptions
        self.cancel_operation = cancel_operation
        self.waiting_retry = waiting_retry
        self.wait = wait
    
    def request(self):
        self.response_text = self._DEFAULT_RESPONSE
        if not self.exceptions:
            self.exceptions = Exception
        if not self.wait:
            self.wait = time.sleep
        if not self.headers:
            self.headers = {}
        for i in xrange(self.tries):
            self.current_tries = i + 1
            if self.before_request:
                self.before_request(self)
            if self.cancel_operation and self.cancel_operation():
                break
            request_report = 'Request URL: ' + Utils.str(self.url)
            request_report += '\nRequest data: ' + Utils.str(self.data)
            request_report += '\nRequest headers: ' + Utils.str(self.headers)
            #Logger.debug(request_report);
            try:
                req = urllib2.Request(self.url, self.data, self.headers)
                response = urllib2.urlopen(req)
                self.response_text = response.read()
                self.response_url = response.geturl()
                self.response_code = response.getcode()
                self.response_info = response.info()
                self.success = True
                break
            except self.exceptions as e:
                root_exception = e
                Logger.debug('Request exception: ' + Utils.unicode(e))
                response_report = ''
                if isinstance(e, urllib2.HTTPError):
                    response_report = e.read()
                    Logger.debug('Request response: ' + Utils.unicode(e))
                rex = RequestException(Utils.str(e), root_exception, request_report, Utils.str(response_report))
                if self.on_exception:
                    self.on_exception(self, rex)
                if self.cancel_operation and self.cancel_operation():
                    break
                if self.current_tries == self.tries:
                    if self.on_failure:
                        self.on_failure(self)
                    if self.on_complete:
                        self.on_complete(self)
                    Logger.debug('Raising exception...')
                    raise rex
                current_time = time.time()
                max_waiting_time = current_time + self.current_delay
                while (not self.cancel_operation or not self.cancel_operation()) and max_waiting_time > current_time:
                    remaining = round(max_waiting_time-current_time)
                    if self.waiting_retry:
                        self.waiting_retry(self, remaining)
                    self.wait(1)
                    current_time = time.time()
                self.current_delay *= self.backoff
        if self.success and self.on_success:
            self.on_success(self)
        if self.on_complete:
            self.on_complete(self)
        #Logger.debug('Response text: ' + Utils.str(self.response_text))
        return self.response_text
        
    def request_json(self):
        return json.loads(Utils.default(self.request(), self._DEFAULT_RESPONSE))

    def get_response_text_as_json(self):
        return json.loads(Utils.default(self.response_text, self._DEFAULT_RESPONSE))