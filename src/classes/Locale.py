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

import json


class Locale:
    def __init__(self, config):
        self.refOnly = ''
        self.arrayDate = []
        self.regexDate = ''
        self.formatDate = ''
        self.subjectOnly = ''
        self.regexSubject = ''
        self.dateTimeFormat = ''
        self.locale = config.cfg['LOCALE']['locale']
        self.localeOCR = config.cfg['LOCALE']['localeocr']
        self.date_path = config.cfg['LOCALE']['localedatepath']

        with open(self.date_path + self.locale + '.json') as file:
            fp = json.load(file)
            self.refOnly = fp['refOnly']
            self.URLRegex = fp['URLRegex']
            self.regexDate = fp['dateRegex']
            self.formatDate = fp['dateFormat']
            self.arrayDate = fp['dateConvert']
            self.phoneRegex = fp['phoneRegex']
            self.emailRegex = fp['emailRegex']
            self.subjectOnly = fp['subjectOnly']
            self.regexSubject = fp['subjectRegex']
            self.dateTimeFormat = fp['dateTimeFormat']
