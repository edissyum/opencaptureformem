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
import uuid
import pypdf
import shutil
import pytesseract
from pdf2image import convert_from_path


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
        Start from standard PDF, with no OCR, and create a searchable PDF, with OCR. Thanks to pytesseract python lib

        :param pdf: Path to original pdf (not searchable, without OCR)
        :param tmp_path: Path to store the final pdf, searchable with OCR
        :param separator: Class Separator instance
        """

        images = convert_from_path(pdf, dpi=400)
        cpt = 1
        _uuid = str(uuid.uuid4())
        output_file = tmp_path + '/result.pdf'

        for i in range(len(images)):
            output = tmp_path + '/to_merge_' + _uuid + '-' + str(cpt).zfill(3)
            images[i].save(output + '.jpg', 'JPEG')
            pdf_content = pytesseract.image_to_pdf_or_hocr(output + '.jpg', extension='pdf')

            try:
                os.remove(output + '.jpg')
            except FileNotFoundError:
                pass

            with open(output + '.pdf', 'w+b') as f:
                f.write(pdf_content)
            cpt = cpt + 1

        if cpt > 2:
            pdf_to_merge = []
            for file in sorted(os.listdir(tmp_path)):
                if file.startswith('to_merge_'):
                    if file.endswith('.pdf'):
                        pdf_to_merge.append(tmp_path + '/' + file)

            merger = pypdf.PdfMerger()
            for _p in pdf_to_merge:
                merger.append(_p)
            merger.write(output_file)
            merger.close()
        else:
            shutil.move(tmp_path + '/to_merge_' + _uuid + '-001.pdf', tmp_path + '/result.pdf')

        if separator.convert_to_pdfa == "True":
            output_file = tmp_path + '/result-pdfa.pdf'
            separator.convert_to_pdfa_function(output_file, tmp_path + '/result.pdf', self.Log)

        self.searchablePdf = output_file
