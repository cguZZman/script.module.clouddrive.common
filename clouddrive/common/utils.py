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

class Utils:
    @staticmethod
    def get_extension(name):
        index = name.rfind('.')
        if index > -1:
            return name[index+1:].lower()
        return ''
    
    @staticmethod
    def remove_extension(name):
        index = name.rfind('.')
        if index > -1:
            return name[:index]
        return name
    
    @staticmethod
    def replace_extension(name, newExtension):
        index = name.rfind('.')
        if index > -1:
            return name[:index+1] + newExtension
        return name
    
    @staticmethod
    def get_safe_value(dictionary, key, default_value=None):
        if dictionary and key in dictionary:
            return dictionary[key]
        return default_value
    
    @staticmethod
    def default(value, default_value):
        return value if value else default_value
    
    @staticmethod
    def unicode(txt):
        if isinstance (txt,str):
            txt = txt.decode("utf-8")
        return u'%s' % (txt)
    
    @staticmethod
    def str(txt):
        return Utils.unicode(txt).encode("utf-8", 'replace')
    
    @staticmethod
    def ascii(txt):
        return Utils.unicode(txt).encode('ascii', 'ignore')
   
    @staticmethod
    def get_fqn(o):
        return o.__module__ + "." + o.__class__.__name__
    
    @staticmethod
    def get_class(fqn):
        data = fqn.split('.')
        module = __import__(data[0])
        for comp in data[1:]:
            module = getattr(module, comp)
        return module
    
