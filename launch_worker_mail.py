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
import sys
import argparse
import tempfile
import datetime

from src.main import launch
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
    sys.exit('Config file couldn\'t be found')

process = args['process']

Config = configClass.Config()
Config.load_file(args['config'])

ConfigMail = configClass.Config()
ConfigMail.load_file(args['config_mail'])

if ConfigMail.cfg.get(process) is None:
    sys.exit('Process ' + process + ' is not set into ' + args['config_mail'] + ' file')

global_log = logClass.Log(Config.cfg['GLOBAL']['logfile'])

now = datetime.datetime.now()
path = ConfigMail.cfg['GLOBAL']['batchpath'] + '/' + str('%02d' % now.year) + str('%02d' % now.month) + str('%02d' % now.day) + '/'
path_without_time = ConfigMail.cfg['GLOBAL']['batchpath']

Mail = mailClass.Mail(
    ConfigMail.cfg[process]['host'],
    ConfigMail.cfg[process]['port'],
    ConfigMail.cfg[process]['login'],
    ConfigMail.cfg[process]['password'],
)
web_service = webserviceClass.WebServices(
    Config.cfg['OCForMaarch']['host'],
    Config.cfg['OCForMaarch']['user'],
    Config.cfg['OCForMaarch']['password'],
    global_log
)

cfg = ConfigMail.cfg[process]

isSSl = str2bool(cfg['isssl'])
folder_trash = cfg['foldertrash']
action = cfg['actionafterprocess']
folder_to_crawl = cfg['foldertocrawl']
folder_destination = cfg['folderdestination']
import_only_attachments = str2bool(ConfigMail.cfg['GLOBAL']['importonlyattachments'])
priority_mail_subject = str2bool(ConfigMail.cfg[process]['prioritytomailsubject'])
Mail.test_connection(isSSl)

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
            os.mkdir(path)
        date_batch = str('%02d' % now.year) + str('%02d' % now.month) + str('%02d' % now.day) + '_' + str('%02d' % now.hour) + str('%02d' % now.minute) + str('%02d' % now.second) + str('%02d' % now.microsecond)
        batch_path = tempfile.mkdtemp(dir=path, prefix='BATCH_' + date_batch + '_')

        Log = logClass.Log(batch_path + '/' + date_batch + '.log')
        Log.info('Start following batch : ' + os.path.basename(os.path.normpath(batch_path)))
        Log.info('Import only attachments is : ' + str(import_only_attachments))
        Log.info('Number of e-mail to process : ' + str(len(emails)))
        i = 1
        for msg in emails:
            # Backup all the e-mail into batch path
            Mail.backup_email(msg, batch_path)
            ret, file = Mail.construct_dict_before_send_to_maarch(msg, ConfigMail.cfg[process], batch_path)
            if not import_only_attachments:
                launch({
                    'cpt': str(i),
                    'file': file,
                    'isMail': True,
                    'msg_uid': str(msg.uid),
                    'process': process,
                    'data': ret['mail'],
                    'config': args['config'],
                    'batch_path': batch_path,
                    'nb_of_mail': str(len(emails)),
                    'attachments': ret['attachments'],
                    'error_path': path_without_time + '/_ERROR',
                    'log': batch_path + '/' + date_batch + '.log',
                    'priority_mail_subject': priority_mail_subject,
                })
            else:
                Log.info('Start to process only attachments')
                if len(ret['attachments']) > 0:
                    Log.info('Found ' + str(len(ret['attachments'])) + ' attachments')
                    for attachment in ret['attachments']:
                        launch({
                            'log': batch_path + '/' + date_batch + '.log',
                            'isMail': False,
                            'file': batch_path + '/attachments/' + attachment['filename'] + '.' + attachment['format'],
                            'process': 'incoming',
                            'data': ret['mail'],
                            'config': args['config']
                        })
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
