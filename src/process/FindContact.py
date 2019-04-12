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

import re
from threading import Thread

class FindContact(Thread):
    def __init__(self, text, Log, Config, WebService):
        Thread.__init__(self, name='contactThread')
        self.text       = text
        self.Log        = Log
        self.Config     = Config
        self.WebService = WebService
        self.contact    = ''

    def run(self):
        foundContact = False
        for mail in re.finditer(r"[^@\s]+@[^@\s]+\.[^@\s]+", self.text):
            self.Log.info('Find E-MAIL : ' + mail.group())
            contact = self.WebService.retrieve_contact_by_mail(mail.group())
            if contact:
                foundContact = True
                self.contact = contact
                break
        # If no contact were found, search for URL
        if not foundContact:
            for url in re.finditer(
                    r"((http|https)://)?(www\.)?[a-zA-Z0-9+_.\-]+\.(" + self.Config.cfg['REGEX']['urlpattern'] + ")",
                    self.text
            ):
                self.Log.info('Find URL : ' + url.group())
                contact = self.WebService.retrieve_contact_by_url(url.group())
                if contact:
                    self.contact = contact
                    break
