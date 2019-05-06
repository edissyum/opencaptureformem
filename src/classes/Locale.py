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
