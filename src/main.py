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
import time
import json
import tempfile

# useful to use the worker and avoid ModuleNotFoundError
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from kuyruk import Kuyruk
from src.classes.SMTP import SMTP
import src.classes.Log as logClass
import src.classes.Locale as localeClass
import src.classes.Images as imagesClass
import src.classes.Config as configClass
import src.classes.PyTesseract as ocrClass
from .process.FindSubject import FindSubject
import src.classes.Separator as separatorClass
import src.classes.WebServices as webserviceClass
from src.process.OCForMEM import process, get_process_name
from src.classes.Mail import move_batch_to_error, send_email_error_pj

OCForMEM = Kuyruk()

if os.path.isfile('./src/config/rabbitMQ.json'):
    with open('./src/config/rabbitMQ.json', 'r') as f:
        rabbitMQData = json.load(f)

    if rabbitMQData['host']:
        OCForMEM.config.RABBIT_HOST = rabbitMQData['host']
    if rabbitMQData['port']:
        OCForMEM.config.RABBIT_PORT = rabbitMQData['port']
    if rabbitMQData['username']:
        OCForMEM.config.RABBIT_USER = rabbitMQData['username']
    if rabbitMQData['password']:
        OCForMEM.config.RABBIT_PASSWORD = rabbitMQData['password']
    if rabbitMQData['vhost'] and rabbitMQData['vhost'] != '/':
        OCForMEM.config.RABBIT_VIRTUAL_HOST = rabbitMQData['vhost']


def str2bool(value):
    """
    Function to convert string to boolean

    :return: Boolean
    """
    return value.lower() in "true"


def check_file(image: imagesClass.Image, path: str, config: configClass.Config, log: logClass.Log) -> bool:
    """
    Check integrity of file

    :param image: Class Image instance
    :param path: Path to file
    :param config: Class Config instance
    :param log: Class Log instance
    :return: Boolean to show if integrity of file is ok or not
    """
    if not image.check_file_integrity(path, config):
        log.error('The integrity of file could\'nt be verified : ' + str(path))
        return False
    else:
        return True


def recursive_delete(list_folder: list, log: logClass.Log):
    """
    Delete recusively a folder (temporary folder)

    :param list_folder: list of folder to recursively delete
    :param log: Class Log instance
    """
    for folder in list_folder:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                try:
                    os.remove(folder + '/' + file)
                except FileNotFoundError as e:
                    log.error('Unable to delete ' + folder + '/' + file + ' on temp folder: ' + str(e))
            try:
                os.rmdir(folder)
            except FileNotFoundError as e:
                log.error('Unable to delete ' + folder + ' on temp folder: ' + str(e))


def timer(start_time: time.time(), end_time: time.time()):
    """
    Show how long the process takes

    :param start_time: Time when the program start
    :param end_time: Time when all the processes are done
    :return: Difference between :start_time and :end_time
    """
    hours, rem = divmod(end_time - start_time, 3600)
    minutes, seconds = divmod(rem, 60)
    return "{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds)


def process_file(image, path, config, log, args, separator, ocr, locale, web_service, tmp_folder, config_mail, smtp):
    if check_file(image, path, config, log):
        # Process the file and send it to MEM Courrier
        res = process(args, path, log, separator, config, image, ocr, locale, web_service, tmp_folder, config_mail)
        if args.get('isMail') is not None and args.get('isMail') is True:
            # Process the attachments of mail
            if res[0]:
                res_id = res[1]['resId']
                if len(args['attachments']) > 0:
                    log.info('Found ' + str(len(args['attachments'])) + ' attachments')
                    for attachment in args['attachments']:
                        if attachment['format'].lower() in args['extensionsAllowed']:
                            res = web_service.insert_attachment_from_mail(attachment, res_id)
                            if res[0]:
                                log.info('Insert attachment OK : ' + str(res[1]))
                                continue
                            send_email_error_pj(args['batch_path'], args['process'], args['msg'], res[1], smtp, attachment)
                            log.error('Error while inserting attachment : ' + str(res[1]))
                        else:
                            log.info('Attachment not in allowedExtensions : ' + attachment['subject'])
                else:
                    log.info('No attachments found')
            else:
                move_batch_to_error(args['batch_path'], args['error_path'], smtp, args['process'], args['msg'], res[1])
                log.error('Error while processing e-mail : ' + str(res[1]))

            recursive_delete([tmp_folder, separator.output_dir, separator.output_dir_pdfa], log)
            log.info('End process')
        else:
            return res


# @OCForMEM.task()
def launch(args):
    start = time.time()
    # Init all the necessary classes
    config = configClass.Config()
    config.load_file(args['config'])
    smtp = False

    if args.get('isMail') is not None and args['isMail'] in [True, 'attachments']:
        log = logClass.Log(args['log'])
        config_mail = configClass.Config()
        config_mail.load_file(args['config_mail'])
        smtp = SMTP(
            config_mail.cfg['GLOBAL']['smtp_notif_on_error'],
            config_mail.cfg['GLOBAL']['smtp_host'],
            config_mail.cfg['GLOBAL']['smtp_port'],
            config_mail.cfg['GLOBAL']['smtp_login'],
            config_mail.cfg['GLOBAL']['smtp_pwd'],
            config_mail.cfg['GLOBAL']['smtp_ssl'],
            config_mail.cfg['GLOBAL']['smtp_starttls'],
            config_mail.cfg['GLOBAL']['smtp_dest_admin_mail'],
            config_mail.cfg['GLOBAL']['smtp_delay'],
            config_mail.cfg['GLOBAL']['smtp_auth'],
            config_mail.cfg['GLOBAL']['smtp_from_mail'],
        )
        if args['isMail'] is True:
            log.info('Process email n°' + args['cpt'] + '/' + args['nb_of_mail'] + ' with UID : ' + args['msg_uid'])
    else:
        log = logClass.Log(config.cfg['GLOBAL']['logfile'])
        config_mail = False

    tmp_folder = tempfile.mkdtemp(dir=config.cfg['GLOBAL']['tmppath'])
    filename = tempfile.NamedTemporaryFile(dir=tmp_folder).name + '.jpg'
    locale = localeClass.Locale(config)
    ocr = ocrClass.PyTesseract(locale.localeOCR, log, config)
    web_service = webserviceClass.WebServices(
        config.cfg['OCForMEM']['host'],
        config.cfg['OCForMEM']['user'],
        config.cfg['OCForMEM']['password'],
        log,
        config.cfg['GLOBAL']['timeout'],
        config.cfg['OCForMEM']['certpath']
    )

    image = imagesClass.Images(
        filename,
        int(config.cfg['GLOBAL']['resolution']),
        int(config.cfg['GLOBAL']['compressionquality']),
        log,
        config
    )

    # Start process
    _process = get_process_name(args, config)
    args['process_name'] = _process
    separator = separatorClass.Separator(log, config, tmp_folder, _process)

    if args.get('isMail') is None or args.get('isMail') is False:
        separator.enabled = str2bool(config.cfg[_process]['separator_qr'])

    if args.get('file') is not None:
        path = args['file']
        if check_file(image, path, config, log):
            if separator.enabled:
                separator.run(path)
                if separator.error:  # in case the file is not a pdf or no qrcode was found, process as an image
                    process(args, path, log, separator, config, image, ocr, locale, web_service, tmp_folder)
                else:
                    for file in separator.pdf_list:
                        res = process_file(image, file, config, log, args, separator, ocr, locale, web_service, tmp_folder, config_mail, smtp)
                        if res[0]:
                            res = json.loads(res[1])
                            if 'resId' in res:
                                res_id = res['resId']
                                for pj in separator.pj_list:
                                    document_filename = os.path.basename(file)
                                    pj_filename = re.sub(r"#\d", "", os.path.basename(pj).replace('PJ_', ''))
                                    if pj_filename == document_filename:
                                        image.pdf_to_jpg(pj, True)
                                        ocr.text_builder(image.img)
                                        subject_thread = FindSubject(ocr.text, locale, log)
                                        subject_thread.start()
                                        subject_thread.join()
                                        pj_args = {
                                            'file': pj,
                                            'format': 'pdf',
                                            'status': 'A_TRA',
                                            'subject': subject_thread.subject
                                        }
                                        res = web_service.insert_attachment_from_mail(pj_args, res_id)
                                        if res:
                                            log.info('Attachment inserted : ' + str(res))
            else:
                process_file(image, path, config, log, args, separator, ocr, locale, web_service, tmp_folder, config_mail, smtp)
    recursive_delete([tmp_folder, separator.output_dir, separator.output_dir_pdfa], log)
    end = time.time()
    log.info('Process end after ' + timer(start, end) + '\n')
