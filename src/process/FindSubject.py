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
from threading import Thread

class FindSubject(Thread):
    def __init__(self, text, Locale, Log):
        Thread.__init__(self, name='subjectThread')
        self.text       = text
        self.Log        = Log
        self.Locale     = Locale
        self.subject    = None

    @staticmethod
    def loopFindSubject(array, compilePattern):
        pattern = re.compile(compilePattern)
        for value in array:
            if pattern.search(value):
                return value
        return None

    def run(self):
        subjectArray = []
        for _subject in re.finditer(r"" + self.Locale.regexSubject + "", self.text):
            if len(_subject.group()) > 3:
                # Using the [:-2] to delete the ".*" of the regex
                # Useful to keep only the subject and delete the left part (e.g : remove "Objet : " from "Objet : Candidature pour un emploi - Démo Salindres")
                subjectArray.append( _subject.group())

        # If there is more than one subject found, prefer the "Object" one instead of "Ref"
        if len(subjectArray) > 1:
            subject = self.loopFindSubject(subjectArray, self.Locale.subjectOnly)
            if subject:
                self.subject = re.sub(r"" + self.Locale.regexSubject[:-2] + "", '', subject).strip()
            else:
                subject = self.loopFindSubject(subjectArray, self.Locale.refOnly)
                if subject:
                    self.subject = re.sub(r"" + self.Locale.regexSubject[:-2] + "", '', subject).strip()
        elif len(subjectArray) == 1:
            self.subject = re.sub(r"" + self.Locale.regexSubject[:-2] + "", '', subjectArray[0]).strip()
        else:
            self.subject = ''

        if self.subject is not '':
            self.Log.info("Find the following subject : " + self.subject, 'FindSubject.py', 60)