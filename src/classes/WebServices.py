# This file is part of Open-Capture.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import sys
import json
import base64
import requests
from requests.auth import HTTPBasicAuth

class WebServices:
    def __init__(self, host, user, pwd, Log):
        self.baseUrl    = host
        self.auth       = HTTPBasicAuth(user, pwd)
        self.Log        = Log
        self.check_connection()

    def check_connection(self):
        try:
            requests.get(self.baseUrl)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error connecting to the host. Exiting program..')
            self.Log.error('More information : ' + str(e))
            sys.exit('Connection error')

    def retrieve_contact_by_mail(self, mail):
        res = requests.get(self.baseUrl + 'getContactByMail', auth=self.auth, params={'mail' : mail})
        if res.status_code != 200:
            self.Log.error('(' + str(res.status_code) + ') GetContactByMailError : ' + str(res.text))
            return False
        else:
            return json.loads(res.text)

    def retrieve_contact_by_phone(self, phone):
        res = requests.get(self.baseUrl + 'getContactByPhone', auth=self.auth, params={'phone': phone})
        if res.status_code != 200:
            self.Log.error('(' + str(res.status_code) + ') \n GetContactByPhoneError : ' + str(res.text))
            return False
        else:
            return json.loads(res.text)

    def retrieve_contact_by_url(self, url):
        url = url.replace('http://', '').replace('https://', '').replace('www.', '')
        res = requests.get(self.baseUrl + 'getContactByUrl', auth=self.auth, params={'url': url})

        if res.status_code != 200:
            self.Log.error('(' + str(res.status_code) + ') GetContactByUrlError : ' + str(res.text))
            return False
        else:
            return json.loads(res.text)

    def insert_with_args(self, fileContent, Config, contact, subject, date, destination, _process, custom_mail):
        if not contact:
            contact = {'id' : '', 'contact_id' : ''}
        if not subject:
            subject = ''
        else:
            if Config.cfg['OCForMaarch']['uppercasesubject'] == 'True':
                subject = subject.upper()

        data = {
            'encodedFile'   : base64.b64encode(fileContent).decode('utf-8'),
            'priority'      : Config.cfg[_process]['priority'],
            'status'        : Config.cfg[_process]['status'],
            'type_id'       : Config.cfg[_process]['type_id'],
            'format'        : Config.cfg[_process]['format'],
            'category_id'   : Config.cfg[_process]['category_id'],
            'typist'        : Config.cfg[_process]['typist'],
            'subject'       : subject,
            'destination'   : destination,
            'address_id'    : contact['id'],
            'exp_contact_id': contact['contact_id'],
            'doc_date'      : date,
        }

        if 'reconciliation' not in _process:
            data[Config.cfg[_process]['custom_mail']] = custom_mail[:254]  # 254 to avoid too long string (maarch custom is limited to 255 char)

        try:
            res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=json.dumps(data), headers={'Connection':'close', 'Content-Type' : 'application/json'})

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') InsertIntoMaarchError : ' + str(res.text))
                return False
            else:
                return res.text
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while inserting in Maarch')
            self.Log.error('More information : ' + str(e))
            return False

    def insert_attachment(self, fileContent, Config, res_id, _process):
        data = {
            'resId'         : res_id,
            'status'        : Config.cfg[_process]['status'],
            'collId'        : 'letterbox_coll',
            'table'         : 'res_attachments',
            'data'          : [
                {'column' : 'title', 'value' : 'Rapprochement note interne', 'type': 'string'},
                {'column' : 'attachment_type', 'value' : Config.cfg[_process]['attachment_type'], 'type' : 'string'},
                {'column' : 'coll_id', 'value' : 'letterbox_coll', 'type' : 'string'},
                {'column' : 'res_id_master', 'value' : res_id, 'type' : 'string'}
            ],
            'encodedFile'   : base64.b64encode(fileContent).decode('utf-8'),
            'fileFormat'    : Config.cfg[_process]['format'],
        }

        try:
            res = requests.post(self.baseUrl + 'attachments', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type' : 'application/json'})

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') InsertAttachmentsIntoMaarchError : ' + str(res.text))
                return False
            else:
                return res.text
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while inserting in Maarch')
            self.Log.error('More information : ' + str(e))
            return False

    def insert_attachment_reconciliation(self, fileContent, chrono, _process):
        data = {
            'chrono'            : chrono,
            'encodedFile'       : base64.b64encode(fileContent).decode('utf-8'),
        }

        try:
            res = requests.post(self.baseUrl + 'reconciliation/add', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'})

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') InsertAttachmentsReconciliationIntoMaarchError : ' + str(res.text))
                return False
            else:
                return res.text
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while inserting in Maarch')
            self.Log.error('More information : ' + str(e))
            return False

    def check_attachment(self, chrono):
        res = requests.get(self.baseUrl + 'reconciliation/check', auth=self.auth, params={'chrono': chrono})
        if res.status_code != 200:
            self.Log.error('(' + str(res.status_code) + ') CheckAttachmentError : ' + str(res.text))
            return False
        else:
            return json.loads(res.text)