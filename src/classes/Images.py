# This file is part of Open-Capture For MEM Courrier.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture For MEM Courrier is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture For MEM Courrier.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import os
import time
import shutil
import pypdf
from PIL import Image
from bs4 import BeautifulSoup
from pdf2image import convert_from_path


class Images:
    def __init__(self, jpg_name, res, quality, log, config):
        Image.MAX_IMAGE_PIXELS = None  # Disable to avoid DecompressionBombWarning error
        self.jpg_name = jpg_name
        self.resolution = res
        self.compressionQuality = quality
        self.img = None
        self.log = log
        self.config = config.cfg

    def html_to_txt(self, html_name):
        """
        Convert html to txt (do not OCRise HTML)

        :param html_name: Path to the html
        :return: Boolean to show if the process ended well
        """

        try:
            with open(html_name, 'r', encoding='utf-8') as file:
                bs_content = BeautifulSoup(file.read(), 'lxml')
                html_content = bs_content.get_text('\n')
        except (OSError, FileNotFoundError) as _e:
            self.log.error('Error while converting HTML to raw text : ' + str(_e))
            return False

        return html_content

    def timer(self, start_time, end_time):
        hours, rem = divmod(end_time - start_time, 3600)
        minutes, seconds = divmod(rem, 60)
        return "{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds)

    def pdf_to_jpg(self, pdf_name, open_img=True):
        """
        Convert the first page of PDF to JPG and open the image

        :param pdf_name: Path to the pdf
        :param open_img: Boolean to open image and store it in class var
        :return: Boolean to show if all the processes ended well
        """
        res = self.save_img_with_pdf2image(pdf_name, self.jpg_name, 1)
        if res is not False:
            if open_img:
                self.img = Image.open(self.jpg_name)
            return True
        try:
            shutil.move(pdf_name, self.config['GLOBAL']['errorpath'])
        except shutil.Error as _e:
            self.log.error('Moving file ' + pdf_name + ' error : ' + str(_e))
        return False

    def save_img_with_pdf2image(self, pdf_name, output, page=None):
        try:
            output = os.path.splitext(output)[0]
            bck_output = os.path.splitext(output)[0]
            images = convert_from_path(pdf_name, first_page=page, last_page=page, dpi=400)
            cpt = 1
            for i in range(len(images)):
                if not page:
                    output = bck_output + '-' + str(cpt).zfill(3)
                images[i].save(output + '.jpg', 'JPEG')
                cpt = cpt + 1
            return True
        except Exception as error:
            self.log.error('Error during pdf2image conversion : ' + str(error))
            return False

    def open_img(self, img):
        """
        Simply open an image and store it in class var

        :param img: path to the image
        """
        self.img = Image.open(img)

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
                        if file.lower().endswith(".pdf"):
                            try:
                                pypdf.PdfReader(doc, strict=False)
                            except pypdf.utils.PdfReadError:
                                shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
                                return False
                            return True
                        elif file.lower().endswith('.html') or file.lower().endswith('.txt'):
                            return True
                        elif file.lower().endswith('.jpg'):
                            try:
                                Image.open(file)
                            except OSError:
                                return False
                            return True
                        else:
                            return False
                    else:
                        count = count + 1
                        continue
            except PermissionError as e:
                self.log.error(e)
                return False
        return False
