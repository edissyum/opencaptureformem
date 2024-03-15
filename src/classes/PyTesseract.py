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

import io
import pypdf
import pytesseract
from pdf2image import convert_from_path


class PyTesseract:
    def __init__(self, locale, log, config):
        self.log = log
        self.text = ''
        self.tool = ''
        self.lang = locale
        self.config = config
        self.searchable_pdf = ''

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
            self.log.error('Tesseract ERROR : ' + str(t))

    def generate_searchable_pdf(self, pdf, tmp_path, separator):
        """
        Start from standard PDF, with no OCR, and create a searchable PDF, with OCR.
        Thanks to pytesseract python lib

        :param pdf: Path to original pdf (not searchable, without OCR)
        :param tmp_path: Path to store the final pdf, searchable with OCR
        :param separator: Class Separator instance
        """

        with open(pdf, 'rb') as file:
            pdf_reader = pypdf.PdfReader(file)
            page_count = len(pdf_reader.pages)

        output_file = tmp_path + '/result.pdf'
        merger = pypdf.PdfMerger()

        cpt = 1
        for chunk_idx in range(0, page_count, 10):
            start_page = 0 if chunk_idx == 0 else chunk_idx + 1
            end_page = min(chunk_idx + 10, page_count)
            chunk_images = convert_from_path(pdf, first_page=start_page, last_page=end_page, dpi=300)
            for image in chunk_images:
                pdf_content = pytesseract.image_to_pdf_or_hocr(image, extension='pdf')
                merger.append(pypdf.PdfReader(io.BytesIO(pdf_content)))
                cpt = cpt + 1
        merger.write(output_file)
        merger.close()

        if separator.convert_to_pdfa == "True":
            output_file = tmp_path + '/result-pdfa.pdf'
            separator.convert_to_pdfa_function(output_file, tmp_path + '/result.pdf', self.log)

        self.searchable_pdf = output_file
