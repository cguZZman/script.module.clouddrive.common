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


from urllib2 import HTTPError

import cherrypy
from clouddrive.common.exception import ExceptionUtils
from clouddrive.common.service.cherrypy.rpc import RpcUtil
from clouddrive.common.ui.logger import Logger


@cherrypy.expose   
class Download(object):
    name = 'download'
    app_config = {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
    
    def _cp_dispatch(self, vpath):
        if len(vpath) > 3:
            cherrypy.request.params['name'] = vpath.pop()
            cherrypy.request.params['item_id'] = vpath.pop()
            cherrypy.request.params['item_driveid'] = vpath.pop()
            cherrypy.request.params['driveid'] = vpath.pop()
            cherrypy.request.params['addonid'] = vpath.pop()
            return self
    
    def GET(self, **kwargs):
        try:
            Logger.notice('Download request: %s' % kwargs)
            kwargs['include_download_info'] = True
            item = RpcUtil.execute_remote_method(kwargs['addonid'], 'get_item', kwargs = kwargs)
            Logger.notice('Item returned: %s' % item)
        except Exception as e:
            httpex = ExceptionUtils.extract_exception(e, HTTPError)
            if httpex:
                code = httpex.code
            else:
                code = 500
            message = ExceptionUtils.full_stacktrace(e)
            Logger.error('DownloadException:')
            Logger.error(message)
            raise cherrypy.HTTPError(code, message)
        raise cherrypy.HTTPRedirect(item['download_info']['url'], status=307)
        