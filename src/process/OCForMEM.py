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

import os
import re
import sys
import json
import torch
import shutil
import warnings
import subprocess
import transformers
from .FindDate import FindDate
from .FindChrono import FindChrono
from .FindSubject import FindSubject
from .FindContact import FindContact
from .OCForForms import process_form


def search_entity_and_doctype(trained_model, img):
    warnings.filterwarnings('ignore')
    transformers.logging.set_verbosity_error()

    processor = transformers.DonutProcessor.from_pretrained(trained_model, local_files_only=True)
    model = transformers.VisionEncoderDecoderModel.from_pretrained(trained_model, local_files_only=True)

    pixel_values = processor(img, random_padding="test", return_tensors="pt").pixel_values.squeeze()
    pixel_values = torch.tensor(pixel_values).unsqueeze(0)
    task_prompt = "<s>"
    decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids

    device = "cuda" if torch.cuda.is_available() else "cpu"

    outputs = model.generate(
        pixel_values.to(device),
        decoder_input_ids=decoder_input_ids.to(device),
        max_length=model.decoder.config.max_position_embeddings,
        early_stopping=True,
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        use_cache=True,
        num_beams=1,
        bad_words_ids=[[processor.tokenizer.unk_token_id]],
        return_dict_in_generate=True,
    )
    prediction = processor.batch_decode(outputs.sequences)[0]
    prediction = processor.token2json(prediction)
    return prediction

from pdf2image import convert_from_path
from PIL import Image
from pyzbar.pyzbar import decode

def get_process_name(args, config):
    if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        _process = args['process']
    else:
        if args['process'] in config.cfg['OCForMEM']['processavailable'].split(','):
            _process = 'OCForMEM_' + args['process'].lower()
        else:
            _process = 'OCForMEM_' + config.cfg['OCForMEM']['defaultprocess'].lower()

    return _process


def compress_pdf(args, config, process, file, log):
    if not args.get('isMail') and os.path.splitext(file)[1].lower() not in ('.html', '.txt'):
        config = config[process]
        if 'compress_type' in config and config['compress_type'] and config['compress_type'] != 'None':
            log.info('Compress PDF : ' + config['compress_type'])
            compressed_file_path = '/tmp/min_' + os.path.basename(file)

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

    if type(destination) is not int:
        for dest in destinations['entities']:
            if str(destination).lower() == str(dest['id']).lower():
                destination = dest['serialId']
                return destination
    return False


def check_doctype(doctypes, doctype):
    if isinstance(doctype, int) or doctype.isnumeric():
        for doct in doctypes['structure']:
            if 'type_id' in doct and int(doctype) == int(doct['type_id']):
                print(doctype, doct['type_id'])
                return True
    return False


def process(args, file, log, separator, config, image, ocr, locale, web_service, tmp_folder, config_mail=None):
    log.info('Processing file : ' + file)

    # Check if the choosen process mode if available. If not take the default one
    _process = args['process_name']
    log.info('Using the following process : ' + _process)

    destination = ''

    # Check if RDFF is enabled, if yes : retrieve the service ID from the filename
    if args.get('RDFF') not in [None, False]:
        log.info('RDFF is enabled')
        file_name = os.path.basename(file)
        file_name = re.sub('^MEM_', '', file_name)
        file_name = re.sub('^MAARCH_', '', file_name)
        if separator.divider not in file_name:
            destination = config.cfg[_process]['destination']
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

    if not destination:
        # Put default destination
        destination = config.cfg[_process]['destination']
        log.info("Destination can't be found, using default destination : " + destination)

    # Check if the destination is valid
    destinations_list = web_service.retrieve_entities()
    destination = check_destination(destinations_list, destination.lower())
    if destination and args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        args['data']['destination'] = destination

    # Check if the status is valid
    doctypes_list = web_service.retrieve_doctypes()
    if not check_doctype(doctypes_list, config.cfg[_process]['doctype']):
        log.error('Document type not found, exit...')
        exit(os.EX_CONFIG)

    # If destination still not good, try with default destination
    if type(destination) is not int or not destination:
        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
            destination = args['data']['destination']
        else:
            destination = config.cfg[_process]['destination']

        for dest in destinations_list['entities']:
            if destination == dest['id']:
                destination = dest['serialId']
                if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
                    args['data']['destination'] = destination

    # Retrieve user_id to use it as typist
    if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        typist = args['data']['typist']
    else:
        typist = config.cfg[_process]['typist']

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

    if not args.get('isMail'):
        if 'IA' in config.cfg and 'enabled' in config.cfg['IA'] and config.cfg['IA']['enabled'].lower() == 'true':
            if 'doctype_entity' in config.cfg['IA']:
                trained_model = config.cfg['IA']['doctype_entity']
                if os.path.isdir(trained_model):
                    log.info('Search entity_id and doctype with IA model')
                    prediction = search_entity_and_doctype(trained_model, image.img)
                    if prediction:
                        if 'type_id' in prediction:
                            if check_doctype(doctypes_list, prediction['type_id']):
                                log.info('Document type found using IA : ' + prediction['type_id'])
                                config.cfg[_process]['doctype'] = prediction['type_id']
                        if 'entity_id' in prediction:
                            ia_destination = check_destination(destinations_list, prediction['entity_id'].lower())
                            if ia_destination:
                                destination = ia_destination
                                log.info('Destination found using IA : ' + prediction['entity_id'].upper())

    if 'reconciliation' not in _process and config.cfg['GLOBAL']['disablelad'] == 'False':
        # Get the OCR of the file as a string content
        if not args.get('isMail') and os.path.splitext(file)[1].lower() not in ('.html', '.txt'):
            ocr.text_builder(image.img)

        # Find subject of document
        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_subject') is True:
            subject_thread = ''
        else:
            subject_thread = FindSubject(ocr.text, locale, log)

        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and 'chronoregex' not in config_mail.cfg[_process]:
            chrono_thread = ''
        elif args.get('isMail') is not None and args.get('isMail') in [True] and 'chronoregex' in config_mail.cfg[_process] and config_mail.cfg[_process]['chronoregex']:
            chrono_thread = FindChrono(ocr.text, config_mail.cfg[_process])
        elif _process in config.cfg and 'chronoregex' in config.cfg[_process] and config.cfg[_process]['chronoregex']:
            chrono_thread = FindChrono(ocr.text, config.cfg[_process])
        else:
            chrono_thread = ''

        # Find date of document
        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_date') is True:
            date_thread = ''
        else:
            date_thread = FindDate(ocr.text, locale, log, config)

        # Find mail in document and check if the contact exist in MEM Courrier
        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_from') is True:
            contact_thread = ''
        else:
            contact_thread = FindContact(ocr.text, log, config, web_service, locale)

        # Launch all threads
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_date') is True):
            date_thread.start()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_subject') is True):
            subject_thread.start()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_from') is True):
            contact_thread.start()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']) and 'chronoregex' in config.cfg[_process] and config.cfg[_process]['chronoregex']:
            chrono_thread.start()
        elif args.get('isMail') is not None and args.get('isMail') in [True] and 'chronoregex' in config_mail.cfg[_process] and config_mail.cfg[_process]['chronoregex']:
            chrono_thread.start()

        # Wait for end of threads
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_date') is True):
            date_thread.join()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_subject') is True):
            subject_thread.join()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_from') is True):
            contact_thread.join()
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']) and 'chronoregex' in config.cfg[_process] and config.cfg[_process]['chronoregex']:
            chrono_thread.join()
        elif args.get('isMail') is not None and args.get('isMail') in [True] and 'chronoregex' in config_mail.cfg[_process] and config_mail.cfg[_process]['chronoregex']:
            chrono_thread.join()

        # Get the returned values
        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_date') is True):
            date = date_thread.date
        else:
            date = ''

        if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and 'chronoregex' not in config_mail.cfg[_process]:
            chrono_number = ''
        elif args.get('isMail') is not None and args.get('isMail') in [True] and 'chronoregex' in config_mail.cfg[_process] and config_mail.cfg[_process]['chronoregex']:
            chrono_number = chrono_thread.chrono
        elif _process in config.cfg and 'chronoregex' in config.cfg[_process] and config.cfg[_process]['chronoregex']:
            chrono_number = chrono_thread.chrono
        else:
            chrono_number = ''

        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_subject') is True):
            subject = subject_thread.subject
        else:
            subject = ''

        if not (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments'] and args.get('priority_mail_from') is True):
            contact = contact_thread.contact
            custom_mail = contact_thread.custom_mail
        else:
            contact = ''
            custom_mail = ''
    else:
        date = ''
        subject = ''
        chrono_number = ''
        contact = {}
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

    if not chrono_number and args.get('isMail') is not None and args.get('isMail') in [True]:
        chrono_class = FindChrono(args['msg']['subject'], config_mail.cfg[_process])
        chrono_class.run()
        chrono_number = chrono_class.chrono
        if chrono_number:
            log.info('Chrono found in mail subject : ' + chrono_number)

    if chrono_number:
        chrono_res_id = web_service.retrieve_document_by_chrono(chrono_number)
        if chrono_res_id:
            if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
                if 'e_reconciliation_status' in config_mail.cfg[_process] and config_mail.cfg[_process]['e_reconciliation_status']:
                    args['data']['status'] = config_mail.cfg[_process]['e_reconciliation_status']
                if 'retrieve_metadata' in config_mail.cfg[_process] and config_mail.cfg[_process]['retrieve_metadata']:
                    if 'doctype' in chrono_res_id and chrono_res_id['doctype']:
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
                if 'e_reconciliation_status' in config.cfg[_process] and config.cfg[_process]['e_reconciliation_status']:
                    config.cfg[_process]['status'] = config.cfg[_process]['e_reconciliation_status']

                if 'retrieve_metadata' in config.cfg[_process] and config.cfg[_process]['retrieve_metadata']:
                    if 'doctype' in chrono_res_id and chrono_res_id['doctype']:
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
        if contact:
            args['data']['senders'] = [{'id': contact['id'], 'type': 'contact'}]
        else:
            if not (args.get('isMail') is not None and args.get('isMail') is True and args.get('priority_mail_from') is True):
                log.info('No contact found on mail body, try with "from" of the mail :  ' + args['from'])
            contact = web_service.retrieve_contact_by_mail(args['from'])
            if contact:
                args['data']['senders'] = [{'id': contact['id'], 'type': 'contact'}]

        if args.get('isMail') == 'attachments':
            args['data']['file'] = args['file']
            args['data']['format'] = args['format']

        if 'ereconciliation' in config_mail.cfg[_process] and config_mail.cfg[_process]['ereconciliation'] == 'True':
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

                if 'reconciliationtype' not in config.cfg['OCForMEM']:
                    reconciliation_type = 'QRCODE'
                else:
                    reconciliation_type = config.cfg['OCForMEM']['reconciliationtype']

                for barcode in detected_barcodes:
                    if barcode.type == reconciliation_type:
                        log.info(f"Detected barcode data: {barcode.data.decode('utf-8')}")
                        response = web_service.check_attachment(barcode.data.decode('utf-8'))
                        if isinstance(response, dict):
                            chrono = barcode.data.decode('utf-8')
                            log.info('OK')
                        elif isinstance(response, tuple):
                            if not response[0]:
                                chrono = ''
                                log.info('KO')
                                log.error(f"Error response: {response[1]}")

            if chrono != '':
                log.info('Insert attachment reconciliation')
                res = web_service.insert_attachment_reconciliation(file_to_send, chrono, config_mail.cfg[_process]['processreconciliationsuccess'], config)
            else:
                log.info('Insert letterbox from mail')
                args['data']['file'] = file
                res = web_service.insert_letterbox_from_mail(args['data'], config_mail.cfg[_process])
        else:
            log.info('Insert letterbox from mail default')
            res = web_service.insert_letterbox_from_mail(args['data'], config_mail.cfg[_process])
        if res:
            log.info('Insert email OK : ' + str(res))
            if chrono_number:
                if chrono_res_id:
                    web_service.link_documents(res[1]['resId'], chrono_res_id['resId'])
            return res
        try:
            shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
        except shutil.Error as _e:
            log.error('Moving file ' + file + ' error : ' + str(_e))
        return False, res
    elif 'is_attachment' in config.cfg[_process] and config.cfg[_process]['is_attachment'] != '':
        if args['isinternalnote']:
            res = web_service.insert_attachment(file_to_send, config, args['resid'], _process)
        else:
            res = web_service.insert_attachment_reconciliation(file_to_send, args['chrono'], _process, config)
    else:
        res = web_service.insert_with_args(file_to_send, config, contact, subject, date, destination, config.cfg[_process], custom_mail, file_format)

    if res and res[0] is not False:
        log.info("Insert OK : " + str(res))
        if chrono_res_id and chrono_number:
            new_res_id = json.loads(res)['resId']
            web_service.link_documents(new_res_id, chrono_res_id['resId'])

        # BEGIN OBR01
        # If reattach is active and the origin document already exist,  reattach the new one to it
        if config.cfg['REATTACH_DOCUMENT']['active'] == 'True' and config.cfg[_process].get('reconciliation') is not None:
            log.info("Reattach document is active : " + config.cfg['REATTACH_DOCUMENT']['active'])
            if args['chrono']:
                check_document_res = web_service.check_document(args['chrono'])
                log.info("Reattach check result : " + str(check_document_res))
                if check_document_res['resources']:
                    res_id_origin = check_document_res['resources'][0]['res_id']
                    res_id_signed = json.loads(res)['resId']

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
        return True, res
    try:
        shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
    except shutil.Error as _e:
        log.error('Moving file ' + file + ' error : ' + str(_e))
    return False, ''
