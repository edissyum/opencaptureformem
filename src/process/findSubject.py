import re
from threading import Thread, currentThread

class findSubject(Thread):
    def __init__(self, text):
        Thread.__init__(self)
        self.text       = text
        self.subject    = None

    def run(self):
        print (currentThread().getName() + ' Starting Subject')
        for _subject in re.finditer(r"[o,O]bje[c]?t\s*(:)?\s*.*", self.text):
            self.subject = re.sub(r"[o,O]bje[c]?t\s*(:)?\s*", '', _subject.group())
            break

        print(currentThread().getName() + ' Exiting Subject')