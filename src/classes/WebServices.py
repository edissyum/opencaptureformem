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

    def insert_with_args(self, fileContent, Config, contact, subject, date, destination):
        if not contact:
            contact = {'id' : '', 'contact_id' : ''}
        data = {
            #'encodedFile'   : base64.b64encode(open(file, 'rb').read()).decode("utf-8"),
            'encodedFile'   : base64.b64encode(fileContent),
            'priority'      : Config.cfg['OCForMaarch']['priority'],
            'status'        : Config.cfg['OCForMaarch']['status'],
            'type_id'       : Config.cfg['OCForMaarch']['type_id'],
            'format'        : Config.cfg['OCForMaarch']['format'],
            'category_id'   : Config.cfg['OCForMaarch']['category_id'],
            'subject'       : subject,
            'destination'   : destination,
            'address_id'    : contact['id'],
            'exp_contact_id': contact['contact_id'],
            'doc_date'      : date
        }

        res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=data)
        if res.status_code != 200:
            self.Log.error('InsertIntoMaarch : ' + str(res.status_code) + ' : ' + str(res.text))
            return False
        else:
            return res.text

