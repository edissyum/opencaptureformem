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
from datetime import datetime
from threading import Thread

class FindDate(Thread):
    def __init__(self, text, Locale, Log, Config):
        Thread.__init__(self, name='dateThread')
        self.text       = text
        self.Locale     = Locale
        self.date       = ''
        self.Log        = Log
        self.Config     = Config

    def run(self):
        for _date in re.finditer(r"" + self.Locale.regexDate + "", self.text.replace(' ', '')):
            self.date = _date.group().replace('1er', '01')   # Replace some possible inconvenient char
            self.date = self.date.replace(',', '')           # Replace some possible inconvenient char
            self.date = self.date.replace('/', ' ')          # Replace some possible inconvenient char
            self.date = self.date.replace('-', ' ')          # Replace some possible inconvenient char

            dateConvert = self.Locale.arrayDate
            for key in dateConvert:
                for month in dateConvert[key]:
                    if month.lower() in self.date.lower():
                        self.date = (self.date.lower().replace(month.lower(), key))
                        break

            try:
                self.date   = datetime.strptime(self.date, self.Locale.dateTimeFomat).strftime(self.Locale.formatDate)
                # Check if the date of the document isn't too old. 62 (default value) is equivalent of 2 months
                today       = datetime.now()
                docDate     = datetime.strptime(self.date, self.Locale.formatDate)
                timedelta   = today - docDate

                if timedelta.days > int(self.Config.cfg['OCForMaarch']['timedelta']) or timedelta.days < 0 :
                    self.Log.info("Date is older than 2 month or in the future: " + self.date)
                    self.date = ''
                    continue
                else:
                    self.Log.info("Date found : " + self.date)
                    break
            except ValueError:
                self.Log.info("Date wasn't in a good format : " + self.date)
                self.date = ''
                continue
