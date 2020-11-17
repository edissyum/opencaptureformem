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
import time
import shutil

from bs4 import BeautifulSoup
import PyPDF2
from PIL import Image
from wand.color import Color
from wand.image import Image as Img
from wand import exceptions as wand_except


class Images:
    def __init__(self, jpg_name, res, quality, log, config):
        Image.MAX_IMAGE_PIXELS = None  # Disable to avoid DecompressionBombWarning error
        self.jpgName = jpg_name
        self.resolution = res
        self.compressionQuality = quality
        self.img = None
        self.Log = log
        self.Config = config.cfg

    def html_to_txt(self, html_name):
        """
        Convert html to txt (do not OCRise HTML)

        :param html_name: Path to the html
        :return: Boolean to show if the process ended well
        """

        try:
            html_content = open(html_name, 'r').read()
            bs_content = BeautifulSoup(html_content, 'lxml')
            html_content = bs_content.get_text('\n')
        except (OSError, FileNotFoundError) as e:
            self.Log.error('Error while converting HTML to raw text : ' + str(e))
            return False

        return html_content

    def pdf_to_jpg(self, pdf_name, open_img=True):
        """
        Convert the first page of PDF to JPG and open the image

        :param pdf_name: Path to the pdf
        :param open_img: Boolean to open image and store it in class var
        :return: Boolean to show if all the processes ended well
        """
        res = self.save_img_with_wand(pdf_name, self.jpgName)
        if res is not False:
            if open_img:
                self.img = Image.open(self.jpgName)
            return True
        else:
            try:
                shutil.move(pdf_name.replace('[0]', ''), self.Config['GLOBAL']['errorpath'])
            except shutil.Error as e2:
                self.Log.error('Moving file ' + pdf_name.replace('[0]', '') + ' error : ' + str(e2))
            return False

    def open_img(self, img):
        """
        Simply open an image and store it in class var

        :param img: path to the image
        """
        self.img = Image.open(img)

    # Save pdf with one or more pages into JPG file
    def save_img_with_wand(self, pdf_name, output):
        """
        Save pdf with on or more pages into JPG file. Called by self.pdf_to_jpg function

        :param pdf_name: path to pdf
        :param output: Filename of temporary jpeg after pdf conversion
        :return: Boolean to show if all the processes ended well
        """
        try:
            with Img(filename=pdf_name, resolution=self.resolution) as pic:
                pic.compression_quality = self.compressionQuality
                pic.background_color = Color("white")
                pic.alpha_channel = 'remove'
                pic.save(filename=output)

        except wand_except.WandRuntimeError as e:
            self.Log.error(e)
            self.Log.error('Exiting program...Fix the issue and restart the service')
            return False
        except wand_except.CacheError as e:
            self.Log.error(e)
            self.Log.error('Exiting program...Fix the issue and restart the service')
            return False
        except wand_except.PolicyError as e:
            self.Log.error(e)
            self.Log.error('Maybe you have to check the PDF rights in ImageMagick policy.xml file')
            self.Log.error('Exiting programm...Fix the issue and restart the service')
            return False

    def check_file_integrity(self, file, config):
        """
        Check if file is not corrupted

        :param file: Path to file
        :param config: Class Config instance
        :return: Boolean to show if all the processes ended well
        """
        is_full = False
        count = 0
        while not is_full and count < 5:
            try:
                with open(file, 'rb') as doc:
                    # size and size2 allow to check if file is full (to avoid process truncate file while files was send over network)
                    size = os.path.getsize(file)
                    time.sleep(1)
                    size2 = os.path.getsize(file)
                    if size2 == size:
                        if file.endswith(".pdf"):
                            try:
                                PyPDF2.PdfFileReader(doc, strict=False)
                            except PyPDF2.utils.PdfReadError:
                                shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
                                return False
                            else:
                                return True
                        elif file.endswith('.html') or file.endswith('.txt'):
                            return True
                        elif file.endswith('.jpg'):
                            try:
                                Image.open(file)
                            except OSError:
                                return False
                            else:
                                return True
                    else:
                        count = count + 1
                        continue
            except PermissionError as e:
                self.Log.error(e)
                return False
        return False
