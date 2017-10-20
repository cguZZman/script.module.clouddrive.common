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

from clouddrive.common.utils import Utils
import xbmc
import xbmcaddon

class Logger:
    @staticmethod
    def _log(msg, level):
        xbmc.log('[' + xbmcaddon.Addon().getAddonInfo('id') + '] ' + Utils.str(msg), level)
        
    @staticmethod
    def debug(msg):
        Logger._log(msg, xbmc.LOGNOTICE)
    
    @staticmethod
    def notice(msg):
        Logger._log(msg, xbmc.LOGNOTICE)
    
    @staticmethod
    def error(msg):
        Logger._log(msg, xbmc.LOGERROR)