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
    def __init__(self, host, user, pwd, log):
        self.Log = log
        self.baseUrl = host
        self.auth = HTTPBasicAuth(user, pwd)
        self.check_connection()

    def check_connection(self):
        """
        Check if remote host is UP
        """
        try:
            requests.get(self.baseUrl)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error connecting to the host. Exiting program..')
            self.Log.error('More information : ' + str(e))
            sys.exit('Connection error')

    def retrieve_contact_by_mail(self, mail):
        """
        Search a contact into Maarch database using mail

        :param mail: e-mail to search
        :return: Contact from Maarch
        """
        res = requests.get(self.baseUrl + 'getContactByMail', auth=self.auth, params={'mail': mail})
        if res.status_code != 200:
            self.Log.error('(' + str(res.status_code) + ') GetContactByMailError : ' + str(res.text))
            return False
        else:
            return json.loads(res.text)

    def retrieve_contact_by_phone(self, phone):
        """
        Search a contact into Maarch database using phone

        :param phone: phone to search
        :return: Contact from Maarch
        """
        res = requests.get(self.baseUrl + 'getContactByPhone', auth=self.auth, params={'phone': phone})
        if res.status_code != 200:
            self.Log.error('(' + str(res.status_code) + ') \n GetContactByPhoneError : ' + str(res.text))
            return False
        else:
            return json.loads(res.text)

    def retrieve_contact_by_url(self, url):
        """
        Search a contact into Maarch database using URL

        :param url: URL to search
        :return: Contact from Maarch
        """
        url = url.replace('http://', '').replace('https://', '').replace('www.', '')
        res = requests.get(self.baseUrl + 'getContactByUrl', auth=self.auth, params={'url': url})

        if res.status_code != 200:
            self.Log.error('(' + str(res.status_code) + ') GetContactByUrlError : ' + str(res.text))
            return False
        else:
            return json.loads(res.text)

    def insert_with_args(self, file_content, config, contact, subject, date, destination, _process, custom_mail):
        """
        Insert document into Maarch Database

        :param file_content: Path to file, then it will be encoded it in b64
        :param config: Class Config instance
        :param contact: contact content (id and contact_id, from Maarch database)
        :param subject: Subject found with REGEX on OCR pdf
        :param date: Date found with REGEX on OCR pdf
        :param destination: Destination (default or found with QR Code or by reading the filename)
        :param _process: Process we will use to insert on Maarch (from config file)
        :param custom_mail: custom to add all the e-mail found
        :return: res_id from Maarch
        """
        if not contact:
            contact = {'id': '', 'contact_id': ''}
        if not subject:
            subject = ''
        else:
            if config.cfg['OCForMaarch']['uppercasesubject'] == 'True':
                subject = subject.upper()

        data = {
            'encodedFile': base64.b64encode(file_content).decode('utf-8'),
            'priority': config.cfg[_process]['priority'],
            'status': config.cfg[_process]['status'],
            'type_id': config.cfg[_process]['type_id'],
            'format': config.cfg[_process]['format'],
            'category_id': config.cfg[_process]['category_id'],
            'typist': config.cfg[_process]['typist'],
            'subject': subject,
            'destination': destination,
            'address_id': contact['id'],
            'exp_contact_id': contact['contact_id'],
            'doc_date': date,
        }

        if 'reconciliation' not in _process:
            data[config.cfg[_process]['custom_mail']] = custom_mail[:254]  # 254 to avoid too long string (maarch custom is limited to 255 char)

        try:
            res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'})

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') InsertIntoMaarchError : ' + str(res.text))
                return False
            else:
                return res.text
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while inserting in Maarch')
            self.Log.error('More information : ' + str(e))
            return False

    def insert_attachment(self, file_content, config, res_id, _process):
        """
        Insert attachment into Maarch database

        :param file_content: Path to file, then it will be encoded it in b64
        :param config: Class Config instance
        :param res_id: Res_id of the document to attach the new attachment
        :param _process: Process we will use to insert on Maarch (from config file)
        :return: res_id from Maarch
        """
        data = {
            'resId': res_id,
            'status': config.cfg[_process]['status'],
            'collId': 'letterbox_coll',
            'table': 'res_attachments',
            'data': [
                {'column': 'title', 'value': 'Rapprochement note interne', 'type': 'string'},
                {'column': 'attachment_type', 'value': config.cfg[_process]['attachment_type'], 'type': 'string'},
                {'column': 'coll_id', 'value': 'letterbox_coll', 'type': 'string'},
                {'column': 'res_id_master', 'value': res_id, 'type': 'string'}
            ],
            'encodedFile': base64.b64encode(file_content).decode('utf-8'),
            'fileFormat': config.cfg[_process]['format'],
        }

        try:
            res = requests.post(self.baseUrl + 'attachments', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'})

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') InsertAttachmentsIntoMaarchError : ' + str(res.text))
                return False
            else:
                return res.text
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while inserting in Maarch')
            self.Log.error('More information : ' + str(e))
            return False

    def insert_attachment_reconciliation(self, file_content, chrono, _process):
        """
        Insert attachment into Maarch database
        Difference between this function and :insert_attachment() : this on will replace an attachment

        :param file_content: Path to file, then it will be encoded it in b64
        :param chrono: Chrono of the attachment to replace
        :param _process: Process we will use to insert on Maarch (from config file)
        :return: res_id from Maarch
        """
        data = {
            'chrono': chrono,
            'encodedFile': base64.b64encode(file_content).decode('utf-8'),
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
        """
        Check if attachment exist

        :param chrono: Chrono of the attachment to check
        :return: Info of attachment from Maarch database
        """
        res = requests.get(self.baseUrl + 'reconciliation/check', auth=self.auth, params={'chrono': chrono})
        if res.status_code != 200:
            self.Log.error('(' + str(res.status_code) + ') CheckAttachmentError : ' + str(res.text))
            return False
        else:
            return json.loads(res.text)
