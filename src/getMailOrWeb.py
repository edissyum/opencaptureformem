# import the necessary packages
import argparse
import sys
import os
import re
import classes.Database as dbClass
import classes.PyOCR as ocrClass
import classes.Images as imagesClass
import classes.Config as configClass
import classes.WebServices as webserviceClass

if __name__ == '__main__':
    # construct the argument parse and parse the arguments
    ap      = argparse.ArgumentParser()
    ap.add_argument("-p", "--pdf", required=True, help="path to folder containing pdf")
    ap.add_argument("-c", "--config", required=True, help="path to config.xml")
    args    = vars(ap.parse_args())

    # Init all the necessary classes
    Config      = configClass.Config(args['config'])
    WebService  = webserviceClass.WebServices(
        Config.cfg['WS']['host'],
        Config.cfg['WS']['user'],
        Config.cfg['WS']['password']
    )
    Database    = dbClass.Database(Config.cfg['SQLITE']['path'])
    Ocr         = ocrClass.PyOCR()
    fileName    = Config.cfg['GLOBAL']['tmpfilename']
    Image       = imagesClass.Images(
        fileName,
        int(Config.cfg['GLOBAL']['resolution']),
        int(Config.cfg['GLOBAL']['compressionquality'])
    )

    # Start process
    for file in os.listdir(args['pdf']):
        print(file)
        # Open the pdf and convert it to JPG
        # Then resize the picture
        Image.pdf_to_jpg(args['pdf'] + file + '[0]')

        # Get all the content we just ocr'ed
        Ocr.word_box_builder(Image.img)

        for box in Ocr.text:
            if re.match(r"[^@]+@[^@]+\.[^@]+", box.content):
                mail = box.content.lower()
                contact = WebService.retrieve_contact_by_mail(mail)
                if contact:
                    res = WebService.insert_with_contact_info(args['pdf'] + file, Config, contact)
                    if res:
                        print ('Insert OK : ' + res)
                        break
                    else:
                        print ('Insert error : ' + res)
            elif re.match(r"((http|https)://)?(www\.)?[a-zA-Z0-9+_.\-]+\.(" + Config.cfg['REGEX']['urlpattern'] + ")$", box.content):
                url = box.content.lower()
                contact = WebService.retrieve_contact_by_url('http://www.maarch.com')
                if contact:
                    res = WebService.insert_with_contact_info(args['pdf'] + file, Config, contact)
                    if res:
                        print ('Insert OK : ' + res)
                        break
                    else:
                        print ('Insert error : ' + res)

