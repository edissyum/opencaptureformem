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

import os
import shutil
from threading import Thread

def runQueue(q, Config, Image, Log, WebService, Ocr):
    numberOfThreads = int(Config.cfg['GLOBAL']['nbthreads'])
    threads =  []
    for i in range(numberOfThreads):
        thread = ProcessQueue(q, Config, Image, Log, WebService, Ocr, i)
        thread.start()
        threads.append(thread)

    for t in threads:
        t.join()

class ProcessQueue(Thread):
    def __init__(self, q, Config, Image, Log, WebService, Ocr, cpt):
        Thread.__init__(self, name='processQueue' + str(cpt))
        self.queue      = q
        self.Log        = Log
        self.Ocr        = Ocr
        self.Config     = Config
        self.Image      = Image
        self.WebService = WebService

    def run(self):
        while not self.queue.empty():
            queueInfo   = self.queue.get()
            file        = queueInfo['file']
            date        = queueInfo['date']
            subject     = queueInfo['subject']
            contact     = queueInfo['contact']
            fileToSend  = queueInfo['fileToSend']
            destination = queueInfo['destination']

            # Send to Maarch
            res = self.WebService.insert_with_args(fileToSend, self.Config, contact, subject, date, destination)
            if res:
                self.Log.info("Insert OK : " + res)
                try:
                    os.remove(file)
                except FileNotFoundError as e:
                    self.Log.error('Unable to delete ' + file + ' : ' + str(e))
                return True
            else:
                shutil.move(file, self.Config.cfg['GLOBAL']['errorpath'] + file)
                return False
