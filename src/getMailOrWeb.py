# import the necessary packages
import argparse
import sys
import os
import re
from datetime import datetime
import classes.Log as logClass
import classes.PyOCR as ocrClass
import classes.Database as dbClass
import classes.Locale as localeClass
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
    Log         = logClass.Log(Config.cfg['GLOBAL']['logfile'])
    WebService  = webserviceClass.WebServices(
        Config.cfg['WS']['host'],
        Config.cfg['WS']['user'],
        Config.cfg['WS']['password'],
        Log
    )
    Database    = dbClass.Database(Config.cfg['SQLITE']['path'])
    fileName    = Config.cfg['GLOBAL']['tmpfilename']
    Image       = imagesClass.Images(
        fileName,
        int(Config.cfg['GLOBAL']['resolution']),
        int(Config.cfg['GLOBAL']['compressionquality'])
    )
    Locale      = localeClass.Locale(Config)
    Ocr         = ocrClass.PyOCR(Locale.localeOCR)

    # Start process
    for file in os.listdir(args['pdf']):
        Log.info('Processing file : ' + args['pdf'] + file)
        # Open the pdf and convert it to JPG
        # Then resize the picture
        Image.pdf_to_jpg_without_resize(args['pdf'] + file + '[0]')

        Ocr.text_builder(Image.img)

        # Find subject of document
        subject = None
        for findSubject in re.finditer(r"[o,O]bje[c]?t\s*(:)?\s*.*", Ocr.text):
            subject = re.sub(r"[o,O]bje[c]?t\s*(:)?\s*", '', findSubject.group())
            break

        # Find date of document
        foundDate   = False
        date        = ''
        print(file)
        for findDate in re.finditer(r"" + Locale.regexDate + "", Ocr.text):
            date        = findDate.group().replace('1er', '01') # Replace some possible inconvenient char
            dateConvert = Locale.arrayDate
            for key in dateConvert:
                for month in dateConvert[key]:
                    if month.lower() in date:
                        date = (date.lower().replace(month.lower(), key))
                        break

            try:
                date = datetime.strptime(date, '%d %m %Y')
            except ValueError as e:
                print(e)
            foundDate = True


        # Find mail in document and check if the contact exist in Maarch
        foundContact    = False
        for mail in re.finditer(r"[^@\s]+@[^@\s]+\.[^@\s]+", Ocr.text):
            Log.info('Find E-MAIL : ' + mail.group())
            contact = WebService.retrieve_contact_by_mail(mail.group())
            if contact:
                foundContact = True
                break

        # If not contact were found, search for URL
        if not foundContact:
            for url in re.finditer(r"((http|https)://)?(www\.)?[a-zA-Z0-9+_.\-]+\.(" + Config.cfg['REGEX']['urlpattern'] + ")", Ocr.text):
                Log.info('Find URL : ' + url.group())
                contact = WebService.retrieve_contact_by_url(url.group())
                if contact:
                    foundContact = True
                    break

        res = WebService.insert_with_args(args['pdf'] + file, Config, contact, subject, date)
        if res:
            Log.info("Insert OK : " + res)

