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
    def __init__(self, locale, log, config):
        self.Log = log
        self.text = ''
        self.tool = ''
        self.lang = locale
        self.Config = config
        self.searchablePdf = ''

    def text_builder(self, img):
        """
        OCRise image to simple string contains all the text

        :param img: Path to image file which will be ocresised
        """
        try:
            self.text = pytesseract.image_to_string(
                img,
                lang=self.lang
            )
        except pytesseract.pytesseract.TesseractError as t:
            self.Log.error('Tesseract ERROR : ' + str(t))

    def generate_searchable_pdf(self, pdf, tmp_path, separator):
        """
        Start from standard PDF, with no OCR, and create a searchable PDF, with OCR. Thanks to ocrmypdf python lib

        :param pdf: Path to original pdf (not searchable, without OCR)
        :param tmp_path: Path to store the final pdf, searchable with OCR
        :param separator: Class Separator instance
        """
        try:
            output_file = tmp_path + '/result.pdf'
            ocrmypdf.ocr(pdf, output_file, output_type='pdf', language=self.lang, skip_text=True, progress_bar=False, jobs=int(self.Config.cfg['GLOBAL']['nbthreads']))
            if separator.convert_to_pdfa == "True":
                output_file = tmp_path + '/result-pdfa.pdf'
                separator.convert_to_pdfa_function(output_file, tmp_path + '/result.pdf', self.Log)

            self.searchablePdf = open(output_file, 'rb').read()
        except ocrmypdf.exceptions.PriorOcrFoundError as e:
            self.Log.error(e)
