# import the necessary packages
import argparse
import sys
import os
import re
import classes.Database as dbClass
import classes.PyOCR as ocrClass
import classes.Images as imagesClass


if __name__ == '__main__':
    # construct the argument parse and parse the arguments
    ap      = argparse.ArgumentParser()
    ap.add_argument("-p", "--pdf", required=True, help="path to folder containing pdf")
    args    = vars(ap.parse_args())

    # Init all the necessary classes
    Database            = dbClass.Database('db/zipcode.db')
    Ocr                 = ocrClass.PyOCR()
    fileName            = "/tmp/tmp.jpg"
    resolution          = 300
    compressionQuality  = 100
    Image               = imagesClass.Images(fileName, resolution, compressionQuality)

    # Start process
    for file in os.listdir(args['pdf']):
        # Open the pdf and convert it to JPG
        # Then resize the picture
        Image.pdf_to_jpg(args['pdf'] + file + '[0]')

        # Get all the content we just ocr'ed
        Ocr.word_box_builder(Image.img)

            #print(Ocr.text.find())
        for box in Ocr.text:
            if re.match(r"[^@]+@[^@]+\.[^@]+", box.content):
                mail = box.content
                print(mail)
