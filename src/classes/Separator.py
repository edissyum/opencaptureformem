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
# @dev : Pierre-Yvon Bezert <pierreyvon.bezert@edissyum.com>

import os
import cv2
import uuid
import shutil
import subprocess
import xml.etree.ElementTree as ET
import PyPDF2
from wand.color import Color
from wand.image import Image as Img
from wand.api import library


class Separator:
    def __init__(self, log, config, tmp_folder):
        self.Log = log
        self.Config = config
        self.pages = []
        self.nb_doc = 0
        self.nb_pages = 0
        self.error = False
        self.qrList = None
        self.enabled = False
        self.divider = config.cfg['SEPARATOR_QR']['divider']
        self.convert_to_pdfa = config.cfg['SEPARATOR_QR']['exportpdfa']
        tmp_folder_name = os.path.basename(os.path.normpath(tmp_folder))
        self.tmp_dir = config.cfg['SEPARATOR_QR']['tmppath'] + '/' + tmp_folder_name + '/'
        self.output_dir = config.cfg['SEPARATOR_QR']['outputpdfpath'] + '/' + tmp_folder_name + '/'
        self.output_dir_pdfa = config.cfg['SEPARATOR_QR']['outputpdfapath'] + '/' + tmp_folder_name + '/'

        os.mkdir(self.output_dir)
        os.mkdir(self.output_dir_pdfa)

    @staticmethod
    def is_blank_page(image, config):
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
        self.Log.info('Start page separation using QR CODE')
        self.pages = []
        try:
            if self.Config.cfg['SEPARATOR_QR']['removeblankpage'] == 'True':
                self.remove_blank_page(file)
            pdf = PyPDF2.PdfFileReader(open(file, 'rb'))
            self.nb_pages = pdf.getNumPages()
            self.get_xml_qr_code(file)
            self.parse_xml()
            self.check_empty_docs()
            self.set_doc_ends()
            self.extract_and_convert_docs(file)
        except Exception as e:
            self.error = True
            self.Log.error("INIT : " + str(e))

    def remove_blank_page(self, file):
        with Img(filename=file, resolution=300) as pic:
            library.MagickResetIterator(pic.wand)
            pic.scene = 1  # Start cpt of filename at 1 instead of 0
            pic.compression_quality = 100
            pic.background_color = Color("white")
            pic.alpha_channel = 'remove'
            pic.save(filename=(self.output_dir + '/result.jpg'))

        blank_page_exists = False
        pages_to_keep = []
        for _file in os.listdir(self.output_dir):
            if _file.endswith('.jpg'):
                if not self.is_blank_page(self.output_dir + '/' + _file, self.Config.cfg):
                    blank_page_exists = True
                    pages_to_keep.append(os.path.splitext(_file)[0].split('-')[1])
                try:
                    os.remove(self.output_dir + '/' + _file)
                except FileNotFoundError:
                    pass

        if blank_page_exists:
            infile = PyPDF2.PdfFileReader(file)
            output = PyPDF2.PdfFileWriter()
            for i in sorted(pages_to_keep):
                p = infile.getPage(int(i) - 1)
                output.addPage(p)

            with open(file, 'wb') as f:
                output.write(f)

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

            if err.decode('utf-8'):
                self.Log.error('ZBARIMG : ' + str(err))
            self.qrList = ET.fromstring(out)
        except subprocess.CalledProcessError as cpe:
            if cpe.returncode != 4:
                self.Log.error("ZBARIMG : \nreturn code: %s\ncmd: %s\noutput: %s\nglobal : %s" % (cpe.returncode, cpe.cmd, cpe.output, cpe))

    def parse_xml(self):
        """
        Parse XML content of QR Code to retrieve the destination of the document (in Maarc)

        """
        if self.qrList is None:
            return
        ns = {'bc': 'http://zbar.sourceforge.net/2008/barcode'}
        indexes = self.qrList[0].findall('bc:index', ns)
        for index in indexes:
            page = {}
            data = index.find('bc:symbol', ns).find('bc:data', ns)
            page['service'] = data.text
            page['index_sep'] = int(index.attrib['num'])

            if page['index_sep'] + 1 >= self.nb_pages:  # If last page is a separator
                page['is_empty'] = True
            else:
                page['is_empty'] = False
                page['index_start'] = page['index_sep'] + 2

            page['uuid'] = str(uuid.uuid4())    # Generate random number for pdf filename
            page['pdf_filename'] = self.output_dir + page['service'] + self.divider + page['uuid'] + '.pdf'
            page['pdfa_filename'] = self.output_dir_pdfa + page['service'] + self.divider + page['uuid'] + '.pdf'
            self.pages.append(page)
        self.nb_doc = len(self.pages)

    def check_empty_docs(self):
        """
        Check if a document is empty

        """
        for i in range(self.nb_doc - 1):
            if self.pages[i]['index_sep'] + 1 == self.pages[i + 1]['index_sep']:
                self.pages[i]['is_empty'] = True

    def set_doc_ends(self):
        """
        Set a virtual limit to split document later

        """
        for i in range(self.nb_doc):
            if self.pages[i]['is_empty']:
                continue
            if i + 1 < self.nb_doc:
                self.pages[i]['index_end'] = self.pages[i + 1]['index_sep']
            else:
                self.pages[i]['index_end'] = self.nb_pages

    def extract_and_convert_docs(self, file):
        """
        If empty doc, move it directly
        Else, split document and export them

        :param file:
        """
        if len(self.pages) == 0:
            try:
                shutil.move(file, self.output_dir)
            except shutil.Error as e:
                self.Log.error('Moving file ' + file + ' error : ' + str(e))
            return
        else:
            try:
                for page in self.pages:
                    if page['is_empty']:
                        continue

                    pages_to_keep = range(page['index_start'], page['index_end'] + 1)
                    split_pdf(file, page['pdf_filename'], pages_to_keep)
                    if self.convert_to_pdfa == 'True':
                        self.convert_to_pdfa(page['pdfa_filename'], page['pdf_filename'])
                os.remove(file)
            except Exception as e:
                self.Log.error("EACD: " + str(e))


def split_pdf(input_path, output_path, pages):
    """
    Finally, split PDF into multiple PDF

    :param input_path: Orignal PDF (including separator with QR Code)
    :param output_path: Final PDF, splitted
    :param pages: Pages which compose the new PDF
    """
    input_pdf = PyPDF2.PdfFileReader(open(input_path, "rb"))
    output_pdf = PyPDF2.PdfFileWriter()

    for page in pages:
        output_pdf.addPage(input_pdf.getPage(page - 1))

    with open(output_path, "wb") as stream:
        output_pdf.write(stream)


def convert_to_pdfa(pdfa_filename, pdf_filename):
    """
    Convert a simple PDF to a PDF/A

    :param pdfa_filename: New PDF/A filename
    :param pdf_filename: Old PDF filename
    """
    gs_command_line = 'gs#-dPDFA#-dNOOUTERSAVE#-sProcessColorModel=DeviceCMYK#-sDEVICE=pdfwrite#-o#%s#-dPDFACompatibilityPolicy=1#PDFA_def.ps#%s' % (pdfa_filename, pdf_filename)
    gs_args = gs_command_line.split('#')
    subprocess.check_call(gs_args)
    os.remove(pdf_filename)
