import re
from threading import Thread, currentThread

class findContact(Thread):
    def __init__(self, text, Log, Config, WebService):
        Thread.__init__(self)
        self.text       = text
        self.Log        = Log
        self.Config     = Config
        self.WebService = WebService
        self.contact    = ''

    def run(self):
        print(currentThread().getName() + ' Starting Contact')
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

        print(currentThread().getName() + ' Exiting Contact')