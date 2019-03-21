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
import classes.Separator as separatorClass
import classes.WebServices as webserviceClass


if __name__ == '__main__':
    # construct the argument parse and parse the arguments
    ap      = argparse.ArgumentParser()
    ap.add_argument("-p", "--path", required=False, help="path to folder containing documents")
    ap.add_argument("-f", "--file", required=False, help="path to folder containing documents")
    ap.add_argument("-c", "--config", required=True, help="path to config.xml")
    args    = vars(ap.parse_args())

    if args['path'] is None and args['file'] is None:
        sys.exit('No file or path were given')
    elif args['path'] is not None and args['file'] is not None:
        sys.exit('Chose between path or file')

    # Init all the necessary classes
    Config      = configClass.Config(args['config'])
    Log         = logClass.Log(Config.cfg['GLOBAL']['logfile'])
    WebService  = webserviceClass.WebServices(
        Config.cfg['OCForMaarch']['host'],
        Config.cfg['OCForMaarch']['user'],
        Config.cfg['OCForMaarch']['password'],
        Log
    )
    Database    = dbClass.Database(Config.cfg['REFERENTIALS']['zipcode'])
    fileName    = Config.cfg['GLOBAL']['tmpfilename']
    Image       = imagesClass.Images(
        fileName,
        int(Config.cfg['GLOBAL']['resolution']),
        int(Config.cfg['GLOBAL']['compressionquality'])
    )
    Locale      = localeClass.Locale(Config)
    Ocr         = ocrClass.PyOCR(Locale.localeOCR)
    Separator   = separatorClass.Separator(Log, Config)

    # Start process
    if args['path'] is not None:
        for file in os.listdir(args['path']):
            print(file)
            Log.info('Processing file : ' + args['path'] + file)
            if os.path.splitext(file)[1] == '.pdf': # Open the pdf and convert it to JPG
                Image.pdf_to_jpg_without_resize(args['path'] + file + '[0]')

                # Check if pdf is already OCR and searchable
                checkOcr = os.popen('pdffonts ../data/tmp/RH_CV_Benoit_Favier.pdf', 'r')
                tmp     = ''
                isOcr   = True
                for line in checkOcr:
                    tmp += line

                if len(tmp.split('\n')) > 2 :
                    isOcr = True
            else: # Open the picture
                Image.open_img(args['path'] + file)
                isOcr = False

            # Get the OCR of the file as a string content
            Ocr.text_builder(Image.img)
            # Create the searchable PDF
            if isOcr is False:
                Ocr.generate_searchable_pdf(Image.img)

            # Find subject of document
            subject = None
            for findSubject in re.finditer(r"[o,O]bje[c]?t\s*(:)?\s*.*", Ocr.text):
                subject = re.sub(r"[o,O]bje[c]?t\s*(:)?\s*", '', findSubject.group())
                break

            # Find date of document
            date        = ''
            for findDate in re.finditer(r"" + Locale.regexDate + "", Ocr.text):
                date        = findDate.group().replace('1er', '01') # Replace some possible inconvenient char
                dateConvert = Locale.arrayDate
                for key in dateConvert:
                    for month in dateConvert[key]:
                        if month.lower() in date:
                            date = (date.lower().replace(month.lower(), key))
                            break
                try:
                    date = datetime.strptime(date, Locale.dateTimeFomat).strftime(Locale.formatDate)
                    break
                except ValueError as e:
                    print (e)
            print(date)

            # Find mail in document and check if the contact exist in Maarch
            foundContact    = False
            contact         = ''
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

            res = WebService.insert_with_args(Ocr.searchablePdf, Config, contact, subject, date)
            if res:
                Log.info("Insert OK : " + res)

    elif args['file'] is not None:
        if Config.cfg['SEPARATOR_QR']['enabled'] == 'True':
            Separator.process(args['file'])



