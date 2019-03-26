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
import sys
import argparse
import classes.Log as logClass
import classes.PyOCR as ocrClass
import classes.Locale as localeClass
import classes.Images as imagesClass
import classes.Config as configClass
import classes.Separator as separatorClass
import classes.WebServices as webserviceClass
from process.OCForMaarch import process

if __name__ == '__main__':
    # construct the argument parse and parse the arguments
    ap      = argparse.ArgumentParser()
    ap.add_argument("-f", "--file", required=False, help="path to file")
    ap.add_argument("-c", "--config", required=True, help="path to config.xml")
    ap.add_argument("-d", '--destination', required=False, help="Default destination")
    ap.add_argument("-p", "--path", required=False, help="path to folder containing documents")
    ap.add_argument("--read-destination-from-filename", '--RDFF', dest='RDFF', action="store_true", required=False, help="Read destination from filename")
    args    = vars(ap.parse_args())

    if args['path'] is None and args['file'] is None:
        sys.exit('No file or path were given')
    elif args['path'] is not None and args['file'] is not None:
        sys.exit('Chose between path or file')

    # Init all the necessary classes
    Config      = configClass.Config(args['config'])
    Log         = logClass.Log(Config.cfg['GLOBAL']['logfile'])
    fileName    = Config.cfg['GLOBAL']['tmpfilename']
    Locale      = localeClass.Locale(Config)
    Ocr         = ocrClass.PyOCR(Locale.localeOCR)
    Separator   = separatorClass.Separator(Log, Config)
    WebService  = webserviceClass.WebServices(
        Config.cfg['OCForMaarch']['host'],
        Config.cfg['OCForMaarch']['user'],
        Config.cfg['OCForMaarch']['password'],
        Log
    )
    Image = imagesClass.Images(
        fileName,
        int(Config.cfg['GLOBAL']['resolution']),
        int(Config.cfg['GLOBAL']['compressionquality'])
    )

    # Start process
    if args['path'] is not None:
        path = args['path']
        if Separator.enabled == 'True':
            for fileToSep in os.listdir(path):
                Separator.process(path + fileToSep)
            path = Separator.output_dir_pdfa if Separator.convert_to_pdfa == 'True' else Separator.output_dir

        # Find file in the wanted folder (default or exported pdf after qrcode separation)
        for file in os.listdir(path):
            process(args, path + file, Log, Separator, Config, Image, Ocr, Locale, WebService)

    elif args['file'] is not None:
        path = args['file']
        if Separator.enabled == 'True':
            Separator.process(path)
            if Separator.error: # in case the file is not a pdf, process as an Image
                process(args, path, Log, Separator, Config, Image, Ocr, Locale, WebService)
            else:
                path = Separator.output_dir_pdfa if Separator.convert_to_pdfa == 'True' else Separator.output_dir
                for file in os.listdir(path):
                    process(args, path + file, Log, Separator, Config, Image, Ocr, Locale, WebService)
        else:
            # Process the file and send it to Maarch
            process(args, path, Log, Separator, Config, Image, Ocr, Locale, WebService)



