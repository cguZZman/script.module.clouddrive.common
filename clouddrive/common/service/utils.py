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


class DownloadServiceUtil(object):
    @staticmethod
    def build_download_url(addonid, driveid, item_driveid, item_id, name):
        return 'http://127.0.0.1:%s/download/%s/%s/%s/%s/%s' % (KodiUtils.get_server_service_port(), addonid, driveid, item_driveid, item_id, name)
        