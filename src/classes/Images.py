from wand.image import Image as Img
from PyPDF2 import PdfFileMerger
from PIL import Image
import cv2
import os

class Images:
    def __init__(self, jpgName, res, quality):
        self.jpgName                = jpgName
        self.resolution             = res
        self.compressionQuality     = quality
        self.img                    = None

    def pdf_to_jpg(self, pdfName):
        with Img(filename=pdfName, resolution=self.resolution) as pic:
            pic.compression_quality = self.compressionQuality
            pic.save(filename=self.jpgName)
        self.resize()

    def pdf_to_jpg_without_resize(self, pdfName):
        with Img(filename=pdfName, resolution=self.resolution) as pic:
            pic.compression_quality = self.compressionQuality
            pic.save(filename=self.jpgName)
        self.img = Image.open(self.jpgName)

    def open_img_with_PIL(self, img):
        self.img = Image.open(img)

    def open_img_with_wand(self, pdfName, output):
        with Img(filename=pdfName, resolution=self.resolution) as pic:
            pic.compression_quality = self.compressionQuality
            pic.save(filename=output)

    def resize(self):
        # Open the picture to resize it and save it as is
        img = cv2.imread(self.jpgName)
        height, width, channels = img.shape  # Use the height and width to crop the wanted zone

        # Vars used to select the zone we want to analyze (top of the document by default)
        x = 0
        y = 0
        w = width
        h = int(height * 0.35)
        crop_image = img[y:y + h, x:x + w]
        cv2.imwrite(self.jpgName, crop_image)

        # Read the image before we get the text content
        self.img = Image.open(self.jpgName)

    @staticmethod
    def sorted_file(path, extension):
        file_json = []
        for file in os.listdir(path):
            if file.endswith("." + extension):
                filename    = os.path.splitext(file)[0]
                cpt         = filename.split('-')[1]
                if len(cpt) == 1:
                    tmpCpt = '0' + str(cpt)
                    cpt = tmpCpt
                file_json.append((cpt, path + file))
        sorted_file = sorted(file_json, key=lambda fileCPT: fileCPT[0])
        return sorted_file

    @staticmethod
    def merge_pdf(fileSorted, tmpPath):
        merger = PdfFileMerger()
        for pdf in fileSorted:
            merger.append(pdf[1])
        merger.write('/tmp/' + 'result.pdf')

        return open('/tmp/' + 'result.pdf', 'rb').read()