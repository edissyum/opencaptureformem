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
import queue
import sys
import tempfile
import time

# useful to use the worker and avoid ModuleNotFoundError
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from kuyruk import Kuyruk
from kuyruk_manager import Manager
import src.classes.Log as logClass
import src.classes.Locale as localeClass
import src.classes.Images as imagesClass
import src.classes.Config as configClass
import src.classes.PyTesseract as ocrClass
from src.process.OCForMaarch import process, get_process_name
from src.classes.Mail import move_batch_to_error
from src.classes.SMTP import SMTP
import src.classes.Separator as separatorClass
import src.classes.WebServices as webserviceClass

OCforMaarch = Kuyruk()

OCforMaarch.config.MANAGER_HOST = "127.0.0.1"
OCforMaarch.config.MANAGER_PORT = 16501
OCforMaarch.config.MANAGER_HTTP_PORT = 16500

m = Manager(OCforMaarch)


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
        # Process the file and send it to Maarch
        res = process(args, path, log, separator, config, image, ocr, locale, web_service, tmp_folder, None, config_mail)

        if args.get('isMail') is not None and args.get('isMail') is True:
            # Process the attachments of mail
            if res[0]:
                res_id = res[1]['resId']
                if len(args['attachments']) > 0:
                    log.info('Found ' + str(len(args['attachments'])) + ' attachments')
                    for attachment in args['attachments']:
                        res = web_service.insert_attachment_from_mail(attachment, res_id)
                        if res[0]:
                            log.info('Insert attachment OK : ' + str(res[1]))
                            continue
                        else:
                            move_batch_to_error(args['batch_path'], args['error_path'], smtp, args['process'], args['msg'], res[1])
                            log.error('Error while inserting attachment : ' + str(res[1]))
                else:
                    log.info('No attachments found')
            else:
                move_batch_to_error(args['batch_path'], args['error_path'], smtp, args['process'], args['msg'], res[1])
                log.error('Error while processing e-mail : ' + str(res[1]))

            recursive_delete([tmp_folder, separator.output_dir, separator.output_dir_pdfa], log)
            log.info('End process')


# If needed just run "kuyruk --app src.main.OCforMaarch manager" to have web dashboard of current running worker
@OCforMaarch.task()
def launch(args):
    start = time.time()
    # Init all the necessary classes
    config = configClass.Config()
    config.load_file(args['config'])
    smtp = False

    if args.get('isMail') is not None and args['isMail'] is True:
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
        )
        log.info('Process email n°' + args['cpt'] + '/' + args['nb_of_mail'] + ' with UID : ' + args['msg_uid'])
    else:
        log = logClass.Log(config.cfg['GLOBAL']['logfile'])
        config_mail = False

    tmp_folder = tempfile.mkdtemp(dir=config.cfg['GLOBAL']['tmppath'])
    filename = tempfile.NamedTemporaryFile(dir=tmp_folder).name + '.jpg'
    locale = localeClass.Locale(config)
    ocr = ocrClass.PyTesseract(locale.localeOCR, log)
    separator = separatorClass.Separator(log, config, tmp_folder)
    web_service = webserviceClass.WebServices(
        config.cfg['OCForMaarch']['host'],
        config.cfg['OCForMaarch']['user'],
        config.cfg['OCForMaarch']['password'],
        log
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

    if args.get('isMail') is None or args.get('isMail') is False:
        separator.enabled = str2bool(config.cfg[_process]['separator_qr'])

    if args.get('path') is not None:
        path = args['path']
        if separator.enabled:
            for fileToSep in os.listdir(path):
                if check_file(image, path + fileToSep, config, log):
                    separator.run(path + fileToSep)
                    for file in separator.pdf_list:
                        process_file(image, file, config, log, args, separator, ocr, locale, web_service, tmp_folder, config_mail, smtp)
        else:
            for file in os.listdir(path):
                process_file(image, path + '/' + file, config, log, args, separator, ocr, locale, web_service, tmp_folder, config_mail, smtp)

    elif args.get('file') is not None:
        path = args['file']
        if check_file(image, path, config, log):
            if separator.enabled:
                separator.run(path)
                if separator.error:  # in case the file is not a pdf or no qrcode was found, process as an image
                    process(args, path, log, separator, config, image, ocr, locale, web_service, tmp_folder)
                else:
                    for file in separator.pdf_list:
                        process_file(image, file, config, log, args, separator, ocr, locale, web_service, tmp_folder, config_mail, smtp)
            else:
                process_file(image, path, config, log, args, separator, ocr, locale, web_service, tmp_folder, config_mail, smtp)

    # Empty the tmp dir to avoid residual file
    recursive_delete([tmp_folder, separator.output_dir, separator.output_dir_pdfa], log)

    end = time.time()
    log.info('Process end after ' + timer(start, end) + '\n')
