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
import sys
import os
import queue
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
# Before, do : pip3 install kuyruk-manager

@OCforMaarch.task()
def launch(args):
    # Init all the necessary classes
    Config      = configClass.Config(args['config'])
    Log         = logClass.Log(Config.cfg['GLOBAL']['logfile'])
    fileName    = Config.cfg['GLOBAL']['tmppath'] + 'tmp.jpg'
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
        int(Config.cfg['GLOBAL']['compressionquality'])
    )

    # Start process
    if args['path'] is not None:
        path = args['path']
        if Separator.enabled == 'True':
            for fileToSep in os.listdir(path):
                if not Image.check_file_integrity(path + fileToSep, Config):
                    Log.error('The integrity of file could\'nt be verified : ' + str(path + fileToSep))
                    sys.exit()
                Separator.run(path + fileToSep)
            path = Separator.output_dir_pdfa if Separator.convert_to_pdfa == 'True' else Separator.output_dir

        # Create the Queue to store files
        q = queue.Queue()
        # Find file in the wanted folder (default or exported pdf after qrcode separation)
        for file in os.listdir(path):
            q = process(args, path + file, Log, Separator, Config, Image, Ocr, Locale, WebService, q)

        while not q.empty():
            runQueue(q, Config, Image, Log, WebService, Ocr)

    elif args['file'] is not None:
        path = args['file']
        if not Image.check_file_integrity(path, Config):
            Log.error('The integrity of file could\'nt be verified' + str(path))
            sys.exit()

        if Separator.enabled == 'True':
            Separator.run(path)
            if Separator.error: # in case the file is not a pdf, process as an Image
                process(args, path, Log, Separator, Config, Image, Ocr, Locale, WebService)
            else:
                path = Separator.output_dir_pdfa if Separator.convert_to_pdfa == 'True' else Separator.output_dir

                # Create the Queue to store files
                q = queue.Queue()
                # Find file in the wanted folder (default or exported pdf after qrcode separation)
                for file in os.listdir(path):
                    q = process(args, path + file, Log, Separator, Config, Image, Ocr, Locale, WebService, q)

                while not q.empty():
                    runQueue(q, Config, Image, Log, WebService, Ocr)
        else:
            if not Image.check_file_integrity(path, Config):
                Log.error('The integrity of file could\'nt be verified')
                sys.exit()

            # Process the file and send it to Maarch
            process(args, path, Log, Separator, Config, Image, Ocr, Locale, WebService)

