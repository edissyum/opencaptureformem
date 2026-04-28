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
# @dev: Serena tetart <serena.tetart@edissyum.com>

import os
import re
import sys
import torch
import pickle
import shutil
import warnings
import requests
import subprocess
import transformers


from rapidfuzz import fuzz

from .FindDate import FindDate
from pyzbar.pyzbar import decode
from .FindChrono import FindChrono
from .FindSubject import FindSubject
from .OCForForms import process_form
from pdf2image import convert_from_path
from .FindContact import FindContact, run_inference_sender, run_inference_sender_remote
from .FindDestination import run_inference_destination, run_inference_destination_remote

def get_process_name(args, config):
    if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        _process = args['process']
    else:
        if args['process'] in config.cfg['OCForMEM']['process_available'].split(','):
            _process = 'OCForMEM_' + args['process'].lower()
        else:
            _process = 'OCForMEM_' + config.cfg['OCForMEM']['default_process'].lower()

    return _process


def compress_pdf(args, config, process, file, log):
    if not args.get('isMail') and os.path.splitext(file)[1].lower() not in ('.html', '.txt'):
        config = config[process]
        if 'compress_type' in config and config['compress_type'] and config['compress_type'].lower() != 'none':
            log.info('Compress PDF : ' + config['compress_type'])
            compressed_file_path = '/tmp/min_' + os.path.basename(file)

            # None, default (very low), printer (low), prepress (medium), ebook (high), screen (very high)
            gs_command = (f"gs#-sDEVICE=pdfwrite#-dCompatibilityLevel=1.4#-dPDFSETTINGS=/{config['compress_type']}"
                          f"#-dNOPAUSE#-dQUIET#-o#{compressed_file_path}#{file}")
            gs_args = gs_command.split('#')
            subprocess.check_call(gs_args)

            try:
                shutil.move(compressed_file_path, file)
            except (shutil.Error, FileNotFoundError) as _e:
                log.error('Moving file ' + compressed_file_path + ' error : ' + str(_e))


def check_destination(destinations, destination):
    if isinstance(destination, int) or destination.isnumeric():
        for dest in destinations['entities']:
            if int(destination) == int(dest['serialId']):
                return destination
            if (isinstance(dest['id'], int) or dest['id'].isnumeric()) and int(destination) == int(dest['id']):
                return dest['serialId']
    else:
        for dest in destinations['entities']:
            if str(destination).lower() == str(dest['id']).lower():
                destination = dest['serialId']
                return destination
    return False


def check_doctype(doctypes, doctype, log=None):
    if doctype in [None, '']:
        return False

    doctype_str = str(doctype).strip()
    if not doctype_str:
        return False

    candidates = []

    for doct in doctypes.get('structure', []):
        if 'type_id' not in doct or doct['type_id'] in [None, '']:
            continue

        type_id = str(doct['type_id']).strip()

        if doctype_str.isnumeric():
            if int(doctype_str) == int(type_id):
                return type_id

        for key in ('description', 'label', 'type_label', 'doctype'):
            if key not in doct or doct[key] in [None, '']:
                continue

            db_label = str(doct[key]).strip()

            if doctype_str.lower() == db_label.lower():
                return type_id

            score = fuzz.ratio(doctype_str.lower(), db_label.lower())
            candidates.append((score, type_id, db_label))

    if candidates:
        best_score, best_type_id, best_label = max(candidates, key=lambda x: x[0])
        if best_score >= 80:
            if log:
                log.info(
                    f'Doctype fuzzy matched: "{doctype_str}" -> "{best_label}" '
                    f'(score={best_score:.2f}, type_id={best_type_id})'
                )
            return best_type_id

    return False


def process(args, file, log, separator, config, image, ocr, locale, web_service, tmp_folder, config_mail=None):
    log.info('Processing file : ' + file)

    # Check if the choosen process mode if available. If not take the default one
    _process = args['process_name']
    log.info('Using the following process : ' + _process)

    destination = ''
    search_ai_destination = False

    # Check if RDFF is enabled, if yes : retrieve the service ID from the filename
    if args.get('RDFF') not in [None, False]:
        log.info('RDFF is enabled')
        file_name = os.path.basename(file)
        file_name = re.sub('^MEM_', '', file_name)
        file_name = re.sub('^MAARCH_', '', file_name)

        if separator.divider not in file_name:
            destination = config.cfg[_process]['destination']
            search_ai_destination = True
        else:
            try:
                destination = int(file_name.split(separator.divider)[0])
            except ValueError:
                destination = file_name.split(separator.divider)[0]
    # Or from the destination arguments
    elif args.get('destination') is not None:
        destination = args['destination']
    elif args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        destination = args['data']['destination']

    if not destination and ('isinternalnote' not in args or not args['isinternalnote']):
        # Put default destination
        destination = config.cfg[_process]['destination']
        log.info("Destination can't be found, using default destination : " + destination)
        search_ai_destination = True

    # Check if the destination is valid
    res, destinations_list = web_service.retrieve_entities()
    if not res:
        log.error('Unable to retrieve destinations list, exit...')
        return False, destinations_list

    destination = check_destination(destinations_list, destination)
    if destination and args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        args['data']['destination'] = destination

        # Check if the doctype is valid
    res, doctypes_list = web_service.retrieve_doctypes()
    if not doctypes_list:
        log.error('Unable to retrieve doctypes list, exit...')
        return False, doctypes_list

    forced_doctype = False

    if 'isinternalnote' not in args or not args['isinternalnote']:
        # Priorité au doctype passé en ligne de commande
        if args.get('doctype') not in [None, '']:
            forced_doctype = check_doctype(doctypes_list, args['doctype'], log)
            if not forced_doctype and 'reconciliation' not in _process:
                log.error('Document type passed by argument not found, exit...')
                return False, None

            if forced_doctype:
                log.info(
                    'Document type forced by CLI : '
                    + str(args['doctype'])
                    + ' -> '
                    + str(forced_doctype)
                )

                if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
                    config_mail.cfg[_process]['doctype'] = str(forced_doctype)
                    if 'data' in args:
                        args['data']['doctype'] = str(forced_doctype)
                else:
                    config.cfg[_process]['doctype'] = str(forced_doctype)

        else:
            if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
                tmp_doctype = config_mail.cfg[_process]['doctype']
            else:
                tmp_doctype = config.cfg[_process]['doctype']

            resolved_tmp_doctype = check_doctype(doctypes_list, tmp_doctype, log)
            if not resolved_tmp_doctype and 'reconciliation' not in _process:
                log.error('Document type not found, exit...')
                return False, None

            if resolved_tmp_doctype:
                if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
                    config_mail.cfg[_process]['doctype'] = str(resolved_tmp_doctype)
                else:
                    config.cfg[_process]['doctype'] = str(resolved_tmp_doctype)
                config.cfg[_process]['doctype'] = str(resolved_tmp_doctype)

    # If destination still not good, try with default destination
    if not isinstance(destination, int) or not destination:
        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
            destination = args['data']['destination']
            search_ai_destination = True
        else:
            if 'isinternalnote' not in args or not args['isinternalnote']:
                search_ai_destination = True
                destination = config.cfg[_process]['destination']

        for dest in destinations_list['entities']:
            if destination == dest['id']:
                destination = dest['serialId']
                if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
                    args['data']['destination'] = destination
                    search_ai_destination = False

    # Retrieve user_id to use it as typist
    if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        typist = args['data']['typist']
    else:
        if 'isinternalnote' not in args or not args['isinternalnote']:
            typist = config.cfg[_process]['typist']

    if 'isinternalnote' not in args or not args['isinternalnote']:
        if type(typist) is not int:
            list_of_users = web_service.retrieve_users()
            for user in list_of_users['users']:
                if typist == user['user_id']:
                    typist = user['id']
                    if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
                        args['data']['typist'] = typist
                    else:
                        config.cfg[_process]['typist'] = typist

    if args.get('isMail') is not None and args.get('isMail') is True:
        if args['isForm']:
            log.info('Start searching form into e-mail')
            form = process_form(args, config, config_mail, log, web_service, _process, file)
            if form and form[1] != 'default':
                return form

    if os.path.splitext(file)[1].lower() == '.pdf':  # Open the pdf and convert it to JPG
        res = image.pdf_to_jpg(file, True)
        if res is False:
            exit(os.EX_IOERR)

        # Check if pdf is already OCR and searchable
        check_ocr = subprocess.run(['pdffonts', file], capture_output=True, text=True, check=False)
        tmp = ''
        if check_ocr.stdout:
            for line in check_ocr.stdout:
                tmp += line

        is_ocr = len(tmp.split('\n')) > 3
    elif os.path.splitext(file)[1].lower() == '.html':
        res = image.html_to_txt(file)
        if res is False:
            return False, None
        ocr.text = res
        is_ocr = True
    elif os.path.splitext(file)[1].lower() == '.txt':
        ocr.text = open(file, 'r').read()
        is_ocr = True
    else:  # Open the picture
        image.open_img(file)
        is_ocr = False

    if 'reconciliation' not in _process and config.cfg['GLOBAL']['disable_lad'] == 'False' and ('isinternalnote' not in args or not args['isinternalnote']):
        # Get the OCR of the file as a string content
        if not args.get('isMail') and os.path.splitext(file)[1].lower() not in ('.html', '.txt'):
            ocr.text_builder(image.img)

    contact = {}
    custom_mail = ''

    if 'isinternalnote' not in args or not args['isinternalnote'] and os.path.splitext(file)[1].lower() == '.pdf':
        if args.get('isMail'):
            process_config = config_mail.cfg[_process]
        else:
            process_config = config.cfg[_process]

            if (not forced_doctype
                and 'doctype_ai' in process_config and process_config['doctype_ai'].lower() == 'true'
                and 'doctype' in config.cfg['IA'] and search_ai_destination):

                doctype_prediction = {}
                if 'doctype_mode' in config.cfg['IA'] and config.cfg['IA']['doctype_mode'].lower() == 'remote':
                    log.info('Search destination and doctype with remote AI model')
                    status, doctype_prediction = run_inference_destination_remote(config.cfg['IA'], image.img)
                    if not status:
                        log.info(f"ERROR : Destination AI remote model service not available - {doctype_prediction}")
                        doctype_prediction = {}
                else:
                    doctype_model = config.cfg['IA']['doctype']
                    if os.path.isdir(doctype_model) and os.listdir(doctype_model):
                        log.info('Search destination and doctype with AI model')
                        doctype_prediction = run_inference_destination(doctype_model, image.img)

                if doctype_prediction:
                    if 'doctype' in doctype_prediction:
                        resolved_doctype = check_doctype(doctypes_list, doctype_prediction['doctype'])
                        if resolved_doctype:
                            log.info(
                                'Document type found using AI : '
                                + str(doctype_prediction['doctype'])
                                + ' -> '
                                + str(resolved_doctype)
                            )
                            process_config['doctype'] = str(resolved_doctype)

                    if 'destination' in doctype_prediction:
                        ia_destination = check_destination(destinations_list, doctype_prediction['destination'])
                        if ia_destination:
                            destination = ia_destination
                            log.info('Destination found using AI : ' + doctype_prediction['destination'].upper())

        if ('sender_ai' in process_config and process_config['sender_ai'].lower() == 'true' and 'sender' in config.cfg['IA']):

            sender_prediction = {}
            if 'sender_mode' in config.cfg['IA'] and config.cfg['IA']['sender_mode'].lower() == 'remote' and image.img != None:
                log.info('Search sender with remote AI model')
                status, sender_prediction = run_inference_sender_remote(config.cfg['IA'], image.img)
                if not status:
                    log.info('ERROR : Sender AI remote model service not available : ' + str(sender_prediction))
            elif image.img != None:
                sender_model = config.cfg['IA']['sender']
                if os.path.isdir(sender_model) and os.listdir(sender_model):
                    log.info('Search sender with AI model')
                    sender_prediction = run_inference_sender(sender_model, image.jpg_name, log, config.cfg['IA']['sender_dtype'])
                else:
                    log.info('ERROR : Sender AI model not found')

            if sender_prediction:
                contact_class = FindContact(ocr.text, log, config, web_service, locale)
                contact = contact_class.find_contact_by_ai(sender_prediction, process_config)

    if 'reconciliation' not in _process and config.cfg['GLOBAL']['disable_lad'] == 'False' and ('isinternalnote' not in args or not args['isinternalnote']):
        # Find subject of document
        if (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']
                and args.get('priority_mail_subject') is True):
            subject_thread = ''
        else:
            subject_thread = FindSubject(ocr.text, locale, log, config)

        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and 'chrono_regex' not in config_mail.cfg[_process]:
            chrono_thread = ''
        elif args.get('isMail') is not None and args.get('isMail') in [True] and 'chrono_regex' in config_mail.cfg[_process] and config_mail.cfg[_process]['chrono_regex']:
            chrono_thread = FindChrono(ocr.text, config_mail.cfg[_process])
        elif _process in config.cfg and 'chrono_regex' in config.cfg[_process] and config.cfg[_process]['chrono_regex']:
            chrono_thread = FindChrono(ocr.text, config.cfg[_process])
        else:
            chrono_thread = ''

        # Find date of document
        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_date') is True:
            date_thread = ''
        else:
            date_thread = FindDate(ocr.text, locale, log, config)

        # Find mail in document and check if the contact exist in MEM Courrier
        if (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']
                and args.get('priority_mail_from') is True) or contact:
            contact_thread = ''
        else:
            contact_thread = FindContact(ocr.text, log, config, web_service, locale)

        # Launch all threads
        if date_thread:
            date_thread.start()
        if subject_thread:
            subject_thread.start()
        if contact_thread:
            contact_thread.start()
        if chrono_thread:
            chrono_thread.start()

        # Wait for end of threads
        if date_thread:
            date_thread.join()
        if subject_thread:
            subject_thread.join()
        if contact_thread:
            contact_thread.join()
        if chrono_thread:
            chrono_thread.join()

        # Get the returned values
        if date_thread:
            date = date_thread.date
        else:
            date = ''

        if chrono_thread:
            chrono_number = chrono_thread.chrono
        else:
            chrono_number = ''

        if subject_thread:
            subject = subject_thread.subject
            summary_AI = subject_thread.summary_AI
            tone_AI = subject_thread.tone_AI
        else:
            subject = ''
            summary_AI = ''
            tone_AI = ''

        if contact_thread:
            contact = contact_thread.contact
            custom_mail = contact_thread.custom_mail
    else:
        date = ''
        subject = ''
        summary_AI = ''
        tone_AI = ''
        chrono_number = ''
        custom_mail = ''

    try:
        os.remove(image.jpg_name)  # Delete the temp file used to OCR'ed the first PDF page
    except FileNotFoundError:
        pass

    # Create the searchable PDF if necessary
    if args.get('isMail') is not None and args.get('isMail') in [True]:
        file_format = 'html'
    elif args.get('isMail') is not None and args.get('isMail') in ['attachments']:
        file_format = args['format']
    else:
        file_format = config.cfg[_process]['format']

    if is_ocr is False:
        log.info('Start OCR on document before send it')
        ocr.generate_searchable_pdf(file, tmp_folder, separator)
        if ocr.searchable_pdf:
            # Compress pdf if necessary
            compress_pdf(args, config.cfg, _process, ocr.searchable_pdf, log)

            with open(ocr.searchable_pdf, 'rb') as f:
                file_to_send = f.read()
        else:
            if separator.convert_to_pdfa == 'True' and os.path.splitext(file)[1].lower() == '.pdf' and (not args.get('isMail')):
                output_file = file.replace(separator.output_dir, separator.output_dir_pdfa)
                separator.convert_to_pdfa_function(output_file, file, log)
                file = output_file

            # Compress pdf if necessary
            compress_pdf(args, config.cfg, _process, file, log)

            with open(file, 'rb') as f:
                file_to_send = f.read()
            file_format = os.path.splitext(file)[1].lower().replace('.', '')
    else:
        if separator.convert_to_pdfa == 'True' and os.path.splitext(file)[1].lower() == '.pdf' and (not args.get('isMail')):
            output_file = file.replace(separator.output_dir, separator.output_dir_pdfa)
            separator.convert_to_pdfa_function(output_file, file, log)
            file = output_file

        # Compress pdf if necessary
        compress_pdf(args, config.cfg, _process, file, log)

        with open(file, 'rb') as f:
            file_to_send = f.read()

    chrono_res_id = False

    if chrono_number:
        log.info('Chrono found in body : ' + chrono_number)

    if not chrono_number and args.get('isMail') is not None and args.get('isMail') in [True] and ('isinternalnote' not in args or not args['isinternalnote']):
        chrono_class = FindChrono(args['msg']['subject'], config_mail.cfg[_process])
        chrono_class.run()
        chrono_number = chrono_class.chrono
        if chrono_number:
            log.info('Chrono found in mail subject : ' + chrono_number)

    if chrono_number:
        chrono_res_id = web_service.retrieve_document_by_chrono(chrono_number)
        if chrono_res_id:
            if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
                if 'e_link_status' in config_mail.cfg[_process] and config_mail.cfg[_process]['e_link_status']:
                    args['data']['status'] = config_mail.cfg[_process]['e_link_status']
                if 'retrieve_metadata' in config_mail.cfg[_process] and config_mail.cfg[_process]['retrieve_metadata']:
                    if not forced_doctype and 'doctype' in chrono_res_id and chrono_res_id['doctype']:
                        args['data']['doctype'] = str(chrono_res_id['doctype'])
                    if 'destination' in chrono_res_id and chrono_res_id['destination']:
                        args['data']['destination'] = str(chrono_res_id['destination'])
                    listinstances = web_service.retrieve_listinstance(chrono_res_id['resId'])
                    if 'listInstance' in listinstances and listinstances['listInstance'] and len(listinstances['listInstance']) > 0:
                        for _list in listinstances['listInstance']:
                            if _list['item_mode'] == 'dest':
                                args['data']['diffusionList'] = [{
                                    "id": _list['itemSerialId'],
                                    "type": "user",
                                    "mode": "dest",
                                }]
            else:
                if 'e_link_status' in config.cfg[_process] and config.cfg[_process]['e_link_status']:
                    config.cfg[_process]['status'] = config.cfg[_process]['e_link_status']

                if 'retrieve_metadata' in config.cfg[_process] and config.cfg[_process]['retrieve_metadata']:
                    if not forced_doctype and 'doctype' in chrono_res_id and chrono_res_id['doctype']:
                        config.cfg[_process]['doctype'] = str(chrono_res_id['doctype'])
                    if 'destination' in chrono_res_id and chrono_res_id['destination']:
                        destination = str(chrono_res_id['destination'])
                    listinstances = web_service.retrieve_listinstance(chrono_res_id['resId'])
                    if 'listInstance' in listinstances and listinstances['listInstance'] and len(listinstances['listInstance']) > 0:
                        for _list in listinstances['listInstance']:
                            if _list['item_mode'] == 'dest':
                                config.cfg[_process]['diffusion_list'] = [{
                                    "id": _list['itemSerialId'],
                                    "type": "user",
                                    "mode": "dest",
                                }]

    if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        if date != '':
            args['data']['documentDate'] = date
        if subject != '':
            args['data']['subject'] = subject
        if summary_AI != '':
            args['data']['summary_AI'] = summary_AI
        if tone_AI != '':
            args['data']['tone_AI'] = tone_AI
        if contact:
            args['data']['senders'] = [{'id': contact['id'], 'type': 'contact'}]
        else:
            if 'emailFrom' in args and args['emailFrom']:
                if not (args.get('isMail') is not None and args.get('isMail') and args.get('priority_mail_from')):
                    log.info('No contact found on mail body, try with "from" of the mail :  ' + args['emailFrom'])
                    contact = web_service.retrieve_contact_by_mail(args['emailFrom'])
                    if contact:
                        log.info('Contact found using email : ' + args['emailFrom'])
                        args['data']['senders'] = [{'id': contact['id'], 'type': 'contact'}]

        if args.get('isMail') == 'attachments':
            args['data']['file'] = args['file']
            args['data']['format'] = args['format']

        if 'e_reconciliation' in config_mail.cfg[_process] and config_mail.cfg[_process]['e_reconciliation'] == 'True':
            log.info('E-reconciliation enabled, trying to read barcode')
            chrono = ''
            if file.lower().endswith('.pdf'):
                try:
                    images = convert_from_path(file)
                except Exception as e:
                    log.error(f"Failed to convert PDF to images: {e}")
                    return False, None

                detected_barcodes = []
                for img in images:
                    detected_barcodes.extend(decode(img))

                log.info(f"Detected barcodes: {detected_barcodes}")

                if 'reconciliation_type' not in config.cfg['OCForMEM']:
                    reconciliation_type = 'QRCODE'
                else:
                    reconciliation_type = config.cfg['OCForMEM']['reconciliation_type']

                for barcode in detected_barcodes:
                    if barcode.type == reconciliation_type:
                        log.info(f"Detected barcode data : {barcode.data.decode('utf-8')}")
                        response = web_service.check_attachment(barcode.data.decode('utf-8'))
                        if isinstance(response, dict) and response[0]:
                            chrono = barcode.data.decode('utf-8')
                        elif isinstance(response, tuple) or not response[0]:
                            chrono = ''
                            log.error(f"Error response: {response[1]}")

            if chrono != '':
                log.info('Start RECONCILIATION process')
                ws_res = web_service.insert_attachment_reconciliation(file_to_send, chrono,
                                                                   'OCForMEM_reconciliation_found', config)
            else:
                log.info('Start DEFAULT process')
                args['data']['file'] = file
                ws_res = web_service.insert_letterbox_from_mail(args['data'], config_mail.cfg[_process])
        else:
            log.info('Insert letterbox from mail default')
            if is_ocr is False and os.path.splitext(file)[1].lower() == '.pdf' and ocr.searchable_pdf and os.path.exists(ocr.searchable_pdf):
                args['data']['file'] = ocr.searchable_pdf
            ws_res = web_service.insert_letterbox_from_mail(args['data'], config_mail.cfg[_process])

        if ws_res[0]:
            log.info('Insert email OK : ' + str(ws_res))
            if chrono_number:
                if chrono_res_id:
                    web_service.link_documents(ws_res[1]['resId'], chrono_res_id['resId'])
            return ws_res
        try:
            shutil.move(file, config.cfg['GLOBAL']['error_path'] + os.path.basename(file))
        except shutil.Error as _e:
            log.error('Moving file ' + file + ' error : ' + str(_e))
        return ws_res
    elif 'is_attachment' in config.cfg[_process] and config.cfg[_process]['is_attachment'] != '':
        if 'isinternalnote' in args and args['isinternalnote']:
            res_id_master = web_service.retrieve_res_id_master_by_chrono(args['chrono'])
            if res_id_master and len(res_id_master['resources']) == 1:
                args['resid'] = res_id_master['resources'][0]['resId']
                ws_res = web_service.insert_attachment(file_to_send, config, args, _process)
            else:
                log.error('Unable to find master document for attachment, exit...')
                try:
                    shutil.move(file, config.cfg['GLOBAL']['error_path'] + os.path.basename(file))
                except shutil.Error as _e:
                    log.error('Moving file ' + file + ' error : ' + str(_e))
                return False, ''
        else:
            ws_res = web_service.insert_attachment_reconciliation(file_to_send, args['chrono'], _process, config)
    else:
        if 'custom_fields' not in args:
            args['custom_fields'] = None

        ws_res = web_service.insert_with_args(file_to_send, config, contact, subject, date, destination, config.cfg[_process], custom_mail, file_format, args['custom_fields'], summary_AI, tone_AI)

    if ws_res and ws_res[0] is not False:
        if 'isinternalnote' not in args or not args['isinternalnote']:
            log.info("Insert OK : " + str(ws_res[1]))
        else:
            log.info("Insert attachment OK : " + str(ws_res[1]))

        if chrono_res_id and chrono_number:
            new_res_id = ws_res[1]['resId']
            web_service.link_documents(new_res_id, chrono_res_id['resId'])

        if 'isinternalnote' in args and args['isinternalnote']:
            if 'document_status' in config.cfg[_process] and config.cfg[_process]['document_status'] != '':
                web_service.change_status(args['resid'], config, config.cfg[_process]['document_status'])
                log.info('Status changed for principal document')

        # BEGIN OBR01
        # If reattach is active and the origin document already exist,  reattach the new one to it
        if (config.cfg['REATTACH_DOCUMENT']['active'] == 'True' and config.cfg[_process].get('reconciliation') is not
                None and ('isinternalnote' not in args or not args['isinternalnote'])):
            log.info("Reattach document is active : " + config.cfg['REATTACH_DOCUMENT']['active'])
            if args['chrono']:
                check_document_res = web_service.check_document(args['chrono'])
                log.info("Reattach check result : " + str(check_document_res))
                if check_document_res['resources']:
                    res_id_origin = check_document_res['resources'][0]['res_id']
                    res_id_signed = ws_res[1]['resId']

                    log.info("Reattach res_id : " + str(res_id_origin) + " to " + str(res_id_signed))
                    # Get ws user id and reattach the document
                    list_of_users = web_service.retrieve_users()
                    for user in list_of_users['users']:
                        if config.cfg['OCForMEM']['user'] == user['user_id']:
                            typist = user['id']
                            reattach_res = web_service.reattach_to_document(res_id_origin, res_id_signed, typist, config)
                            log.info("Reattach result : " + str(reattach_res))

                    # Change status of the document
                    change_status_res = web_service.change_status(res_id_origin, config)
                    log.info("Change status : " + str(change_status_res))
        # END OBR01
        if args.get('isMail') is None:
            try:
                if args.get('keep_pdf_debug').lower() != 'true':
                    os.remove(file)
            except FileNotFoundError as _e:
                log.error('Unable to delete ' + file + ' after insertion : ' + str(_e))
        return ws_res
    try:
        shutil.move(file, config.cfg['GLOBAL']['error_path'] + os.path.basename(file))
    except shutil.Error as _e:
        log.error('Moving file ' + file + ' error : ' + str(_e))
    return False, ''
