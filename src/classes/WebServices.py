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

import json
import base64
import requests
from datetime import datetime
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
            return False

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

    def insert_with_args(self, file_content, config, contact, subject, date, destination, _process, custom_mail):
        """
        Insert document into Maarch Database

        :param file_content: Path to file, then it will be encoded it in b64
        :param config: Class Config instance
        :param contact: contact content (id, from Maarch database)
        :param subject: Subject found with REGEX on OCR pdf
        :param date: Date found with REGEX on OCR pdf
        :param destination: Destination (default or found with QR Code or by reading the filename)
        :param _process: Part of config file, only with process configuration
        :param custom_mail: custom to add all the e-mail found
        :return: res_id from Maarch
        """
        if not contact:
            contact = {}
        else:
            contact = [{'id': contact['id'], 'type': 'contact'}]

        if not date:
            date = None

        if not subject:
            subject = ''
        else:
            if config.cfg['OCForMaarch']['uppercasesubject'] == 'True':
                subject = subject.upper()

        data = {
            'encodedFile': base64.b64encode(file_content).decode('utf-8'),
            'priority': _process['priority'],
            'status': _process['status'],
            'chrono': True if _process['generate_chrono'] == 'True' else '',
            'doctype': _process['doctype'],
            'format': _process['format'],
            'modelId': _process['model_id'],
            'typist': _process['typist'],
            'subject': subject,
            'destination': destination,
            'senders': contact,
            'documentDate': date,
            'arrivaldate': str(datetime.now()),
            'customFields': {},
        }

        if _process.get('custom_fields') is not None:
            data['customFields'] = json.loads(_process.get('custom_fields'))

        if _process.get('reconciliation') is None and custom_mail != '' and _process.get('custom_mail') not in [None, '']:
            data['customFields'][_process['custom_mail']] = custom_mail

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
            'status': config.cfg[_process]['status'],
            'title': 'Rapprochement note interne',
            'type': config.cfg[_process]['attachment_type'],
            'resIdMaster': res_id,
            'encodedFile': base64.b64encode(file_content).decode('utf-8'),
            'format': config.cfg[_process]['format'],
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

    def insert_attachment_reconciliation(self, file_content, chrono, _process, config):
        """
        Insert attachment into Maarch database
        Difference between this function and :insert_attachment() : this one will replace an attachment

        :param config:
        :param file_content: Path to file, then it will be encoded it in b64
        :param chrono: Chrono of the attachment to replace
        :param _process: Process we will use to insert on Maarch (from config file)
        :return: res_id from Maarch
        """
        data = {
            'chrono': chrono,
            'encodedFile': base64.b64encode(file_content).decode('utf-8'),
            'attachment_type': config.cfg[_process]['attachment_type'],
            'status': config.cfg[_process]['status']
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
        try:
            res = requests.post(self.baseUrl + 'reconciliation/check', auth=self.auth, data={'chrono': chrono})
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') CheckAttachmentError : ' + str(res.text))
                return False
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while inserting in Maarch')
            self.Log.error('More information : ' + str(e))
            return False

    # BEGIN OBR01
    def check_document(self, chrono):
        """
        Check if document exist
        :param chrono: Chrono number of the document to check
        :return: process success (boolean)
        """
        args = json.dumps({
            'select': 'res_id',
            'clause': "category_id='outgoing' AND alt_identifier='" + chrono + "' AND status <> 'DEL'",
        })
        try:
            res = requests.post(self.baseUrl + 'res/list', auth=self.auth, data=args, headers={'Connection': 'close', 'Content-Type': 'application/json'})
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') CheckDocumentError : ' + str(res.text))
                return False
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while inserting in Maarch')
            self.Log.error('More information : ' + str(e))
            return False

    def reattach_to_document(self, res_id_origin, res_id_signed, typist, config):
        """
        Reattach signed document to the origin one
        :param typist: id of the user
        :param res_id_origin: res_id of the origin document
        :param res_id_signed: res_id of the signed document
        :param config: config object
        :return: process success (boolean)
        """
        args = json.dumps({
            "data": {"resId": res_id_origin},
            "resources": [res_id_signed]
        })
        action_id = config.cfg['REATTACH_DOCUMENT']['action']
        group = config.cfg['REATTACH_DOCUMENT']['group']
        basket = config.cfg['REATTACH_DOCUMENT']['basket']

        try:
            res = requests.put(self.baseUrl + 'resourcesList/users/' + str(typist) + '/groups/' + group + '/baskets/' + basket + '/actions/' + action_id, auth=self.auth, data=args,
                headers={'Connection': 'close', 'Content-Type': 'application/json'})

            if res.status_code != 204:
                self.Log.error('(' + str(res.status_code) + ') ReattachToDocumentError : ' + str(res.text))
                return False
            else:
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while reattach in Maarch')
            self.Log.error('More information : ' + str(e))
            return False

    def change_status(self, res_id, config):
        """
        Change status of a maarch document
        :param res_id: res_id of the maarch document
        :param config: config object
        :return: process success (boolean)
        """

        if config.cfg['REATTACH_DOCUMENT']['status']:
            args = json.dumps({
                "status": config.cfg['REATTACH_DOCUMENT']['status'],
                "resId": [res_id],
                "historyMessage": 'Réconciliation : clôture du document cible dans le cadre de la réconciliation automatique'
            })
        else:
            args = json.dumps({
                "status": config.cfg['REATTACH_DOCUMENT']['status'],
                "resId": [res_id],
            })

        try:
            res = requests.put(self.baseUrl + 'res/resource/status', auth=self.auth, data=args, headers={'Connection': 'close', 'Content-Type': 'application/json'})
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') ChangeStatusError : ' + str(res.text))
                return False
            else:
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while changing status')
            self.Log.error('More information : ' + str(e))
            return False
    # END OBR01

    def insert_letterbox_from_mail(self, args, _process):
        """
        Insert mail into Maarch Database

        :param _process: Part of mail config file, only with process configuration
        :param args: Array of argument, same as insert_with_args
        :return: res_id or Boolean if issue happen
        """
        args['encodedFile'] = base64.b64encode(open(args['file'], 'rb').read()).decode('UTF-8')
        args['arrivalDate'] = str(datetime.now())

        del args['file']
        del args['from']

        if _process.get('custom_fields') is not None:
            args['customFields'].update(json.loads(_process.get('custom_fields')))

        try:
            res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=json.dumps(args), headers={'Connection': 'close', 'Content-Type': 'application/json'})

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') MailInsertIntoMaarchError : ' + str(res.text))
                return False, json.loads(res.text)
            else:
                return True, json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while inserting in Maarch')
            self.Log.error('More information : ' + str(e))
            return False

    def insert_attachment_from_mail(self, args, res_id):
        """
        Insert attachment into Maarch database

        :param args: Arguments used to insert attachment
        :param res_id: Res_id of the document to attach the new attachment
        :return: res_id from Maarch
        """

        data = {
            'status': args['status'],
            'title': args['subject'],
            'encodedFile': base64.b64encode(open(args['file'], 'rb').read()).decode('UTF-8'),
            'format': args['format'],
            'resIdMaster': res_id,
            'type': 'simple_attachment'
        }

        try:
            res = requests.post(self.baseUrl + 'attachments', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'})

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') MailInsertAttachmentsIntoMaarchError : ' + str(res.text))
                return False, json.loads(res.text)
            else:
                return True, json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while inserting in Maarch')
            self.Log.error('More information : ' + str(e))
            return False, str(e)

    def retrieve_entities(self):
        try:
            res = requests.get(self.baseUrl + 'entities', auth=self.auth, headers={'Connection': 'close', 'Content-Type': 'application/json'})
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveMaarchEntitiesError : ' + str(res.text))
                return False
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while retrieving Maarch entities')
            self.Log.error('More information : ' + str(e))
            return False

    def retrieve_users(self):
        try:
            res = requests.get(self.baseUrl + 'users', auth=self.auth, headers={'Connection': 'close', 'Content-Type': 'application/json'})
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveMaarchUserError : ' + str(res.text))
                return False
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while retrieving Maarch users')
            self.Log.error('More information : ' + str(e))
            return False

    def retrieve_custom_fields(self):
        try:
            res = requests.get(self.baseUrl + 'customFields', auth=self.auth, headers={'Connection': 'close', 'Content-Type': 'application/json'})
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveMaarchCustomFieldsError : ' + str(res.text))
                return False
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while retrieving Maarch custom fields')
            self.Log.error('More information : ' + str(e))
            return False

    def create_contact(self, contact):
        res = requests.post(self.baseUrl + '/contacts', auth=self.auth, data=json.dumps(contact), headers={'Connection': 'close', 'Content-Type': 'application/json'})

        if res.status_code != 200:
            return False, res.text
        else:
            return True, json.loads(res.text)

    def get_ban(self, adr):
        try:
            res = requests.get("https://api-adresse.data.gouv.fr/search/?q=" + adr, headers={'Connection': 'close', 'Content-Type': 'application/json'})
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveMaarchUserError : ' + str(res.text))
                return False
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error while retrieving Maarch users')
            self.Log.error('More information : ' + str(e))
            return False
