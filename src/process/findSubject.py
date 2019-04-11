import re
from threading import Thread

class findSubject(Thread):
    def __init__(self, text):
        Thread.__init__(self, name='subjectThread')
        self.text       = text
        self.subject    = None

    def run(self):
        for _subject in re.finditer(r"[o,O]bje[c]?t\s*(:)?\s*.*", self.text):
            self.subject = re.sub(r"[o,O]bje[c]?t\s*(:)?\s*", '', _subject.group())
            break
