# This file is part of OpenCapture.

# OpenCapture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OpenCapture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with OpenCapture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import json
import base64
import requests
from requests.auth import HTTPBasicAuth

class WebServices:
    def __init__(self, host, user, pwd, Log):
        self.baseUrl    = host
        self.auth       = HTTPBasicAuth(user, pwd)
        self.Log        = Log

    def retrieve_contact_by_mail(self, mail):
        res = requests.get(self.baseUrl + 'getContactByMail', auth=self.auth, params={'mail' : mail})
        if res.status_code != 200:
            self.Log.error('GetContactByMailError : ' + str(res.status_code))
            return False
        else:
            return json.loads(res.text)

    def retrieve_contact_by_url(self, url):
        url = url.replace('http://', '').replace('https://', '').replace('www.', '')
        res = requests.get(self.baseUrl + 'getContactByUrl', auth=self.auth, params={'url': url})

        if res.status_code != 200:
            self.Log.error('GetContactByUrlError : ' + str(res.status_code))
            return False
        else:
            return json.loads(res.text)

    def insert_with_args(self, fileContent, Config, contact, subject, date, destination, _process):
        if not contact:
            contact = {'id' : '', 'contact_id' : ''}
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
            'doc_date'      : date
        }

        res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=json.dumps(data), headers={'Connection':'close', 'Content-Type' : 'application/json'})

        if res.status_code != 200:
            self.Log.error('InsertIntoMaarchError : ' + str(res.status_code) + ' : ' + str(res.text))
            return False
        else:
            return res.text

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

        res = requests.post(self.baseUrl + 'attachments', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type' : 'application/json'})

        if res.status_code != 200:
            self.Log.error('InsertAttachmentsIntoMaarchError : ' + str(res.status_code) + ' : ' + str(res.text))
            return False
        else:
            return res.text

    def insert_attachment_reconciliation(self, fileContent, chrono, _process):
        data = {
            'chrono'            : chrono,
            'encodedFile'       : base64.b64encode(fileContent).decode('utf-8'),
        }

        res = requests.post(self.baseUrl + 'reconciliation/add', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'})

        if res.status_code != 200:
            self.Log.error('InsertAttachmentsReconciliationIntoMaarchError : ' + str(res.status_code) + ' : ' + str(res.text))
            return False
        else:
            return res.text

    def check_attachment(self, chrono):
        res = requests.get(self.baseUrl + 'reconciliation/check', auth=self.auth, params={'chrono': chrono})
        if res.status_code != 200:
            self.Log.error('CheckAttachmentError : ' + str(res.status_code))
            return False
        else:
            return json.loads(res.text)