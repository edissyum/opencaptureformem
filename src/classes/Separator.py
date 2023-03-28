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
# @dev : Pierre-Yvon Bezert <pierreyvon.bezert@edissyum.com>

import os
import re
import cv2
import uuid
import pypdf
import shutil
import pdf2image
import subprocess
from pyzbar.pyzbar import decode
import xml.etree.ElementTree as ET


class Separator:
    def __init__(self, log, config, tmp_folder, process):
        self.pj = []
        self.Log = log
        self.pages = []
        self.nb_doc = 0
        self.nb_pages = 0
        self.pj_list = []
        self.pdf_list = []
        self.qrList = None
        self.error = False
        self.Config = config
        self.enabled = False
        self.process = process
        self.divider = config.cfg['SEPARATOR_QR']['divider']
        self.convert_to_pdfa = config.cfg['SEPARATOR_QR']['exportpdfa']
        tmp_folder_name = os.path.basename(os.path.normpath(tmp_folder))
        self.separation_type = config.cfg['SEPARATOR_QR']['separationtype']
        self.tmp_dir = config.cfg['SEPARATOR_QR']['tmppath'] + '/' + tmp_folder_name + '/'
        self.output_dir = config.cfg['SEPARATOR_QR']['outputpdfpath'] + '/' + tmp_folder_name + '/'
        self.output_dir_pdfa = config.cfg['SEPARATOR_QR']['outputpdfapath'] + '/' + tmp_folder_name + '/'

        os.mkdir(self.output_dir)
        os.mkdir(self.output_dir_pdfa)

    @staticmethod
    def is_blank_page(image, config) -> bool:
        """
         Check if a page is blank

        :param image: Image path
        :param config: Instance of Config class
        :return: True if the page is blank. False if not
        """
        params = cv2.SimpleBlobDetector_Params()
        params.minThreshold = 10
        params.maxThreshold = 200
        params.filterByArea = True
        params.minArea = 20
        params.filterByCircularity = True
        params.minCircularity = 0.1
        params.filterByConvexity = True
        params.minConvexity = 0.87
        params.filterByInertia = True
        params.minInertiaRatio = 0.01

        detector = cv2.SimpleBlobDetector_create(params)
        im = cv2.imread(image)
        keypoints = detector.detect(im)
        rows, cols, channel = im.shape
        blobs_ratio = len(keypoints) / (1.0 * rows * cols)
        if blobs_ratio < float(config['SEPARATOR_QR']['blobsratio']):
            return True
        return False

    def run(self, file):
        """
        Function that runs all the subprocess in order to separate a document using splitter with QR Code

        :param file: Path to pdf file
        """
        self.Log.info('Start page separation using ' + self.separation_type)
        self.pages = []

        try:
            if self.Config.cfg['SEPARATOR_QR']['removeblankpage'] == 'True':
                self.remove_blank_page(file)
            with open(file, 'rb') as pdf_file:
                pdf = pypdf.PdfReader(pdf_file)
                self.nb_pages = len(pdf.pages)

            if self.Config.cfg['SEPARATOR_QR']['separationtype'] == 'C128':
                self.get_xml_c128(file)
            else:
                self.get_xml_qr_code(file)

            self.parse_xml()
            self.check_empty_docs()
            self.set_doc_ends()
            self.extract_and_convert_docs(file)
            if not self.pages or self.nb_pages == 1 and self.pages[0]['is_empty'] is False:
                self.pdf_list.append(self.output_dir + '/' + os.path.basename(file))
            self.extract_pj()
            self.set_doc_ends(True)
            self.extract_and_convert_docs(file, True)

            if len(self.pages) == 0:
                self.extract_only_pj(file)
                if self.pj and self.pdf_list[0] == self.output_dir + '/' + os.path.basename(file):
                    del self.pdf_list[0]

            if len(self.pj) == 0 and len(self.pages) == 0:
                try:
                    shutil.move(file, self.output_dir)
                except shutil.Error as _e:
                    self.Log.error('Moving file ' + file + ' error : ' + str(_e))
                return
        except Exception as _e:
            self.error = True
            self.Log.error("INIT : " + str(_e))

    @staticmethod
    def sorted_files(data):
        """
          Custom function to return a sorted list of file in dir. Works with numeric like 1,2,3,4,5,6,7,8,9,10
          And do not return 1, 10, 2, 20 etc... as the standard sorted function
        :param data:
        :return:
        """
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
        return sorted(data, key=alphanum_key)

    def extract_only_pj(self, file):
        self.parse_xml(True, file)
        if len(self.pj) > 0:
            page = {}
            first_qr_code_page = self.pj[0]['index_sep']
            splitted_file = os.path.basename(file).split(self.divider)
            if len(splitted_file) > 1:
                page['service'] = splitted_file[0]
            else:
                page['service'] = self.Config.cfg[self.process]['destination']
            page['uuid'] = str(uuid.uuid4())
            page['is_empty'] = False
            page['pdf_filename'] = self.output_dir + page['service'] + self.divider + page['uuid'] + '.pdf'
            page['pdfa_filename'] = self.output_dir_pdfa + page['service'] + self.divider + page['uuid'] + '.pdf'
            page['index_start'] = 1
            page['index_end'] = first_qr_code_page
            self.pages.append(page)
            self.extract_and_convert_docs(file, delete_orig=False)
            self.set_doc_ends(True)
            cpt = 0
            for pj_file in self.pj:
                pj_cpt = os.path.basename(os.path.splitext(pj_file['pdf_filename'])[0]).split('#')[1]
                new_filename = self.output_dir + 'PJ_' + page['service'] + self.divider + page['uuid'] + '#' + str(pj_cpt) + '.pdf'
                new_filename_pdfa = self.output_dir_pdfa + 'PJ_' + page['service'] + self.divider + page['uuid'] + '#' + str(pj_cpt) + '.pdf'
                self.pj[cpt]['pdf_filename'] = new_filename
                self.pj[cpt]['pdfa_filename'] = new_filename_pdfa
                cpt += 1
            self.extract_and_convert_docs(file, True)

    def remove_blank_page(self, file):
        pages = pdf2image.convert_from_path(file)
        i = 1
        for page in pages:
            page.save(self.output_dir + '/result-' + str(i) + '.jpg', 'JPEG')
            i = i + 1

        blank_page_exists = False
        pages_to_keep = []
        for _file in self.sorted_files(os.listdir(self.output_dir)):
            if _file.endswith('.jpg'):
                if not self.is_blank_page(self.output_dir + '/' + _file, self.Config.cfg):
                    pages_to_keep.append(os.path.splitext(_file)[0].split('-')[1])
                else:
                    blank_page_exists = True

                try:
                    os.remove(self.output_dir + '/' + _file)
                except FileNotFoundError:
                    pass

        if blank_page_exists:
            infile = pypdf.PdfReader(file)
            output = pypdf.PdfWriter()
            for i in self.sorted_files(pages_to_keep):
                p = infile.pages[int(i) - 1]
                output.add_page(p)

            with open(file, 'wb') as f:
                output.write(f)

    def get_xml_c128(self, file):
        """
        Retrieve the content of a C128 Code

        :param file: Path to pdf file
        """
        pages = pdf2image.convert_from_path(file)
        barcodes = []
        cpt = 0
        for page in pages:
            detected_barcode = decode(page)
            if detected_barcode:
                for barcode in detected_barcode:
                    if barcode.type == 'CODE128':
                        barcodes.append({'text': barcode.data.decode('utf-8'), 'attrib': {'num': cpt}})
            cpt += 1

        if barcodes:
            self.qrList = barcodes

    def get_xml_qr_code(self, file):
        """
        Retrieve the content of a QR Code

        :param file: Path to pdf file
        """
        try:
            xml = subprocess.Popen([
                'zbarimg',
                '--xml',
                '-q',
                '-Sdisable',
                '-Sqr.enable',
                file
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = xml.communicate()
            if out.decode('utf-8') == "<barcodes xmlns='http://zbar.sourceforge.net/2008/barcode'>\n<source href='" + file + "'>\n</source>\n</barcodes>\n":
                return
            if err.decode('utf-8'):
                self.Log.error('ZBARIMG : ' + str(err))
            self.qrList = ET.fromstring(out)
        except subprocess.CalledProcessError as cpe:
            if cpe.returncode != 4:
                self.Log.error("ZBARIMG : \nreturn code: %s\ncmd: %s\noutput: %s\nglobal : %s" % (cpe.returncode, cpe.cmd, cpe.output, cpe))

    def parse_xml(self, is_pj=False, original_filename=False):
        """
        Parse XML content of QR Code to retrieve the destination of the document (in Maarc)

        """

        if self.qrList is None:
            return
        if self.separation_type == 'QR_CODE':
            ns = {'bc': 'http://zbar.sourceforge.net/2008/barcode'}
            indexes = self.qrList[0].findall('bc:index', ns)
        elif self.separation_type == 'C128':
            indexes = self.qrList
        else:
            return
        cpt = 0

        for index in indexes:
            page = {}
            if self.separation_type == 'QR_CODE':
                data = index.find('bc:symbol', ns).find('bc:data', ns)
                text = data.text
                num = index.attrib['num']
                if is_pj:
                    keyword = 'PJSTART'
                else:
                    keyword = 'MAARCH_|MEM_'
            elif self.separation_type == 'C128':
                data = index
                text = data['text']
                num = index['attrib']['num']
                keyword = ''
            else:
                return

            if re.match(keyword, text) is not None:
                page['service'] = text.replace(keyword, '')
                page['index_sep'] = int(num)
                if page['index_sep'] + 1 >= self.nb_pages:  # If last page is a separator
                    page['is_empty'] = True
                else:
                    page['is_empty'] = False
                    page['index_start'] = page['index_sep'] + 2

                page['uuid'] = str(uuid.uuid4())  # Generate random number for pdf filename
                if is_pj:
                    parent_filename = os.path.splitext(os.path.basename(original_filename))[0]
                    page['pdf_filename'] = self.output_dir + 'PJ' + self.divider + parent_filename + '#' + str(cpt) + '.pdf'
                    page['pdfa_filename'] = self.output_dir_pdfa + 'PJ' + self.divider + parent_filename + '#' + str(cpt) + '.pdf'
                    cpt = cpt + 1
                else:
                    page['pdf_filename'] = self.output_dir + page['service'] + self.divider + page['uuid'] + '.pdf'
                    page['pdfa_filename'] = self.output_dir_pdfa + page['service'] + self.divider + page['uuid'] + '.pdf'

                if is_pj:
                    page['original_filename'] = original_filename
                    page['nb_pages'] = self.nb_pages
                    self.pj.append(page)
                else:
                    self.pages.append(page)
            else:
                continue
        if is_pj:
            self.nb_doc = len(self.pj)
        else:
            self.nb_doc = len(self.pages)

    def check_empty_docs(self):
        """
        Check if a document is empty

        """
        for i in range(self.nb_doc - 1):
            if self.pages[i]['index_sep'] + 1 == self.pages[i + 1]['index_sep']:
                self.pages[i]['is_empty'] = True

    def set_doc_ends(self, is_pj=False):
        """
        Set a virtual limit to split document later

        """
        data = self.pages
        if is_pj:
            data = self.pj
            if not data:
                return

        for i in range(self.nb_doc):
            if data[i]['is_empty']:
                continue
            if i + 1 < self.nb_doc:
                if not is_pj or is_pj and data[i]['original_filename'] == data[i + 1]['original_filename']:
                    data[i]['index_end'] = data[i + 1]['index_sep']
                elif is_pj:
                    data[i]['index_end'] = data[i]['nb_pages']
            else:
                if is_pj:
                    data[i]['index_end'] = data[i]['nb_pages']
                else:
                    data[i]['index_end'] = self.nb_pages

    def extract_pj(self):
        if len(self.pages) == 0:
            pass
        else:
            try:
                for page in self.pages:
                    if page['is_empty']:
                        continue
                    self.qrList = None
                    self.get_xml_qr_code(page['pdf_filename'])
                    pdf = pypdf.PdfReader(open(page['pdf_filename'], 'rb'))
                    self.nb_pages = pdf.getNumPages()
                    self.parse_xml(True, page['pdf_filename'])
            except Exception as _e:
                self.Log.error("EACD: " + str(_e))

    def extract_and_convert_docs(self, file, is_pj=False, delete_orig=True):
        """
        If empty doc, move it directly
        Else, split document and export them

        :param file:
        """
        if len(self.pages) == 0 and is_pj is False:
            pass
        else:
            try:
                data = self.pages
                cpt = 0
                if is_pj:
                    data = self.pj
                for page in data:
                    if page['is_empty']:
                        continue
                    pages_to_keep = range(page['index_start'], page['index_end'] + 1)
                    original_pages_to_keep = None
                    if is_pj:
                        self.pj_list.append(page['pdf_filename'])
                        if cpt + 1 == len(self.pj):
                            original_pages_to_keep = range(1, data[0]['index_start'] - 1)
                        file = page['original_filename']
                        cpt = cpt + 1
                    else:
                        self.pdf_list.append(page['pdf_filename'])
                    split_pdf(file, page['pdf_filename'], pages_to_keep, original_pages_to_keep)
                if not is_pj and delete_orig:
                    os.remove(file)
            except Exception as _e:
                self.Log.error("EACD: " + str(_e))

    @staticmethod
    def convert_to_pdfa_function(pdfa_filename, pdf_filename, log):
        """
        Convert a simple PDF to a PDF/A

        :param pdfa_filename: New PDF/A filename
        :param pdf_filename: Old PDF filename
        :param log: Class Log instance
        """
        log.info('Convert file to PDF/A-2B')
        gs_command_line = 'gs#-dNOSAFER#-dPDFA=2#-sColorConversionStrategy=RGB#-dNOOUTERSAVE#-sProcessColorModel=DeviceRGB#-sDEVICE=pdfwrite#-o#%s#-dPDFACompatibilityPolicy=2#PDFA_def.ps#%s' % (
            pdfa_filename, pdf_filename)
        gs_args = gs_command_line.split('#')
        subprocess.check_call(gs_args)
        os.remove(pdf_filename)


def split_pdf(input_path, output_path, pages, original_pages_to_keep=None):
    """
    Finally, split PDF into multiple PDF

    :param input_path: Orignal PDF (including separator with QR Code)
    :param output_path: Final PDF, splitted
    :param pages: Pages which compose the new PDF
    :param original_pages_to_keep: Number of page of original document when we search for PJ
    """
    input_pdf = pypdf.PdfReader(open(input_path, "rb"))
    output_pdf = pypdf.PdfWriter()
    for page in pages:
        output_pdf.add_page(input_pdf.pages[page - 1])
    with open(output_path, "wb") as stream:
        output_pdf.write(stream)

    if original_pages_to_keep:
        original_output_pdf = pypdf.PdfWriter()
        input_pdf_bis = pypdf.PdfReader(open(input_path, "rb"))
        os.remove(input_path)
        for page in original_pages_to_keep:
            original_output_pdf.add_page(input_pdf_bis.pages[page - 1])

        with open(input_path, "wb") as streama:
            original_output_pdf.write(streama)
