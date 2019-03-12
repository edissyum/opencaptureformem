# import the necessary packages
import argparse
import sys
import os
import re
import classes.db as dbClass
import classes.pyOCR as ocrClass
import classes.images as imagesClass

####### Functions definitions

def getNearWords(arrayOfLine, zipCode, rangeX=20, rangeY=15, maxRangeX=200, maxRangeY=350):
    nearWord    = {}
    currentyTL  = zipCode['yTL']
    currentxTL  = zipCode['xTL']
    nearWord[currentyTL] = []
    for line in arrayOfLine:
        # Check words on the same column and keep the coordonnates to check the word in the same line
        if abs(line['xTL'] - zipCode['xTL']) <=  rangeX and abs(line['yTL'] - zipCode['yTL']) <= maxRangeY and line['content'] != ' ' :
            print ('ok' + str(line))
            currentyTL              = line['yTL']
            currentxTL              = line['xTL']
            nearWord[currentyTL]    = []
            for line2 in arrayOfLine:
                # Check the words on the same line
                if abs(line2['yTL'] - currentyTL) <= rangeY and abs(line2['xTL'] - currentxTL) <= maxRangeX and line2['content'] != ' ':
                    nearWord[currentyTL].append({
                        'xTL'       : line2['xTL'],
                        'yTL'       : line2['yTL'],
                        'xBR'       : line2['xBR'],
                        'yBR'       : line2['yBR'],
                        'content'   : line2['content']
                    })
                    currentxTL = line2['xTL']

    contactText = ''
    for pos in sorted(nearWord):
        for word in nearWord[pos]:
            contactText += str(word['content']) + ' '
        contactText += '\n'

    return contactText

def checkZipCode(zipCode):
    # Check on full zipCode
    if Database.select('zipCode', 'zip = ' + zipCode) is not None:
        return True
    else:
        # Check if the 3 first digit could be a zipcode. If True, search on cedex database
        if Database.select('zipCode', "zip like '" + zipCode[0:3] + "%'") is not None:
            if Database.select('cedex', "zip = " + zipCode) is not None:
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
    args                = vars(ap.parse_args())
    Database            = dbClass.Database('db/zipcode.db')
    Ocr                 = ocrClass.PyOCR()
    fileName            = "images/tmp.jpg"
    resolution          = 300
    compressionQuality  = 100
    Image = imagesClass.Images(fileName, resolution, compressionQuality)

    for file in os.listdir(args['pdf']):
        print(file)
        # Open the pdf and convert it to JPG
        # Then resize the picture
        Image.pdf_to_jpg(args['pdf'] + file + '[0]')

        # Get all the content we just ocr'ed
        Ocr.line_and_word_boxes(Image.img)

        # xTL stands for x Top Left (the position of X on the top left of the word)
        # yTL stands for y Top Left
        # xBR stands for x Bottom Right (the position of X on the bottom right of the word)
        # yBR stands for y Bottom Right
        arrayOfLine = []
        arrayOfZipCode = []
        for box in Ocr.text: # Loop over all the lines of the document
            arrayOfLine.append({
                'xTL'       : box.position[0][0],
                'yTL'       : box.position[0][1],
                'xBR'       : box.position[1][0],
                'yBR'       : box.position[1][1],
                'content'   : box.content
            })
            findZipCode = re.match(r"^\d{5}$", box.content)
            if findZipCode is not None and checkZipCode(findZipCode[0]): # Search for zip code (regex on 5 digits) and check in BAN database
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
            print (res + '\n')
            '''with open(args['pdf'] + file + '.txt', 'a') as the_file:
                the_file.write(res)'''

        #os.remove(fileName)
    sys.exit()

    '''cv2.imshow('img', crop_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()'''
