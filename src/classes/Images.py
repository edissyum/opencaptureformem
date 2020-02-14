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
import shutil

import PyPDF2
from PIL import Image
from wand.color import Color
from wand.image import Image as Img
from wand import exceptions as wandExcept

class Images:
    def __init__(self, jpgName, res, quality, Log, Config):
        Image.MAX_IMAGE_PIXELS      = None  # Disable to avoid DecompressionBombWarning error
        self.jpgName                = jpgName
        self.resolution             = res
        self.compressionQuality     = quality
        self.img                    = None
        self.Log                    = Log
        self.Config                 = Config.cfg

    # Convert the first page of PDF to JPG and open the image
    def pdf_to_jpg(self, pdfName, openImg = True):
        res = self.save_img_with_wand(pdfName, self.jpgName)
        if res is not False:
            if openImg:
                self.img = Image.open(self.jpgName)
            return True
        else:
            try:
                shutil.move(pdfName.replace('[0]', ''), self.Config['GLOBAL']['errorpath'])
            except shutil.Error as e2:
                self.Log.error('Moving file ' + pdfName.replace('[0]', '') + ' error : ' + str(e2))
            return False

    # Simply open an
    def open_img(self, img):
        self.img = Image.open(img)

    # Save pdf with one or more pages into JPG file
    def save_img_with_wand(self, pdfName, output):
        try:
            with Img(filename=pdfName, resolution=self.resolution) as pic:
                pic.compression_quality = self.compressionQuality
                pic.background_color    = Color("white")
                pic.alpha_channel       = 'remove'
                pic.save(filename=output)

        except wandExcept.WandRuntimeError as e:
            self.Log.error(e)
            self.Log.error('Exiting program...Fix the issue and restart the service')
            return False
        except wandExcept.CacheError as e:
            self.Log.error(e)
            self.Log.error('Exiting program...Fix the issue and restart the service')
            return False
        except wandExcept.PolicyError as e:
            self.Log.error(e)
            self.Log.error('Maybe you have to check the PDF rights in ImageMagick policy.xml file')
            self.Log.error('Exiting programm...Fix the issue and restart the service')
            return False

    def check_file_integrity(self, file, Config):
        isFull = False
        while not isFull:
            try:
                with open(file, 'rb') as doc:
                    # size and size2 allow to check if file is full (to avoid process truncate file while files was send over network)
                    size = os.path.getsize(file)
                    time.sleep(1)
                    size2 = os.path.getsize(file)
                    if size2 == size:
                        if file.endswith(".pdf"):
                            try:
                                PyPDF2.PdfFileReader(doc)
                            except PyPDF2.utils.PdfReadError:
                                shutil.move(file, Config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
                                return False
                            else:
                                return True
                        elif file.endswith('.jpg'):
                            try:
                                Image.open(file)
                            except OSError:
                                return False
                            else:
                                return True
                    else:
                        continue
            except PermissionError as e:
                self.Log.error(e)
                return False
