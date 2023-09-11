# This file is part of Open-Capture For MEM Courrier.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture For MEM Courrier is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture For MEM Courrier.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import json
import base64
import requests
import holidays
from datetime import datetime, time, timedelta
from requests.auth import HTTPBasicAuth


class WebServices:
    def __init__(self, host, user, pwd, log, timeout, cert_path):
        self.Log = log
        self.baseUrl = host
        self.auth = HTTPBasicAuth(user, pwd)
        self.timeout = int(timeout)
        self.cert = cert_path
        self.check_connection()

    def check_connection(self):
        """
        Check if remote host is UP
        """
        try:
            requests.get(self.baseUrl, timeout=self.timeout, verify=self.cert)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('Error connecting to the host. Exiting program..')
            self.Log.error('More information : ' + str(e))
            raise

    def retrieve_contact_by_mail(self, mail):
        """
        Search a contact into MEM Courrier database using mail

        :param mail: e-mail to search
        :return: Contact from MEM Courrier
        """
        if mail:
            try:
                res = requests.get(self.baseUrl + 'getContactByMail', auth=self.auth, params={'mail': mail}, timeout=self.timeout, verify=self.cert)
                if res.status_code != 200:
                    self.Log.error('(' + str(res.status_code) + ') GetContactByMailError : ' + str(res.text))
                    return False, str(res.text)
                else:
                    return json.loads(res.text)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                self.Log.error('GetContactByMailError : ' + str(e))
                return False, str(e)
        else:
            self.Log.info('GetContactByMailInfo : No email found')

    def retrieve_contact_by_phone(self, phone):
        """
        Search a contact into MEM Courrier database using phone

        :param phone: phone to search
        :return: Contact from MEM Courrier
        """
        try:
            res = requests.get(self.baseUrl + 'getContactByPhone', auth=self.auth, params={'phone': phone}, timeout=self.timeout, verify=self.cert)
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') \n GetContactByPhoneError : ' + str(res.text))
                return False, str(res.text)
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('GetContactByPhoneError : ' + str(e))
            return False, str(e)

    def retrieve_document_by_chrono(self, chrono_number):
        if chrono_number:
            try:
                data = {
                    'chronoNumber': chrono_number
                }
                res = requests.post(self.baseUrl + '/resources/getByChrono', auth=self.auth, data=json.dumps(data),
                                    headers={'Connection': 'close', 'Content-Type': 'application/json'},
                                    timeout=self.timeout, verify=self.cert)
                if res.status_code != 200:
                    self.Log.error('(' + str(res.status_code) + ') getResourceByChrono : ' + str(res.text))
                    return False
                else:
                    return json.loads(res.text)
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                self.Log.error('InsertIntoMEMError : ' + str(e))
                return False, str(e)

    def link_documents(self, res_id_master, res_id):
        data = {
            'linkedResources': [res_id]
        }

        res = requests.post(self.baseUrl + '/resources/' + str(res_id_master) + '/linkedResources', auth=self.auth,
                            data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'})
        if res.status_code not in (200, 204):
            self.Log.error('(' + str(res.status_code) + ') linkDocumentError : ' + str(res.text))
            return False
        return True

    def insert_with_args(self, file_content, config, contact, subject, date, destination, _process, custom_mail):
        """
        Insert document into MEM Courrier Database

        :param file_content: Path to file, then it will be encoded it in b64
        :param config: Class Config instance
        :param contact: contact content (id, from MEM Courrier database)
        :param subject: Subject found with REGEX on OCR pdf
        :param date: Date found with REGEX on OCR pdf
        :param destination: Destination (default or found with QR Code or by reading the filename)
        :param _process: Part of config file, only with process configuration
        :param custom_mail: custom to add all the e-mail found
        :return: res_id from MEM Courrier
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
            if config.cfg['OCForMEM']['uppercasesubject'] == 'True':
                subject = subject.upper()

        if 'subject' in _process and _process['subject']:
            subject = _process['subject']

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
            'diffusionList': _process['diffusion_list'] if 'diffusion_list' in _process else [],
            'processLimitDate': str(self.calcul_process_limit_date(_process['doctype']))
        }

        if _process.get('custom_fields') is not None:
            data['customFields'] = json.loads(_process.get('custom_fields'))

        if _process.get('reconciliation') is None and custom_mail != '' and _process.get('custom_mail') not in [None, '']:
            data['customFields'][_process['custom_mail']] = custom_mail

        try:
            res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') InsertIntoMEMError : ' + str(res.text))
                return False, str(res.text)
            else:
                return res.text
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('InsertIntoMEMError : ' + str(e))
            return False, str(e)

    def insert_attachment(self, file_content, config, res_id, _process):
        """
        Insert attachment into MEM Courrier database

        :param file_content: Path to file, then it will be encoded it in b64
        :param config: Class Config instance
        :param res_id: Res_id of the document to attach the new attachment
        :param _process: Process we will use to insert on MEM Courrier (from config file)
        :return: res_id from MEM Courrier
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
            res = requests.post(self.baseUrl + 'attachments', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') InsertAttachmentsIntoMEMError : ' + str(res.text))
                return False, str(res.text)
            else:
                return res.text
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('InsertAttachmentsIntoMEMError : ' + str(e))
            return False, str(e)

    def insert_attachment_reconciliation(self, file_content, chrono, _process, config):
        """
        Insert attachment into MEM Courrier database
        Difference between this function and :insert_attachment() : this one will replace an attachment

        :param config:
        :param file_content: Path to file, then it will be encoded it in b64
        :param chrono: Chrono of the attachment to replace
        :param _process: Process we will use to insert on MEM Courrier (from config file)
        :return: res_id from MEM Courrier
        """
        data = {
            'chrono': chrono,
            'encodedFile': base64.b64encode(file_content).decode('utf-8'),
            'attachment_type': config.cfg[_process]['attachment_type'],
            'status': config.cfg[_process]['status']
        }

        try:
            res = requests.post(self.baseUrl + 'reconciliation/add', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') InsertAttachmentsReconciliationIntoMEMError : ' + str(res.text))
                return False, str(res.text)
            else:
                return res.text
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('InsertAttachmentsReconciliationIntoMEMError : ' + str(e))
            return False, str(e)

    def check_attachment(self, chrono):
        """
        Check if attachment exist

        :param chrono: Chrono of the attachment to check
        :return: Info of attachment from MEM Courrier database
        """
        try:
            res = requests.post(self.baseUrl + 'reconciliation/check', auth=self.auth, data={'chrono': chrono}, timeout=self.timeout, verify=self.cert)
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') CheckAttachmentError : ' + str(res.text))
                return False, str(res.text)
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('CheckAttachmentError : ' + str(e))
            return False, str(e)

    # BEGIN OBR01
    def check_document(self, chrono):
        """
        Check if document exist
        :param chrono: Chrono number of the document to check
        :return: process success (boolean)
        """
        args = json.dumps({
            'select': 'res_id',
            'clause': "alt_identifier='" + chrono + "' AND status <> 'DEL'",
        })
        try:
            res = requests.post(self.baseUrl + 'res/list', auth=self.auth, data=args, headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') CheckDocumentError : ' + str(res.text))
                return False, str(res.text)
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('CheckDocumentError : ' + str(e))
            return False, str(e)

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
                headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 204:
                self.Log.error('(' + str(res.status_code) + ') ReattachToDocumentError : ' + str(res.text))
                return False, str(res.text)
            else:
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('ReattachToDocumentError : ' + str(e))
            return False, str(e)

    def change_status(self, res_id, config):
        """
        Change status of a MEM Courrier document
        :param res_id: res_id of the MEM Courrier document
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
            res = requests.put(self.baseUrl + 'res/resource/status', auth=self.auth, data=args, headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') ChangeStatusError : ' + str(res.text))
                return False, str(res.text)
            else:
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('ChangeStatusError : ' + str(e))
            return False, str(e)
    # END OBR01

    def insert_letterbox_from_mail(self, args, _process):
        """
        Insert mail into MEM Courrier Database

        :param _process: Part of mail config file, only with process configuration
        :param args: Array of argument, same as insert_with_args
        :return: res_id or Boolean if issue happen
        """
        args['encodedFile'] = base64.b64encode(open(args['file'], 'rb').read()).decode('UTF-8')
        args['arrivalDate'] = str(datetime.now())
        args['processLimitDate'] = str(self.calcul_process_limit_date(args['doctype']))

        del args['file']

        if _process.get('custom_fields') is not None:
            args['customFields'].update(json.loads(_process.get('custom_fields')))

        try:
            res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=json.dumps(args), headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') MailInsertIntoMEMError : ' + str(res.text))
                return False, str(res.text)
            else:
                return True, json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('MailInsertIntoMEMError : ' + str(e))
            return False, str(e)

    def insert_attachment_from_mail(self, args, res_id):
        """
        Insert attachment into MEM Courrier database

        :param args: Arguments used to insert attachment
        :param res_id: Res_id of the document to attach the new attachment
        :return: res_id from MEM Courrier
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
            res = requests.post(self.baseUrl + 'attachments', auth=self.auth, data=json.dumps(data), headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') MailInsertAttachmentsIntoMEMError : ' + str(res.text))
                return False, str(res.text)
            else:
                return True, json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('MailInsertAttachmentsIntoMEMError : ' + str(e))
            return False, str(e)

    def calcul_process_limit_date(self, doctype):
        doctype_info = self.retrieve_doctype(doctype)
        today = datetime.combine(datetime.now(), time.min)
        process_limit_date = today
        days_off = []

        for date, _ in sorted(holidays.FR(prov='Métropole', years=today.year).items()):
            days_off.append(datetime.combine(date, time.min))

        if len(doctype_info['doctype']) != 0:
            process_delay = doctype_info['doctype']['process_delay']
            working_days_info = self.retrieve_workings_days()
            if len(working_days_info['parameter']) != 0:
                working_days = working_days_info['parameter']['param_value_int']
                if working_days:
                    while process_delay > 0:
                        process_limit_date += timedelta(days=1)
                        weekday = process_limit_date.weekday()
                        if weekday >= 5:
                            continue
                        process_delay -= 1
                else:
                    process_limit_date += timedelta(days=process_delay)
        return process_limit_date

    def retrieve_entities(self):
        try:
            res = requests.get(self.baseUrl + 'entities', auth=self.auth, headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveMEMEntitiesError : ' + str(res.text))
                return False, str(res.text)
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('RetrieveMEMEntitiesError : ' + str(e))
            return False, str(e)

    def retrieve_doctype(self, doctype):
        try:
            res = requests.get(self.baseUrl + 'doctypes/types/' + doctype, auth=self.auth, headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveDoctypeError : ' + str(res.text))
                return False, str(res.text)
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('RetrieveDoctypeError : ' + str(e))
            return False, str(e)

    def retrieve_workings_days(self):
        try:
            res = requests.get(self.baseUrl + 'parameters/workingDays', auth=self.auth, headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveWorkingDaysError : ' + str(res.text))
                return False, str(res.text)
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('RetrieveWorkingDaysError : ' + str(e))
            return False, str(e)

    def retrieve_users(self):
        try:
            res = requests.get(self.baseUrl + 'users', auth=self.auth, headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveMEMUserError : ' + str(res.text))
                return False, str(res.text)
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('RetrieveMEMUserError : ' + str(e))
            return False, str(e)

    def retrieve_custom_fields(self):
        try:
            res = requests.get(self.baseUrl + 'customFields', auth=self.auth, headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)
            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveMEMCustomFieldsError : ' + str(res.text))
                return False, str(res.text)
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('RetrieveMEMCustomFieldsError : ' + str(e))
            return False, str(e)

    def create_contact(self, contact):
        try:
            res = requests.post(self.baseUrl + '/contacts', auth=self.auth, data=json.dumps(contact), headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 200:
                self.Log.error('CreateContactError : ' + str(res.text))
                return False, str(res.text)
            else:
                return True, json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('CreateContactError : ' + str(e))
            return False, str(e)

    def retrieve_listinstance(self, res_id):
        try:
            res = requests.get(self.baseUrl + '/resources/' + str(res_id) + '/listInstance', auth=self.auth, headers={'Connection': 'close', 'Content-Type': 'application/json'}, timeout=self.timeout, verify=self.cert)

            if res.status_code != 200:
                self.Log.error('(' + str(res.status_code) + ') RetrieveListInstanceError : ' + str(res.text))
                return False, str(res.text)
            else:
                return json.loads(res.text)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            self.Log.error('RetrieveListInstanceError : ' + str(e))
            return False, str(e)
