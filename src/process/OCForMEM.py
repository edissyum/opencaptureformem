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
import pickle
import shutil
import warnings
import subprocess
import transformers
from .FindDate import FindDate
from pyzbar.pyzbar import decode
from .FindChrono import FindChrono
from .FindSubject import FindSubject
from .FindContact import FindContact
from .OCForForms import process_form
from pdf2image import convert_from_path


class DonutForImageClassification(transformers.DonutSwinPreTrainedModel):
    def __init__(self, config, num_labels_dest, num_labels_type):
        super().__init__(config)
        self.num_labels_dest = num_labels_dest
        self.num_labels_type = num_labels_type
        self.swin = transformers.DonutSwinModel(config)
        self.dropout = torch.nn.Dropout(0.5)
        self.classifier_dest = torch.nn.Linear(self.swin.num_features, num_labels_dest)
        self.classifier_type = torch.nn.Linear(self.swin.num_features, num_labels_type)

    def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
        outputs = self.swin(pixel_values)
        pooled_output = outputs[1]
        pooled_output = self.dropout(pooled_output)
        dest_logits = self.classifier_dest(pooled_output)
        type_logits = self.classifier_type(pooled_output)
        return dest_logits, type_logits


def run_inference_destination(trained_model, img):
    prediction = {}
    warnings.filterwarnings('ignore')
    transformers.logging.set_verbosity_error()

    with open(f'{trained_model}/dest_mapping.pkl', 'rb') as f:
        dest_mapping = pickle.load(f)
        dest_mapping = {v: k for k, v in dest_mapping.items()}

    with open(f'{trained_model}/type_mapping.pkl', 'rb') as f:
        type_mapping = pickle.load(f)
        type_mapping = {v: k for k, v in type_mapping.items()}

    processor = transformers.DonutProcessor.from_pretrained(trained_model, local_files_only=True)
    model = DonutForImageClassification.from_pretrained(trained_model, num_labels_dest=len(dest_mapping),
                                                        num_labels_type=len(type_mapping))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.load_state_dict(torch.load(f"{trained_model}/model_epoch.pth", map_location=torch.device(device)))
    model.to(device)
    model.eval()

    with torch.no_grad():
        pixel_values = processor(img, random_padding="test", return_tensors="pt").pixel_values.squeeze()
        pixel_values = torch.tensor(pixel_values).unsqueeze(0)
        dest_logits, type_logits = model(pixel_values=pixel_values)
        _, dest_index = torch.max(dest_logits, dim=1)
        _, type_index = torch.max(type_logits, dim=1)
        dest_pred = dest_mapping[dest_index[0].item()]
        type_pred = type_mapping[type_index[0].item()]
        if dest_pred:
            prediction['destination'] = dest_pred
        if type_pred:
            prediction['doctype'] = type_pred
    return prediction


def run_inference_sender(trained_model, img):
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
        return_dict_in_generate=True
    )
    prediction = processor.batch_decode(outputs.sequences)[0]
    prediction = processor.token2json(prediction)
    return prediction


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
            if (isinstance(dest['id'], int) or dest['id'].isnumeric()) and int(destination) == int(dest['id']):
                return dest['serialId']
    else:
        for dest in destinations['entities']:
            if str(destination).lower() == str(dest['id']).lower():
                destination = dest['serialId']
                return destination
    return False


def check_doctype(doctypes, doctype):
    if isinstance(doctype, int) or doctype.isnumeric():
        for doct in doctypes['structure']:
            if 'type_id' in doct and int(doctype) == int(doct['type_id']):
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
    destination = check_destination(destinations_list, destination)
    if destination and args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        args['data']['destination'] = destination

    # Check if the doctype is valid
    doctypes_list = web_service.retrieve_doctypes()
    if args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']:
        tmp_doctype = config_mail.cfg[_process]['doctype']
    else:
        tmp_doctype = config.cfg[_process]['doctype']

    if not check_doctype(doctypes_list, tmp_doctype) and 'reconciliation' not in _process:
        log.error('Document type not found, exit...')
        sys.exit(os.EX_CONFIG)

    # If destination still not good, try with default destination
    if not isinstance(destination, int) or not destination:
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

        is_ocr = len(tmp.split('\n')) > 3
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

    contact = {}
    custom_mail = ''
    if not args.get('isMail'):
        if ('doctype_entity_ai' in config.cfg[_process] and config.cfg[_process]['doctype_entity_ai'].lower() == 'true'
                and 'doctype_entity' in config.cfg['IA']):
            doctype_entity_model = config.cfg['IA']['doctype_entity']
            if os.path.isdir(doctype_entity_model) and os.listdir(doctype_entity_model):
                log.info('Search destination and doctype with AI model')
                doctype_entity_prediction = run_inference_destination(doctype_entity_model, image.img)
                if doctype_entity_prediction:
                    if 'doctype' in doctype_entity_prediction:
                        if check_doctype(doctypes_list, doctype_entity_prediction['doctype']):
                            log.info('Document type found using AI : ' + doctype_entity_prediction['doctype'])
                            config.cfg[_process]['doctype'] = doctype_entity_prediction['doctype']
                    if 'destination' in doctype_entity_prediction:
                        ia_destination = check_destination(destinations_list, doctype_entity_prediction['destination'])
                        if ia_destination:
                            destination = ia_destination
                            log.info('Destination found using AI : ' + doctype_entity_prediction['destination'].upper())
        if ('sender_ai' in config.cfg[_process] and
                config.cfg[_process]['sender_ai'].lower() == 'true'
                and 'sender_recipient' in config.cfg['IA']):
            sender_model = config.cfg['IA']['sender_recipient']
            if os.path.isdir(sender_model) and os.listdir(sender_model):
                log.info('Search sender with AI model')
                sender_prediction = run_inference_sender(sender_model, image.img)
                if sender_prediction:
                    contact_class = FindContact(ocr.text, log, config, web_service, locale)
                    contact = contact_class.find_contact_by_ai(sender_prediction)

    if 'reconciliation' not in _process and config.cfg['GLOBAL']['disablelad'] == 'False':
        # Get the OCR of the file as a string content
        if not args.get('isMail') and os.path.splitext(file)[1].lower() not in ('.html', '.txt'):
            ocr.text_builder(image.img)

        # Find subject of document
        if (args.get('isMail') is not None and args.get('isMail') in [True, 'attachments']
                and args.get('priority_mail_subject') is True):
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
        else:
            subject = ''

        if contact_thread:
            contact = contact_thread.contact
            custom_mail = contact_thread.custom_mail
    else:
        date = ''
        subject = ''
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
                if 'e_link_status' in config_mail.cfg[_process] and config_mail.cfg[_process]['e_link_status']:
                    args['data']['status'] = config_mail.cfg[_process]['e_link_status']
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
                if 'e_link_status' in config.cfg[_process] and config.cfg[_process]['e_link_status']:
                    config.cfg[_process]['status'] = config.cfg[_process]['e_link_status']

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
            if not (args.get('isMail') is not None and args.get('isMail') and args.get('priority_mail_from')):
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
                        log.info(f"Detected barcode data : {barcode.data.decode('utf-8')}")
                        response = web_service.check_attachment(barcode.data.decode('utf-8'))
                        if isinstance(response, dict) and response[0]:
                            chrono = barcode.data.decode('utf-8')
                        elif isinstance(response, tuple) or not response[0]:
                            chrono = ''
                            log.error(f"Error response: {response[1]}")

            if chrono != '':
                log.info('Start RECONCILIATION process')
                res = web_service.insert_attachment_reconciliation(file_to_send, chrono,
                                                                   'OCForMEM_reconciliation_found', config)
            else:
                log.info('Start DEFAULT process')
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
        if 'custom_fields' not in args:
            args['custom_fields'] = None

        res = web_service.insert_with_args(file_to_send, config, contact, subject, date, destination,
                                           config.cfg[_process], custom_mail, file_format, args['custom_fields'])

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
