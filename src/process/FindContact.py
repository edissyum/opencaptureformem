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
from re import match
from thefuzz import fuzz
from threading import Thread


MAPPING = {
    'postal_code': 'addressPostcode',
    'city': 'addressTown',
    'num_address': 'addressNumber',
    'address': 'addressStreet',
    'phone': 'phone',
    'email': 'email',
    'lastname': 'lastname',
    'firstname': 'firstname'
}

class FindContact(Thread):
    def __init__(self, text, log, config, web_service, locale):
        Thread.__init__(self, name='contactThread')
        self.log = log
        self.text = text
        self.contact = ''
        self.Locale = locale
        self.Config = config
        self.custom_mail = ''
        self.custom_phone = ''
        self.web_service = web_service

    def run(self):
        """
        Override the default run function of threading package
        This will search for a contact into the text of original PDF
        It will use mail, phone or URL regex

        """

        found_contact = False

        for phone in re.finditer(r"" + self.Locale.phoneRegex + "", self.text):
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
            for mail in re.finditer(r"" + self.Locale.emailRegex + "", self.text):
                self.log.info('Find E-MAIL : ' + mail.group())
                # Now sanitize email to delete potential OCR error
                sanitized_mail = re.sub(r"[" + self.Config.cfg['GLOBAL']['sanitizestr'] + "]", "", mail.group())
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
        print(match_contact)
        print(global_ratio)
        self.log.info(f'Global ratio of contact found by AI compared to MEM Courrier contact : {global_ratio}%')
        return global_ratio >= 80

    def find_contact_by_ai(self, ai_contact):
        found_contact = {}
        for key in ai_contact:
            if ai_contact[key]:
                found_contact[MAPPING[key]] = ai_contact[key]
        contact = {}
        if 'email' in found_contact:
            contact = self.web_service.retrieve_contact_by_mail(found_contact['email'])
            if contact:
                contact = self.web_service.retrieve_contact_by_id(contact['id'])
        #         self.log.info('Contact found using email : ' + found_contact['email'])
        #         match_contact = self.compare_contact(contact['id'], found_contact)
        #         if match_contact:
        #             return contact

        # if 'phone' in found_contact:
        #     contact = self.web_service.retrieve_contact_by_phone(found_contact['phone'])
        #     if contact:
        #         self.log.info('Contact found using phone : ' + found_contact['phone'])
        #         match_contact = self.compare_contact(contact['id'], found_contact)
        #         if match_contact:
        #             return contact

        self.log.info('No contact found using AI contact or global ratio is too low. Insert new temporary contact')
        res, temporary_contact = self.web_service.create_contact(found_contact)
        if contact and res:
            contact['externalId'] = {
                'ia_tmp_contact_id': temporary_contact['id']
            }
            self.web_service.update_contact_external_id(contact)
