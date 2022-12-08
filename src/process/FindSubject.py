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


class FindSubject(Thread):
    def __init__(self, text, locale, log):
        Thread.__init__(self, name='subjectThread')
        self.Log = log
        self.text = text
        self.subject = None
        self.Locale = locale

    def run(self):
        """
        Override the default run function of threading package
        This will search for a subject into the text of original PDF

        """
        subject_array = []
        for _subject in re.finditer(r"" + self.Locale.regexSubject + "", self.text):
            if len(_subject.group()) > 3:
                # Using the [:-2] to delete the ".*" of the regex
                # Useful to keep only the subject and delete the left part (e.g : remove "Objet : " from "Objet : Candidature pour un emploi - Démo Salindres")
                subject_array.append(_subject.group())

        # If there is more than one subject found, prefer the "Object" one instead of "Ref"
        if len(subject_array) > 1:
            subject = loop_find_subject(subject_array, self.Locale.subjectOnly)
            if subject:
                self.subject = re.sub(r"^" + self.Locale.regexSubject[:-2] + "", '', subject).strip()
            else:
                subject = loop_find_subject(subject_array, self.Locale.refOnly)
                if subject:
                    self.subject = re.sub(r"^" + self.Locale.regexSubject[:-2] + "", '', subject).strip()
        elif len(subject_array) == 1:
            self.subject = re.sub(r"^" + self.Locale.regexSubject[:-2] + "", '', subject_array[0]).strip()
        else:
            self.subject = ''

        if self.subject != '':
            self.search_subject_second_line()
            self.Log.info("Find the following subject : " + self.subject)

    def search_subject_second_line(self):
        not_allowed_symbol = [':', '.']
        text = self.text.split('\n')
        cpt = 0
        for line in text:
            find = False
            if self.subject in line:
                next_line = text[cpt + 1]
                if next_line:
                    for letter in next_line:
                        if letter in not_allowed_symbol:  # Check if the line doesn't contain some specific char
                            find = True
                            break
                    if find:
                        continue
                    first_char = next_line[0]
                    if first_char.lower() == first_char:  # Check if first letter of line is not an upper one
                        self.subject += ' ' + next_line
                        break
            cpt = cpt + 1
            char_cpt = 0
            for char in self.subject:
                if char in not_allowed_symbol:
                    self.subject = self.subject[:char_cpt]
                    break
                char_cpt = char_cpt + 1


def loop_find_subject(array, compile_pattern):
    """
    Simple loop to find subject when multiple subject are found

    :param array: Array of subject
    :param compile_pattern: Choose between subject of ref to choose between all the subject in array
    :return: Return the best subject, or None
    """
    pattern = re.compile(compile_pattern)
    for value in array:
        if pattern.search(value):
            return value
    return None
