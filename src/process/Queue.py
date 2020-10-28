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

import os
import shutil
from threading import Thread


def run_queue(q, config, image, log, web_service, ocr):
    """

    :param q: Queue fill with all the processes neede to be launched
    :param config: Class Config instance
    :param image: Class Image instance
    :param log: Class Log instance
    :param web_service: Class WebService instance
    :param ocr: Class Ocr instance
    """
    number_of_threads = int(config.cfg['GLOBAL']['nbthreads'])
    threads = []
    for i in range(number_of_threads):
        thread = ProcessQueue(q, config, image, log, web_service, ocr, i)
        thread.start()
        threads.append(thread)

    for t in threads:
        t.join()


class ProcessQueue(Thread):
    def __init__(self, q, config, image, log, web_service, ocr, cpt):
        Thread.__init__(self, name='processQueue ' + str(cpt))
        self.queue = q
        self.Ocr = ocr
        self.Log = log
        self.Image = image
        self.Config = config
        self.WebService = web_service

    def run(self):
        """
        Override the default run function of threading package
        This will process the queue and insert documents in Maarch

        """
        while not self.queue.empty():
            queue_info = self.queue.get()
            file = queue_info['file']
            date = queue_info['date']
            res_id = queue_info['resId']
            chrono = queue_info['chrono']
            subject = queue_info['subject']
            contact = queue_info['contact']
            _process = self.Config.cfg[queue_info['process']]
            file_to_send = queue_info['fileToSend']
            destination = queue_info['destination']
            is_internal_note = queue_info['isInternalNote']
            custom_mail = queue_info['custom_mail']

            # Send to Maarch
            if 'is_attachment' in self.Config.cfg[queue_info['process']] and  self.Config.cfg[queue_info['process']]['is_attachment'] != '':
                if is_internal_note:
                    res = self.WebService.insert_attachment(file_to_send, self.Config, res_id, queue_info['process'])
                else:
                    res = self.WebService.insert_attachment_reconciliation(file_to_send, chrono, queue_info['process'], self.Config)
            else:
                res = self.WebService.insert_with_args(file_to_send, self.Config, contact, subject, date, destination, _process, custom_mail)

            if res:
                self.Log.info("Insert OK : " + res)
                try:
                    os.remove(file)
                except FileNotFoundError as e:
                    self.Log.error('Unable to delete ' + file + ' after insertion : ' + str(e))
                return True
            else:
                shutil.move(file, self.Config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
                return False
