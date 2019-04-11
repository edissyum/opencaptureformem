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
