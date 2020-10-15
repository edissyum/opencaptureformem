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

import os
import shutil
import sys

from .FindDate import FindDate
from .FindSubject import FindSubject
from .FindContact import FindContact


def get_process_name(args, config):
    if args.get('isMail') is not None and args.get('isMail') is True:
        _process = args['process']
    else:
        if args['process'] in config.cfg['OCForMaarch']['processavailable'].split(','):
            _process = 'OCForMaarch_' + args['process'].lower()
        else:
            _process = 'OCForMaarch_' + config.cfg['OCForMaarch']['defaultprocess'].lower()

    return _process


def process(args, file, log, separator, config, image, ocr, locale, web_service, tmp_folder, q=None):
    log.info('Processing file : ' + file)

    # Check if the choosen process mode if available. If not take the default one
    _process = args['process_name']
    log.info('Using the following process : ' + _process)

    destination = ''

    # Check if RDFF is enabled, if yes : retrieve the service ID from the filename
    if args.get('RDFF') not in [None, False]:
        log.info('RDFF is enabled')
        file_name = os.path.basename(file)
        if separator.divider not in file_name:
            destination = config.cfg[_process]['destination']
        else:
            destination = file_name.split(separator.divider)[0]

    # Or from the destination arguments
    elif args.get('destination') is not None:
        destination = args['destination']
    elif args.get('isMail') is not None and args.get('isMail') is True:
        destination = args['data']['destination']

    if not destination:
        # Put default destination
        destination = config.cfg[_process]['destination']
        log.info("Destination can't be found, using default destination : " + destination)

    # Retrieve destination ID from Maarch 20 if destination is not an integer
    if type(destination) is not int:
        destinations = web_service.retrieve_entities()
        for dest in destinations['entities']:
            if destination == dest['id']:
                destination = dest['serialId']
                if args.get('isMail') is not None and args.get('isMail') is True:
                    args['data']['destination'] = destination

    # If destination still not good, try with default destination
    if type(destination) is not int:
        if args.get('isMail') is not None and args.get('isMail') is True:
            destination = args['data']['destination']
        else:
            destination = config.cfg[_process]['destination']
        destinations = web_service.retrieve_entities()
        for dest in destinations['entities']:
            if destination == dest['id']:
                destination = dest['serialId']
                if args.get('isMail') is not None and args.get('isMail') is True:
                    args['data']['destination'] = destination

    # Retrieve user_id to use it as typist
    if args.get('isMail') is not None and args.get('isMail') is True:
        typist = args['data']['typist']
    else:
        typist = config.cfg[_process]['typist']

    if type(typist) is not int:
        list_of_users = web_service.retrieve_users()
        for user in list_of_users['users']:
            if typist == user['user_id']:
                typist = user['id']
                if args.get('isMail') is not None and args.get('isMail') is True:
                    args['data']['typist'] = typist
                else:
                    config.cfg[_process]['typist'] = typist

    if os.path.splitext(file)[1].lower() == '.pdf':  # Open the pdf and convert it to JPG
        res = image.pdf_to_jpg(file + '[0]', True)
        if res is False:
            exit(os.EX_IOERR)
        # Check if pdf is already OCR and searchable
        check_ocr = os.popen('pdffonts ' + file, 'r')
        tmp = ''
        for line in check_ocr:
            tmp += line

        if len(tmp.split('\n')) > 3:
            is_ocr = True
        else:
            is_ocr = False
    elif os.path.splitext(file)[1].lower() == '.html':
        res = image.html_to_txt(file)
        if res is False:
            sys.exit(os.EX_IOERR)

        ocr.text = res
        is_ocr = True
    elif os.path.splitext(file)[1].lower() == '.txt':
        ocr.text = open(file, 'r').read()
        is_ocr = True
    else:  # Open the picture
        image.open_img(file)
        is_ocr = False

    if 'reconciliation' not in _process:
        # Get the OCR of the file as a string content
        if args.get('isMail') is None or args.get('isMail') is False and os.path.splitext(file)[1].lower() not in ('.html', '.txt'):
            ocr.text_builder(image.img)

        # Find subject of document
        if args.get('isMail') is not None and args.get('isMail') is True and args.get('priority_mail_subject') is True:
            subject_thread = ''
            pass
        else:
            subject_thread = FindSubject(ocr.text, locale, log)
        # Find date of document
        date_thread = FindDate(ocr.text, locale, log, config)
        # Find mail in document and check if the contact exist in Maarch
        contact_thread = FindContact(ocr.text, log, config, web_service, locale)
        # Launch all threads
        date_thread.start()
        if args.get('isMail') is not None and args.get('isMail') is True and args.get('priority_mail_subject') is True:
            pass
        else:
            subject_thread.start()
        contact_thread.start()

        # Wait for end of threads
        date_thread.join()
        if args.get('isMail') is not None and args.get('isMail') is True and args.get('priority_mail_subject') is True:
            pass
        else:
            subject_thread.join()
        contact_thread.join()

        # Get the returned values
        date = date_thread.date
        if args.get('isMail') is not None and args.get('isMail') is True and args.get('priority_mail_subject') is True:
            subject = ''
        else:
            subject = subject_thread.subject
        contact = contact_thread.contact
        custom_mail = contact_thread.custom_mail
    else:
        date = ''
        subject = ''
        contact = {}
        custom_mail = ''

    try:
        os.remove(image.jpgName)  # Delete the temp file used to OCR'ed the first PDF page
    except FileNotFoundError:
        pass

    # Create the searchable PDF if necessary
    if is_ocr is False:
        log.info('Start OCR on document before send it')
        ocr.generate_searchable_pdf(file, tmp_folder)
        file_to_send = ocr.searchablePdf
    else:
        file_to_send = open(file, 'rb').read()

    if q is not None:
        file_to_store = {
            'fileToSend': file_to_send,
            'file': file,
            'date': date,
            'subject': subject,
            'contact': contact,
            'destination': destination,
            'process': _process,
            'resId': args['resid'],
            'chrono': args['chrono'],
            'isInternalNote': args['isinternalnote'],
            'custom_mail': custom_mail,
        }

        q.put(file_to_store)

        return q
    else:
        if args.get('isMail') is not None and args.get('isMail') is True:
            if date != '':
                args['data']['documentDate'] = date
            if subject != '':
                args['data']['subject'] = subject
            if contact != '':
                args['data']['senders'] = [{'id': contact['id'], 'type': 'contact'}]
            else:
                # Search a contact id from Maarch database
                log.info('No contact found on mail body, try with "from" of the mail :  ' + args['data']['from'])
                contact = web_service.retrieve_contact_by_mail(args['data']['from'])
                if contact:
                    args['data']['senders'] = [{'id': contact['id'], 'type': 'contact'}]

            res = web_service.insert_letterbox_from_mail(args['data'])
            if res:
                log.info('Insert email OK : ' + str(res))
                return res
            else:
                try:
                    shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
                except shutil.Error as e:
                    log.error('Moving file ' + file + ' error : ' + str(e))
                return False, res

        elif 'is_attachment' in config.cfg[_process] and config.cfg[_process]['is_attachment'] != '':
            if args['isinternalnote']:
                res = web_service.insert_attachment(file_to_send, config, args['resid'], _process)
            else:
                res = web_service.insert_attachment_reconciliation(file_to_send, args['chrono'], _process, config)
        else:
            res = web_service.insert_with_args(file_to_send, config, contact, subject, date, destination, config.cfg[_process], custom_mail)

        if res:
            log.info("Insert OK : " + res)
            if args.get('isMail') is None:
                try:
                    os.remove(file)
                except FileNotFoundError as e:
                    log.error('Unable to delete ' + file + ' after insertion : ' + str(e))
            return True
        else:
            try:
                shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
            except shutil.Error as e:
                log.error('Moving file ' + file + ' error : ' + str(e))
            return False
