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

    def run(self):
        for _subject in re.finditer(r"" + self.Locale.regexSubject + "", self.text):
            # Using the [:-2] to delete the ".*" of the regex
            # Useful to keep only the subject and delete the left part (e.g : remove "Objet : " from "Objet : Candidature pour un emploi - Démo Salindres")
            self.subject = re.sub(r"" + self.Locale.regexSubject[:-2] + "", '', _subject.group())
            self.Log.info("Find the following subject : " + self.subject)
            break
