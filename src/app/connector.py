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
# @dev : Arthur Mondon <arthur@mondon.pro>

import os
import sys
import base64
import datetime
import tempfile
import requests
from src.classes.SMTP import SMTP
import src.classes.Log as logClass
import src.classes.Mail as mailClass
from src.main import launch, str2bool
import src.classes.Config as configClass
import src.classes.WebServices as webserviceClass
from src.app.controllers.custom import get_custom_config_file_path, get_custom_config_value, \
    get_custom_mail_config_file_path


def process_files(files, custom_id, process_name, read_destination_from_filename, keep_pdf_debug, destination,
                  custom_fields):
    config_file_path, error = get_custom_config_file_path(custom_id)
    if error:
        return {"message": error}, 400

    config_temp_dir, error = get_custom_config_value(config_file_path, 'tmppath', 'GLOBAL')
    if error:
        return {"message": error}, 400

    if not os.path.exists(config_temp_dir):
        os.makedirs(config_temp_dir, exist_ok=True)

    errors = []
    for _, file in enumerate(files):
        tmp_file_path = config_temp_dir + '/' + file['file_name']
        with open(tmp_file_path, 'wb') as temp_file:
            temp_file.write(base64.b64decode(file["file_content"]))
        temp_file.close()

        os.chmod(tmp_file_path, 0o644)

        args = {
            'script': 'API',
            'file': tmp_file_path,
            'process_name': process_name,
            'config': config_file_path,
            'destination': destination,
            'custom_fields': custom_fields,
            'keep_pdf_debug': keep_pdf_debug,
            'RDFF': read_destination_from_filename
        }

        try:
            launch(args)
        except Exception as e:
            errors.append({"file_name": file["file_name"], "error": str(e)})

    if errors:
        return {"message": "Some files encountered errors", "errors": errors}, 500
    else:
        return {"message": "All files processed successfully"}, 200


def generate_graphql_access_token(data):
    get_token_url = data['get_token_url'].replace('{tenant_id}', data['tenant_id'])
    return graphql_request(get_token_url, 'POST', data, [])


def graphql_request(url, method, data, headers):
    if method == 'GET':
        return requests.get(url, headers=headers, timeout=30)

    if method == 'POST':
        return requests.post(url, data=data, headers=headers, timeout=30)


def process_mail(mail_id, custom_id, process_name, note):
    config_path, error = get_custom_config_file_path(custom_id)
    if error:
        return {"error": error}, 400

    config_mail_path, error = get_custom_mail_config_file_path(custom_id)
    if error:
        return {"error": error}, 400

    config = configClass.Config()
    config.load_file(config_path)

    config_mail = configClass.Config()
    config_mail.load_file(config_mail_path)

    if config_mail.cfg.get(process_name) is None:
        sys.exit('Process ' + process_name + ' is not set into ' + config_mail_path + ' file')

    global_log = logClass.Log(config.cfg['GLOBAL']['logfile'])

    now = datetime.datetime.now()
    path = config_mail.cfg['GLOBAL']['batchpath'] + '/' + process_name + '/' + str('%02d' % now.year) + str('%02d' % now.month) + str('%02d' % now.day) + '/'
    path_without_time = config_mail.cfg['GLOBAL']['batchpath']

    web_service = webserviceClass.WebServices(
        config.cfg['OCForMEM']['host'],
        config.cfg['OCForMEM']['user'],
        config.cfg['OCForMEM']['password'],
        global_log,
        config.cfg['GLOBAL']['timeout'],
        config.cfg['OCForMEM']['certpath']
    )

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
        config_mail.cfg['GLOBAL']['smtp_from_mail']
    )

    mail = mailClass.Mail(
        config_mail.cfg[process_name]['auth_method'],
        config_mail.cfg['OAUTH'],
        config_mail.cfg['EXCHANGE'],
        config_mail.cfg['GRAPHQL'],
        config_mail.cfg[process_name]['host'],
        config_mail.cfg[process_name]['port'],
        config_mail.cfg[process_name]['login'],
        config_mail.cfg[process_name]['password'],
        web_service,
        smtp,
    )
    auth_method = config_mail.cfg[process_name]['auth_method']
    if auth_method.lower() != 'graphql':
        return {"error": "Connexion GraphQL non paramétrée"}, 500

    cfg = config_mail.cfg[process_name]

    secured_connection = cfg['securedconnection']
    import_only_attachments = str2bool(cfg['importonlyattachments'])
    priority_mail_subject = str2bool(config_mail.cfg[process_name]['prioritytomailsubject'])
    priority_mail_date = str2bool(config_mail.cfg[process_name]['prioritytomaildate'])
    priority_mail_from = str2bool(config_mail.cfg[process_name]['prioritytomailfrom'])
    force_utf8 = str2bool(config_mail.cfg[process_name]['forceutf8'])
    add_mail_headers_in_body = str2bool(config_mail.cfg[process_name]['addmailheadersinbody'])
    mail.test_connection(secured_connection)

    if mail.graphql_user is None:
        return {"error": "Erreur lors de la connexion GraphQL"}, 500

    extensionsAllowed = []
    for extension in config_mail.cfg[process_name]['extensionsallowed'].split(','):
        extensionsAllowed.append(extension.strip().lower())

    try:
        msg = mail.retrieve_message_by_id(mail_id)
        if msg is None or msg.status_code != 200:
            return {"error": "Erreur lors de la récupération du mail"}, 500

        msg = msg.json()
        now = datetime.datetime.now()
        if not os.path.exists(path):
            os.makedirs(path)
            os.chmod(path, 0o775)

        year, month, day = [str('%02d' % now.year), str('%02d' % now.month), str('%02d' % now.day)]
        hour, minute, second, microsecond = [str('%02d' % now.hour), str('%02d' % now.minute), str('%02d' % now.second), str('%02d' % now.microsecond)]

        date_batch = year + month + day + '_' + hour + minute + second + microsecond
        batch_path = tempfile.mkdtemp(dir=path, prefix='BATCH_' + date_batch + '_')
        os.chmod(batch_path, 0o775)
        Log = logClass.Log(batch_path + '/' + date_batch + '.log')
        Log.info('Start following batch from Addin Outlook : ' + os.path.basename(os.path.normpath(batch_path)))
        Log.info('Action after processing e-mail is : move')

        mail.backup_email(msg, batch_path, force_utf8, add_mail_headers_in_body, Log)
        ret, file = mail.construct_dict_before_send_to_mem(msg, config_mail.cfg[process_name], batch_path, Log)
        _from = ret['mail']['emailFrom']
        document_date = datetime.datetime.strptime(msg['receivedDateTime'], '%Y-%m-%dT%H:%M:%SZ')
        print('document_date', document_date)
        print(document_date.strftime('%d/%m/%Y %H:%M:%S'))
        launch({
            'cpt': '1',
            'file': file,
            'from': _from,
            'isMail': True,
            'msg_uid': str(msg['id']),
            'msg': {'date': document_date.strftime('%d/%m/%Y %H:%M:%S'), 'subject': msg['subject'], 'uid': msg['id']},
            'process': process_name,
            'data': ret['mail'],
            'config': config_path,
            'script': process_name,
            'isForm': False,
            'config_mail': config_mail_path,
            'batch_path': batch_path,
            'nb_of_mail': '1',
            'notes': [note],
            'attachments': ret['attachments'],
            'extensionsAllowed': extensionsAllowed,
            'log': batch_path + '/' + date_batch + '.log',
            'priority_mail_subject': priority_mail_subject,
            'priority_mail_date': priority_mail_date,
            'priority_mail_from': priority_mail_from,
            'error_path': path_without_time + '/_ERROR/' + process_name + '/' + year + month + day
        })
    except Exception as e:
        return {"error": str(e)}, 500

    return {"message": "Mail envoyé avec succès"}, 200
