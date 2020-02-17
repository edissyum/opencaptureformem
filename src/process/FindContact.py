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

import re
import sys
from threading import Thread


class FindContact(Thread):
    def __init__(self, text, log, config, web_service, locale):
        Thread.__init__(self, name='contactThread')
        self.Log = log
        self.text = text
        self.contact = ''
        self.Locale = locale
        self.Config = config
        self.custom_mail = ''
        self.custom_phone = ''
        self.WebService = web_service

    def run(self):
        """
        Override the default run function of threading package
        This will search for a contact into the text of original PDF
        It will use mail, phone or URL regex

        """

        found_contact = False

        for phone in re.finditer(r"" + self.Locale.phoneRegex + "", self.text):
            self.Log.info('Find PHONE : ' + phone.group())

            # Now sanitize email to delete potential OCR error
            sanitized_phone = re.sub(r"[^0-9]", "", phone.group())
            self.Log.info('Sanitized PHONE : ' + sanitized_phone)

            contact = self.WebService.retrieve_contact_by_phone(sanitized_phone)
            if contact:
                found_contact = True
                self.contact = contact
                self.Log.info('Find phone in Maarch, get it : ' + sanitized_phone)
                break
            else:
                # Add the phone into a custom value (custom_t10 by default)
                self.custom_phone += sanitized_phone + ';'
                continue

        if not found_contact:
            for mail in re.finditer(r"" + self.Locale.emailRegex + "", self.text):
                self.Log.info('Find E-MAIL : ' + mail.group())
                # Now sanitize email to delete potential OCR error
                sanitized_mail = re.sub(r"[" + self.Config.cfg['GLOBAL']['sanitizestr'] + "]", "", mail.group())
                self.Log.info('Sanitized E-MAIL : ' + sanitized_mail)

                contact = self.WebService.retrieve_contact_by_mail(sanitized_mail)
                if contact:
                    found_contact = True
                    self.contact = contact
                    self.Log.info('Find E-MAIL in Maarch, attach it to the document')
                    break
                else:
                    # Add the e-mail into a custom value (custom_t10 by default)
                    self.custom_mail += sanitized_mail + ';'
                    continue

        # If no contact were found, search for URL
        if not found_contact:
            for url in re.finditer(
                    r"" + self.Locale.URLRegex + "(" + self.Locale.URLPattern + ")",
                    self.text
            ):
                self.Log.info('Find URL : ' + url.group())
                contact = self.WebService.retrieve_contact_by_url(url.group())
                if contact:
                    self.contact = contact
                    self.Log.info('Find URL in Maarch, get it : ' + url.group())
                    break

        # Stop the thread
        sys.exit()
