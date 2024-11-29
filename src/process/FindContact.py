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

import re
from thefuzz import fuzz
from threading import Thread

MAPPING = {
    'postal_code': 'addressPostcode',
    'city': 'addressTown',
    'num_address': 'addressNumber',
    'address': 'addressStreet',
    'additional_address': 'addressAdditional1',
    'phone': 'phone',
    'email': 'email',
    'lastname': 'lastname',
    'company': 'company',
    'firstname': 'firstname'
}

class FindContact(Thread):
    def __init__(self, text, log, config, web_service, locale):
        Thread.__init__(self, name='contactThread')
        self.log = log
        self.text = text
        self.contact = ''
        self.min_ratio = 80
        self.locale = locale
        self.config = config
        self.custom_mail = ''
        self.custom_phone = ''
        if 'sender_min_ratio' in config.cfg['IA']:
            self.min_ratio = int(config.cfg['IA']['sender_min_ratio'])
        self.web_service = web_service

    def run(self):
        """
        Override the default run function of threading package
        This will search for a contact into the text of original PDF
        It will use mail, phone or URL regex

        """

        found_contact = False

        for phone in re.finditer(r"" + self.locale.phoneRegex + "", self.text):
            self.log.info('Find PHONE : ' + phone.group())

            # Now sanitize email to delete potential OCR error
            sanitized_phone = re.sub(r"[^0-9]", "", phone.group())
            self.log.info('Sanitized PHONE : ' + sanitized_phone)

            contact = self.web_service.retrieve_contact_by_phone(sanitized_phone)
            if contact:
                found_contact = True
                self.contact = contact
                self.log.info('Find phone in MEM Courrier, get it : ' + sanitized_phone)
                break
            else:
                # Add the phone into a custom value (custom_t10 by default)
                self.custom_phone += sanitized_phone + ';'
                continue

        if not found_contact:
            for mail in re.finditer(r"" + self.locale.emailRegex + "", self.text):
                self.log.info('Find E-MAIL : ' + mail.group())
                # Now sanitize email to delete potential OCR error
                sanitized_mail = re.sub(r"[" + self.config.cfg['GLOBAL']['sanitizestr'] + "]", "", mail.group())
                self.log.info('Sanitized E-MAIL : ' + sanitized_mail)

                contact = self.web_service.retrieve_contact_by_mail(sanitized_mail)
                if contact:
                    self.contact = contact
                    self.log.info('Find E-MAIL in MEM Courrier, attach it to the document')
                    break
                else:
                    # Add the e-mail into a custom value (custom_t10 by default)
                    self.custom_mail += sanitized_mail + ';'
                    continue

    def compare_contact(self, contact, ai_contact):
        match_contact = {}
        global_ratio = 0
        cpt = 0

        for key in ai_contact:
            if ai_contact[key]:
                if key in contact:
                    if contact[key]:
                        match_contact[key] = fuzz.ratio(ai_contact[key].lower(), contact[key].lower())
                        global_ratio += match_contact[key]
                        cpt += 1
        global_ratio = global_ratio / cpt

        if global_ratio >= self.min_ratio:
            self.log.info('Global ratio above ' + str(self.min_ratio) + '%, keep the original contact')
        return global_ratio >= self.min_ratio

    def find_contact_by_ai(self, ai_contact):
        found_contact = {}
        for key in ai_contact:
            if ai_contact[key]:
                found_contact[MAPPING[key]] = ai_contact[key][:254]
                if isinstance(found_contact[MAPPING[key]], list):
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]][0]

                if key in ('lastname', 'company', 'city'):
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]].upper()
                elif key == 'firstname':
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]].capitalize()
                elif key == 'email':
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]].lower()
                elif key == 'postal_code' and len(found_contact[MAPPING[key]]) != 5:
                    found_contact[MAPPING[key]] = ''

        contact = {}
        if (('email' not in found_contact or not found_contact['email']) and
                ('phone' not in found_contact or not found_contact['phone'])):
            self.start()
            self.join()
            if self.contact:
                found_contact['email'] = self.contact['email']
                found_contact['phone'] = self.contact['phone']

        if 'email' in found_contact and found_contact['email']:
            if not self.contact:
                contact = self.web_service.retrieve_contact_by_mail(found_contact['email'])
            else:
                contact = self.contact

            if contact:
                self.log.info('Contact found using email : ' + found_contact['email'])
                contact = self.web_service.retrieve_contact_by_id(contact['id'])
                match_contact = self.compare_contact(contact, found_contact)
                if match_contact:
                    return contact
                self.log.info(f'Global ratio under {self.min_ratio}%, search using phone')

        if 'phone' in found_contact and found_contact['phone']:
            if not self.contact:
                contact = self.web_service.retrieve_contact_by_phone(found_contact['phone'])
            else:
                contact = self.contact

            tmp_contact = False
            if contact:
                tmp_contact = contact

            if isinstance(found_contact['phone'], list):
                found_contact['phone'] = found_contact['phone'][0]

            if contact:
                self.log.info('Contact found using phone : ' + found_contact['phone'])
                contact = self.web_service.retrieve_contact_by_id(contact['id'])
                match_contact = self.compare_contact(contact, found_contact)
                if match_contact:
                    return contact
                self.log.info(f'Global ratio under {self.min_ratio}%, insert temporary contact')
            else:
                if tmp_contact:
                    contact = tmp_contact

        found_contact['status'] = 'TMP'
        if not contact:
            self.log.info('No contact found, create a temporary contact')

        res, temporary_contact = self.web_service.create_contact(found_contact)
        if res:
            self.log.info('Temporary contact created with success : ' + str(temporary_contact['id']))
            if contact:
                contact['externalId'] = {
                    'ia_tmp_contact_id': temporary_contact['id']
                }

                if 'civility' in contact and contact['civility'] and 'id' in contact['civility']:
                    contact['civility'] = contact['civility']['id']

                self.web_service.update_contact_external_id(contact)
                return contact
        else:
            self.log.error('Error while creating temporary contact')
            return False
        return temporary_contact
