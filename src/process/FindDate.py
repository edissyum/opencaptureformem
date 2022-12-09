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
from threading import Thread
from datetime import datetime


class FindDate(Thread):
    def __init__(self, text, locale, log, config):
        Thread.__init__(self, name='dateThread')
        self.Log = log
        self.date = ''
        self.text = text
        self.Locale = locale
        self.Config = config

    def format_date(self, _date):
        self.date = _date.group().replace('1er', '01')  # Replace some possible inconvenient char
        self.date = self.date.replace(',', ' ')  # Replace some possible inconvenient char
        self.date = self.date.replace('/', ' ')  # Replace some possible inconvenient char
        self.date = self.date.replace('-', ' ')  # Replace some possible inconvenient char
        self.date = self.date.replace('.', ' ')  # Replace some possible inconvenient char
        date_convert = self.Locale.arrayDate
        for key in date_convert:
            for month in date_convert[key]:
                if month.lower() in self.date.lower():
                    self.date = (self.date.lower().replace(month.lower(), key))
                    break

        try:
            self.date = datetime.strptime(self.date, self.Locale.dateTimeFormat).strftime(self.Locale.formatDate)
            # Check if the date of the document isn't too old. 62 (default value) is equivalent of 2 months
            today = datetime.now()
            doc_date = datetime.strptime(self.date, self.Locale.formatDate)
            timedelta = today - doc_date
            if int(self.Config.cfg['OCForMEM']['timedelta']) != -1:
                if timedelta.days > int(self.Config.cfg['OCForMEM']['timedelta']) or timedelta.days < 0:
                    self.Log.info("Date is older than " + str(self.Config.cfg['OCForMEM']['timedelta']) + " days or in the future: " + self.date)
                    self.date = ''
            elif timedelta.days < 0:
                self.Log.info("Date is in the future: " + self.date)
                self.date = ''

            if self.date:
                self.Log.info("Date found : " + self.date)
            return True
        except ValueError:
            self.Log.info("Date wasn't in a good format : " + self.date)
            self.date = ''

    def run(self):
        """
        Override the default run function of threading package
        This will search for a date into the text of original PDF

        """
        for _date in re.finditer(r"" + self.Locale.regexDate + "", re.sub(r'(\d)\s+(\d)', r'\1\2', self.text)):  # The re.sub is useful to fix space between numerics
            if self.format_date(_date):
                return True

        if not self.date:
            for _date in re.finditer(r"" + self.Locale.regexDate + "", self.text):
                if self.format_date(_date):
                    return True

