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
import pytesseract

class PyTesseract:
    def __init__(self, locale):
        self.text               = ''
        self.tool               = ''
        self.lang               = locale
        self.searchablePdf      = ''

    def text_builder(self, img):
        self.text = pytesseract.image_to_string(
            img,
            lang=self.lang
        )

    def generate_searchable_pdf(self, pdf, Image, Config):
        tmpPath = Config.cfg['GLOBAL']['tmppath']
        Image.open_img_with_wand(pdf, tmpPath + 'tmp.jpg')
        i = 0
        sortedImgList = Image.sorted_file(tmpPath, 'jpg')
        for img in sortedImgList:
            tmpSearchablePdf =  pytesseract.image_to_pdf_or_hocr(
                img[1],
                extension='pdf'
            )
            f = open(tmpPath + 'tmp-'+ str(i) +'.pdf', 'wb')
            f.write(bytearray(tmpSearchablePdf))
            f.close()
            i = i + 1
            os.remove(img[1])

        sortedPdfList       = Image.sorted_file(tmpPath, 'pdf')
        self.searchablePdf  = Image.merge_pdf(sortedPdfList, tmpPath)
