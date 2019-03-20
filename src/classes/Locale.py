import json

class Locale:
    def __init__(self, Config):
        self.locale         = Config.cfg['LOCALE']['locale']
        self.localeOCR      = Config.cfg['LOCALE']['localeocr']
        self.arrayDate      = []
        self.regexDate      = ''
        self.formatDate     = ''
        self.dateTimeFomat  = ''
        self.date_path      = Config.cfg['LOCALE']['localedatepath']

        with open(self.date_path + self.locale + '.json') as file:
            fp                  = json.load(file)
            self.arrayDate      = fp['dateConvert']
            self.regexDate      = fp['dateRegex']
            self.formatDate     = fp['dateFormat']
            self.dateTimeFomat  = fp['dateTimeFormat']