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
import sys
import argparse
import tempfile
import datetime
from src.main import launch
from src.classes.SMTP import SMTP
import src.classes.Log as logClass
import src.classes.Mail as mailClass
import src.classes.Config as configClass
import src.classes.WebServices as webserviceClass


def str2bool(value):
    """
    Function to convert string to boolean

    :return: Boolean
    """
    return value.lower() in "true"


def check_folders(folder_crawl, folder_dest=False):
    """
    Check if IMAP folder exist

    :param folder_crawl: IMAP source folder
    :param folder_dest: IMAP destination folder (if action is made to move or delete)
    :return: Boolean
    """
    if not Mail.check_if_folder_exist(folder_crawl):
        print('The folder to crawl "' + folder_to_crawl + '" doesnt exist')
        return False
    else:
        if folder_dest is not False:
            if not Mail.check_if_folder_exist(folder_dest):
                print('The destination folder "' + str(folder_dest) + '" doesnt exist')
                return False
        return True


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--config", required=True, help="path to config.ini")
ap.add_argument("-cm", "--config_mail", required=True, help="path to mail.ini")
ap.add_argument('-p', "--process", required=True, default='MAIL_1')
args = vars(ap.parse_args())

if not os.path.exists(args['config']) or not os.path.exists(args['config_mail']):
    sys.exit('config file couldn\'t be found')

process = args['process']
print('Start process : ' + process)

config = configClass.Config()
config.load_file(args['config'])

config_mail = configClass.Config()
config_mail.load_file(args['config_mail'])

if config_mail.cfg.get(process) is None:
    sys.exit('Process ' + process + ' is not set into ' + args['config_mail'] + ' file')

global_log = logClass.Log(config.cfg['GLOBAL']['logfile'])

now = datetime.datetime.now()
path = config_mail.cfg['GLOBAL']['batchpath'] + '/' + process + '/' + str('%02d' % now.year) + str('%02d' % now.month) + str('%02d' % now.day) + '/'
path_without_time = config_mail.cfg['GLOBAL']['batchpath']

web_service = webserviceClass.WebServices(
    config.cfg['OCForMEM']['host'],
    config.cfg['OCForMEM']['user'],
    config.cfg['OCForMEM']['password'],
    global_log,
    config.cfg['GLOBAL']['timeout'],
    config.cfg['OCForMEM']['certpath']
)

SMTP = SMTP(
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
    config_mail.cfg['GLOBAL']['smtp_from_mail']
)

Mail = mailClass.Mail(
    config_mail.cfg[process]['auth_method'],
    config_mail.cfg['OAUTH'],
    config_mail.cfg[process]['host'],
    config_mail.cfg[process]['port'],
    config_mail.cfg[process]['login'],
    config_mail.cfg[process]['password'],
    web_service,
    SMTP,
)

cfg = config_mail.cfg[process]

secured_connection = cfg['securedconnection']
folder_trash = cfg['foldertrash']
action = cfg['actionafterprocess']
folder_to_crawl = cfg['foldertocrawl']
folder_destination = cfg['folderdestination']
import_only_attachments = str2bool(cfg['importonlyattachments'])
priority_mail_subject = str2bool(config_mail.cfg[process]['prioritytomailsubject'])
priority_mail_date = str2bool(config_mail.cfg[process]['prioritytomaildate'])
priority_mail_from = str2bool(config_mail.cfg[process]['prioritytomailfrom'])
is_form = str2bool(config_mail.cfg[process]['isform'])
force_utf8 = str2bool(config_mail.cfg[process]['forceutf8'])
Mail.test_connection(secured_connection)

extensionsAllowed = []
for extension in config_mail.cfg[process]['extensionsallowed'].split(','):
    extensionsAllowed.append(extension.strip().lower())

if action == 'delete':
    if folder_trash != '':
        check = check_folders(folder_to_crawl, folder_trash)
    else:
        check = check_folders(folder_to_crawl)
elif action == 'move':
    check = check_folders(folder_to_crawl, folder_destination)
else:
    check = check_folders(folder_to_crawl)

if check:
    Mail.select_folder(folder_to_crawl)
    emails = Mail.retrieve_message()
    if len(emails) > 0:
        now = datetime.datetime.now()
        if not os.path.exists(path):
            os.makedirs(path)

        year, month, day = [str('%02d' % now.year), str('%02d' % now.month), str('%02d' % now.day)]
        hour, minute, second, microsecond = [str('%02d' % now.hour), str('%02d' % now.minute), str('%02d' % now.second), str('%02d' % now.microsecond)]

        date_batch = year + month + day + '_' + hour + minute + second + microsecond
        batch_path = tempfile.mkdtemp(dir=path, prefix='BATCH_' + date_batch + '_')

        print('Batch name : data/MailCollect' + batch_path.split('/MailCollect')[1].replace('//', '/'))
        print('Batch error name : data/MailCollect/_ERROR/' + batch_path.split('/MailCollect')[1].replace('//', '/'))

        Log = logClass.Log(batch_path + '/' + date_batch + '.log')
        Log.info('Start following batch : ' + os.path.basename(os.path.normpath(batch_path)))
        Log.info('Import only attachments is : ' + str(import_only_attachments))
        Log.info('Action after processing e-mail is : ' + action)
        Log.info('Number of e-mail to process : ' + str(len(emails)))
        i = 1
        for msg in emails:
            # Backup all the e-mail into batch path
            Mail.backup_email(msg, batch_path, force_utf8)
            ret, file = Mail.construct_dict_before_send_to_mem(msg, config_mail.cfg[process], batch_path, Log)
            _from = ret['mail']['from']
            if not import_only_attachments:
                launch({
                    'cpt': str(i),
                    'file': file,
                    'from': _from,
                    'isMail': True,
                    'isForm': is_form,
                    'msg_uid': str(msg.uid),
                    'msg': {'date': msg.date.strftime('%d/%m/%Y %H:%M:%S'), 'subject': msg.subject, 'uid': msg.uid},
                    'process': process,
                    'data': ret['mail'],
                    'config': args['config'],
                    'config_mail': args['config_mail'],
                    'batch_path': batch_path,
                    'nb_of_mail': str(len(emails)),
                    'attachments': ret['attachments'],
                    'extensionsAllowed': extensionsAllowed,
                    'log': batch_path + '/' + date_batch + '.log',
                    'priority_mail_subject': priority_mail_subject,
                    'priority_mail_date': priority_mail_date,
                    'priority_mail_from': priority_mail_from,
                    'error_path': path_without_time + '/_ERROR/' + process + '/' + year + month + day
                })
            else:
                Log.info('Start to process only attachments')
                if len(ret['attachments']) > 0:
                    Log.info('Found ' + str(len(ret['attachments'])) + ' attachments')
                    cpt = 1
                    for attachment in ret['attachments']:
                        if attachment['format'].lower() == 'pdf':
                            launch({
                                'isMail': 'attachments',
                                'data': ret['mail'],
                                'from': _from,
                                'process': process,
                                'config': args['config'],
                                'config_mail': args['config_mail'],
                                'file': attachment['file'],
                                'format': attachment['format'],
                                'priority_mail_date': priority_mail_date,
                                'priority_mail_from': priority_mail_from,
                                'priority_mail_subject': priority_mail_subject,
                                'log': batch_path + '/' + date_batch + '.log'
                            })
                        else:
                            Log.error('Attachment n°' + str(cpt) + ' is not a pdf file')
                        cpt += 1
                else:
                    Log.info('No attachments found')

            if action not in ['move', 'delete', 'none']:
                action = 'none'

            if action == 'move':
                Log.info('Move mail into archive folder : ' + folder_destination)
                Mail.move_to_destination_folder(msg, folder_destination, Log)

            elif action == 'delete':
                Log.info('Move mail to trash')
                Mail.delete_mail(msg, folder_trash, Log)
            i = i + 1
    else:
        sys.exit('Folder do not contain any e-mail. Exit...')
else:
    sys.exit(0)
