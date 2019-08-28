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
from wand import exceptions as wandExcept
import shutil
import PyPDF2
from PIL import Image
from wand.image import Image as Img
from wand.color import Color


class Images:
    def __init__(self, jpgName, res, quality, Log):
        Image.MAX_IMAGE_PIXELS      = None  # Disable to avoid DecompressionBombWarning error
        self.jpgName                = jpgName
        self.resolution             = res
        self.compressionQuality     = quality
        self.img                    = None,
        self.Log                    = Log

    # Convert the first page of PDF to JPG and open the image
    def pdf_to_jpg(self, pdfName, openImg=True):
        self.save_img_with_wand(pdfName, self.jpgName)
        if openImg:
            self.img = Image.open(self.jpgName)

    # Simply open an
    def open_img(self, img):
        self.img = Image.open(img)

    # Save pdf with one or more pages into JPG file
    def save_img_with_wand(self, pdfName, output):
        try:
            with Img(filename=pdfName, resolution=300) as pic:
                pic.compression_quality = self.compressionQuality
                pic.background_color = Color("white")
                pic.alpha_channel = 'remove'
                pic.save(filename=output)
        except wandExcept.WandRuntimeError as e:
            self.Log.error(e)
            self.Log.error('Exiting program...')
            sys.exit()
        except wandExcept.CacheError as e:
            self.Log.error(e)
            self.Log.error('Exiting program...')
            sys.exit()

    @staticmethod
    def sorted_file(path, extension):
        file_json = []
        for file in os.listdir(path):
            if file.endswith("." + extension):
                filename    = os.path.splitext(file)[0]
                isCountable = filename.split('-')
                if len(isCountable) > 1 :
                    cpt = isCountable[1]
                    if len(cpt) == 1:
                        tmpCpt = '0' + str(cpt)
                        cpt = tmpCpt
                    file_json.append((cpt, path + file))
                else:
                    file_json.append(('00', path + file))
        sorted_file = sorted(file_json, key=lambda fileCPT: fileCPT[0])
        return sorted_file

    @staticmethod
    def merge_pdf(fileSorted, tmpPath):
        merger = PyPDF2.PdfFileMerger()
        for pdf in fileSorted:
            merger.append(pdf[1])
            os.remove(pdf[1])
        merger.write(tmpPath + '/result.pdf')
        fileToReturn = open(tmpPath + '/result.pdf', 'rb').read()
        os.remove(tmpPath + '/result.pdf')

        return fileToReturn

    @staticmethod
    def check_file_integrity(file, Config):
        isFull = False
        while not isFull:
            with open(file, 'rb') as doc:
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