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
import sys
import time
import queue
import tempfile

# useful to use the worker and avoid ModuleNotFoundError
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from kuyruk import Kuyruk
from kuyruk_manager import Manager
import src.classes.Log as logClass
from src.process.Queue import runQueue
import src.classes.Locale as localeClass
import src.classes.Images as imagesClass
import src.classes.Config as configClass
import src.classes.PyTesseract as ocrClass
from src.process.OCForMaarch import process
import src.classes.Separator as separatorClass
import src.classes.WebServices as webserviceClass

OCforMaarch = Kuyruk()

OCforMaarch.config.MANAGER_HOST = "127.0.0.1"
OCforMaarch.config.MANAGER_PORT = 16501
OCforMaarch.config.MANAGER_HTTP_PORT = 16500

m = Manager(OCforMaarch)

# If needed just run "kuyruk --app src.main.OCforMaarch manager" to have web dashboard of current running worker

@OCforMaarch.task()
def launch(args):
    start = time.time()
    # Init all the necessary classes
    Config      = configClass.Config(args['config'])
    Log         = logClass.Log(Config.cfg['GLOBAL']['logfile'])
    tmpFolder   = tempfile.mkdtemp(dir=Config.cfg['GLOBAL']['tmppath'])
    fileName    = tempfile.NamedTemporaryFile(dir=tmpFolder).name + '.jpg'

    Locale      = localeClass.Locale(Config)
    Ocr         = ocrClass.PyTesseract(Locale.localeOCR, Log)
    Separator   = separatorClass.Separator(Log, Config)
    WebService  = webserviceClass.WebServices(
        Config.cfg['OCForMaarch']['host'],
        Config.cfg['OCForMaarch']['user'],
        Config.cfg['OCForMaarch']['password'],
        Log
    )
    Image       = imagesClass.Images(
        fileName,
        int(Config.cfg['GLOBAL']['resolution']),
        int(Config.cfg['GLOBAL']['compressionquality']),
        Log
    )

    # Start process
    if args['path'] is not None:
        path = args['path']
        if Separator.enabled == 'True' and args['process'] == 'incoming':
            for fileToSep in os.listdir(path):
                if not Image.check_file_integrity(path + fileToSep, Config):
                    Log.error('The integrity of file could\'nt be verified : ' + str(path + fileToSep))
                    os._exit(os.EX_IOERR)
                Separator.run(path + fileToSep)
            path = Separator.output_dir_pdfa if Separator.convert_to_pdfa == 'True' else Separator.output_dir

        # Create the Queue to store files
        q = queue.Queue()
        # Find file in the wanted folder (default or exported pdf after qrcode separation)
        for file in os.listdir(path):
            q = process(args, path + file, Log, Separator, Config, Image, Ocr, Locale, WebService, tmpFolder, q)

        while not q.empty():
            runQueue(q, Config, Image, Log, WebService, Ocr)

    elif args['file'] is not None:
        path = args['file']
        if not Image.check_file_integrity(path, Config):
            Log.error('The integrity of file could\'nt be verified' + str(path))
            os._exit(os.EX_IOERR)

        if Separator.enabled == 'True' and args['process'] == 'incoming':
            Separator.run(path)
            if Separator.error: # in case the file is not a pdf, process as an Image
                process(args, path, Log, Separator, Config, Image, Ocr, Locale, WebService, tmpFolder)
            else:
                path = Separator.output_dir_pdfa if Separator.convert_to_pdfa == 'True' else Separator.output_dir

                # Create the Queue to store files
                q = queue.Queue()
                # Find file in the wanted folder (default or exported pdf after qrcode separation)
                for file in os.listdir(path):
                    q = process(args, path + file, Log, Separator, Config, Image, Ocr, Locale, WebService, tmpFolder, q)

                while not q.empty():
                    runQueue(q, Config, Image, Log, WebService, Ocr)
        else:
            if not Image.check_file_integrity(path, Config):
                Log.error('The integrity of file could\'nt be verified')
                os._exit(os.EX_IOERR)

            # Process the file and send it to Maarch
            process(args, path, Log, Separator, Config, Image, Ocr, Locale, WebService, tmpFolder)

    end = time.time()

    def timer(startTime, endTime):
        hours, rem = divmod(endTime - startTime, 3600)
        minutes, seconds = divmod(rem, 60)
        return "{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds)

    # Empty the tmp dir to avoid residual file
    for file in os.listdir(tmpFolder):
        try:
            os.remove(tmpFolder + '/' + file)
        except FileNotFoundError as e:
            Log.error('Unable to delete ' + tmpFolder + '/' + file + ' on temp folder: ' + str(e))
    try:
        os.rmdir(tmpFolder)
    except FileNotFoundError as e:
        Log.error('Unable to delete ' + tmpFolder + ' on temp folder: ' + str(e))

    Log.info('Process end after ' + timer(start,end) + '')

    os._exit(os.EX_OK)