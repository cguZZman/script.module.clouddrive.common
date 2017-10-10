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
import os


class AccountManager(object):
    accounts = {}
    _addon_data_path = None
    _config_file_name = 'accounts.cfg'
    _config_path = None
    
    def __init__(self, addon_data_path):
        self._addon_data_path = addon_data_path
        self._config_path = os.path.join(addon_data_path, self._config_file_name)
        if not os.path.exists(addon_data_path):
            try:
                os.makedirs(addon_data_path)
            except:
                self.monitor.waitForAbort(3)
                os.makedirs(addon_data_path)

    def load(self):
        self.accounts = {}
        if os.path.exists(self._config_path):
            with open(self._config_path, 'rb') as fo:
                self.accounts = json.loads(fo.read())
        return self.accounts
    
    def add_account(self, account):
        self.load()
        self.accounts[account['id']] = account
        self.save()
        
    '''
    def drive_map(self):
        if not self.accounts:
            self.accounts = {}
            for account_id in self.config.sections():
                account = OneDrive(self.addon.getSetting('client_id_oauth2'))
                account.account_id = account_id
                account.event_listener = self.event_listener
                account.name = self.config.get(account_id, 'name')
                account.access_token = self.config.get(account_id, 'access_token')
                account.refresh_token = self.config.get(account_id, 'refresh_token')
                self.accounts[account_id] = account
        return self.accounts
    '''
    
    def account_by_driveid(self, driveid):
        for accountid in self.accounts:
            for drive in self.accounts[accountid]['drives']:
                if drive['id'] == driveid:
                    return self.accounts[accountid]
        raise AccountNotFoundException()
    
    def drive_by_driveid(self, driveid):
        for account_id in self.accounts:
            for drive in self.accounts[account_id]['drives']:
                if drive['id'] == driveid:
                    return drive
        raise DriveNotFoundException()
    
    def event_listener(self, onedrive, event, obj):
        if event == 'login_success':
            self.save(onedrive)

    def save(self):
        with open(self._config_path, 'wb') as fo:
            fo.write(json.dumps(self.accounts, sort_keys=True, indent=4))

    def remove_account(self, accountid):
        self.load()
        del self.accounts[accountid]
        self.save()
    
    def remove_drive(self, driveid):
        self.load()
        account = self.account_by_driveid(driveid)
        drive = self.drive_by_driveid(driveid)
        account['drives'].remove(drive)
        self.save()

class AccountNotFoundException(Exception):
    pass

class DriveNotFoundException(Exception):
    pass