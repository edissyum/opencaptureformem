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

import ocrmypdf
import pytesseract

class PyTesseract:
    def __init__(self, locale, Log):
        self.Log                = Log
        self.text               = ''
        self.tool               = ''
        self.lang               = locale
        self.searchablePdf      = ''

    def text_builder(self, img):
        try:
            self.text = pytesseract.image_to_string(
                img,
                lang=self.lang
            )
        except pytesseract.pytesseract.TesseractError as t:
            self.Log.error('Tesseract ERROR : ' + str(t))

    def generate_searchable_pdf(self, pdf, tmpPath):
        try:
            ocrmypdf.ocr(pdf, tmpPath + '/result.pdf', language=self.lang, skip_text = True, progress_bar = False)
            self.searchablePdf = open(tmpPath + '/result.pdf', 'rb').read()
        except ocrmypdf.exceptions.PriorOcrFoundError as e:
            self.Log.error(e)