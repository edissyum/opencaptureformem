import re
from datetime import datetime
from threading import Thread

class findDate(Thread):
    def __init__(self, text, Log, Locale, Config, WebService):
        Thread.__init__(self, name='dateThread')
        self.text       = text
        self.Log        = Log
        self.Locale     = Locale
        self.Config     = Config
        self.WebService = WebService
        self.date       = ''

    def run(self):
        for _date in re.finditer(r"" + self.Locale.regexDate + "", self.text):
            self.date = _date.group().replace('1er', '01')  # Replace some possible inconvenient char
            dateConvert = self.Locale.arrayDate
            for key in dateConvert:
                for month in dateConvert[key]:
                    if month.lower() in self.date:
                        self.date = (self.date.lower().replace(month.lower(), key))
                        break
            try:
                self.date = datetime.strptime(self.date, self.Locale.dateTimeFomat).strftime(self.Locale.formatDate)
                break
            except ValueError as e:
                print(e)
