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

import xbmcgui, xbmcvfs
from clouddrive.common.ui.utils import KodiUtils
from clouddrive.common.utils import Utils
import os
from clouddrive.common.ui.logger import Logger

class DialogProgressBG (xbmcgui.DialogProgressBG):
    _default_heading = None
    created = False
    
    def __init__(self, default_heading):
        self._default_heading = default_heading
                 
    def create(self, heading, message=None):
        if self.created:
            self.update(heading=heading, message=message)
        else:
            super(DialogProgressBG, self).create(heading, message)
            self.created = True
    
    def close(self):
        if self.created:
            super(DialogProgressBG, self).close()
            self.created = False
    
    def update(self, percent=0, heading=None, message=None):
        if not self.created:
            if not heading: heading = self._default_heading
            self.create(heading=heading, message=message)
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        super(DialogProgressBG, self).update(percent=percent, heading=heading, message=message)
    
    def iscanceled(self):
        if self.created:
            return super(DialogProgress, self).iscanceled()
        return False 
    
class DialogProgress (xbmcgui.DialogProgress):
    _default_heading = None
    created = False
    
    def __init__(self, default_heading):
        self._default_heading = default_heading
        
    def create(self, heading, line1="", line2="", line3=""):
        if self.created:
            self.close()
            
        super(DialogProgress, self).create(heading, line1, line2, line3)
        self.created = True
    
    def close(self):
        if self.created:
            super(DialogProgress, self).close()
            self.created = False
    
    def update(self, percent, line1="", line2="", line3=""):
        if not self.created:
            self.create(self._default_heading, line1, line2, line3)
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        super(DialogProgress, self).update(percent, line1, line2, line3)
        
    def iscanceled(self):
        if self.created:
            return super(DialogProgress, self).iscanceled()
        return False 
        
        
class QRDialogProgress(xbmcgui.WindowXMLDialog):
    _heading_control = 1000
    _qr_control = 1001
    _text_control = 1002
    _cancel_btn_control = 1003
    #
    def __init__(self, *args, **kwargs):
        self.heading = kwargs["heading"]
        self.qr_code = kwargs["qr_code"]
        self.line1 = kwargs["line1"]
        self.line2 = kwargs["line2"]
        self.line3 = kwargs["line3"]
        self.percent = 0
        self._image_path = None
        self.canceled = False

    def __del__(self):
        #xbmcvfs.delete(self._image_path)
        pass
    
    @staticmethod
    def create(heading, qr_code, line1="", line2="", line3=""):
        path = Utils.unicode(KodiUtils.get_addon_info("path", "script.module.clouddrive.common"))
        return QRDialogProgress("pin-dialog.xml", path, "default", heading=heading, qr_code=qr_code, line1=line1, line2=line2, line3=line3)
    
    def iscanceled(self):
        return self.canceled
    
    def onInit(self):
        import pyqrcode
        self._image_path = os.path.join(Utils.unicode(KodiUtils.translate_path(KodiUtils.get_addon_info("profile", "script.module.clouddrive.common"))),"qr.png")
        qrcode = pyqrcode.create(self.qr_code)
        qrcode.png(self._image_path, scale=10)
        del qrcode
        self.getControl(self._heading_control).setLabel(self.heading)
        self.getControl(self._qr_control).setImage(self._image_path)
        self.update(self.percent, self.line1, self.line2, self.line3)

    def update(self, percent, line1="", line2="", line3=""):
        self.percent = percent
        if percent < 0: percent = 0
        if percent > 100: percent = 100
        if line1:
            self.line1 = line1
        if line2:
            self.line2 = line2
        if line3:
            self.line3 = line3
        text = self.line1
        if self.line2:
            text = text + "[CR]" + self.line2
        if self.line3:
            text = text + "[CR]" + self.line3   
        self.getControl(self._text_control).setText(text)
        self.setFocus(self.getControl(self._cancel_btn_control))
    
    def onClick(self, control_id):
        if (control_id == self._cancel_btn_control):
            self.canceled = True
            self.close()
    
    #def close(self):
    #    self.canceled = True

    def onAction(self, action):
        if action.getId() == xbmcgui.ACTION_PREVIOUS_MENU or action.getId() == xbmcgui.ACTION_NAV_BACK:
            self.canceled = True
        super(QRDialogProgress, self).onAction(action)
        
        