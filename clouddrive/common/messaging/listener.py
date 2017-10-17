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

from clouddrive.common.fetchableitem import FetchableItem
from clouddrive.common.service.messaging import MessagingListerner

class CloudDriveMessagingListerner(MessagingListerner, FetchableItem):
    def on_message(self, message, handler):
        if message:
            msg = json.loads(message)
            if msg['action'] == 'retrieve_download_url':
                driveid = msg['driveid']
                item_driveid = msg['item_driveid']
                item_id = msg['item_id']
                item = self.get_item(driveid, item_driveid, item_id, include_download_info=True)
                info = item['download_info']
                return info
        return ''