# import the necessary packages
from PIL import Image
import pyocr
import pyocr.builders
import pytesseract
import argparse
import numpy as np
import cv2
import imutils
import sys
import os
from wand.image import Image as Img
import re
import db

####### Init PYOCR

tools = pyocr.get_available_tools()
if len(tools) == 0:
    print("No OCR tool found")
    sys.exit(1)
tool = tools[0]
print("Will use tool '%s'" % (tool.get_name()))
# Ex: Will use tool 'libtesseract'

langs = tool.get_available_languages()
print("Available languages: %s" % ", ".join(langs))
lang = langs[2]
print("Will use lang '%s'" % lang)

####### END INIT

####### Functions definitions

def getNearWords(arrayOfLine, zipCode, rangeX=10, rangeY=5, maxRangeX=200, maxRangeY=350):
    nearWord    = {}
    currentyTL  = zipCode['yTL']
    currentxTL  = zipCode['xTL']
    nearWord[currentyTL] = []
    for line in arrayOfLine:
        # Check words on the same column and keep the coordonnates to check the word in the same line
        if abs(line['xTL'] - zipCode['xTL']) < rangeX and abs(line['yTL'] - zipCode['yTL']) < maxRangeY and line['content'] != ' ' :
            currentyTL              = line['yTL']
            currentxTL              = line['xTL']
            nearWord[currentyTL]    = []

        # Check the words on the same line
        if abs(line['yTL'] - currentyTL) < rangeY and abs(line['xTL'] - currentxTL) < maxRangeX and line['content'] != ' ':
            nearWord[currentyTL].append({
                'xTL'       : line['xTL'],
                'yTL'       : line['yTL'],
                'xBR'       : line['xBR'],
                'yBR'       : line['yBR'],
                'content'   : line['content']
            })
            currentxTL = line['xTL']

    contactText = ''
    for pos in sorted(nearWord):
        for word in nearWord[pos]:
            contactText += str(word['content']) + ' '
        contactText += '\n'

    return contactText

def checkZipCode(conn, zipCode):
    # Check on full zipCode
    if db.select(conn, 'zipCode', 'zip =' + zipCode) is not None:
        return True
    else:
        # Check if the 3 first digit could be a zipcode. If True, search on cedex database
        if db.select(conn, 'zipCode', "zip like '" + zipCode[0:3] + "%'") is not None:
            if db.select(conn, 'cedex', "zip = " + zipCode) is not None:
                return True
            else :
                return False
        else:
            return False

####### END functions definitions

if __name__ == '__main__':
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--pdf", required=True,
                    help="path to folder containing pdf")
    args = vars(ap.parse_args())
    conn = db.connect()
    fileName = "images/tmp.jpg"

    for file in os.listdir(args['pdf']):
        # Open the pdf and convert it to JPG
        with Img(filename=args['pdf'] + file + '[0]', resolution=300) as pic:
            pic.compression_quality = 100
            pic.save(filename=fileName)

        # Open the picture to resize it and save it as is
        img = cv2.imread(fileName)
        height, width, channels = img.shape # Use the height and width to crop the wanted zone

        # Vars used to select the zone we want to analyze (top of the document by default)
        x = 0
        y = 0
        w = width
        h = int(height * 0.30)
        crop_image = img[y:y+h, x:x+w]
        cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0)) # Display on the image the zone we capture (cv2.imshow("Output", gray); cv2.waitKey(0) pour afficher l'image lors de l'exec du script)
        cv2.imwrite(fileName, crop_image)

        # Read the image and create boxes of content
        img = Image.open(fileName)

        line_and_word_boxes = tool.image_to_string(
            img,
            lang="fra",
            builder=pyocr.builders.WordBoxBuilder()
        )

        # xTL stands for x Top Left (the position of X on the top left of the word)
        # yTL stands for y Top Left
        # xBR stands for x Bottom Right (the position of X on the bottom right of the word)
        # yBR stands for y Bottom Right
        arrayOfLine = []
        arrayOfZipCode = []
        for box in line_and_word_boxes: # Loop over all the lines of the document
            arrayOfLine.append({
                'xTL'       : box.position[0][0],
                'yTL'       : box.position[0][1],
                'xBR'       : box.position[1][0],
                'yBR'       : box.position[1][1],
                'content'   : box.content
            })
            findZipCode = re.match(r"^\d{5}$", box.content)
            if findZipCode is not None and checkZipCode(conn, findZipCode[0]): # Search for zip code (regex on 5 digits) and check in BAN database
                arrayOfZipCode.append({
                    'xTL'       : box.position[0][0],
                    'yTL'       : box.position[0][1],
                    'xBR'       : box.position[1][0],
                    'yBR'       : box.position[1][1],
                    'content'   : box.content
                })

        # Find other word related to the adress, based on the zip code and the position of the zip code block
        for zipCode in arrayOfZipCode:
            res = getNearWords(arrayOfLine, zipCode)
            with open(args['pdf'] + file + '.txt', 'a') as the_file:
                the_file.write(res)

    sys.exit()

    '''cv2.imshow('img', crop_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()'''
