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
import msal
import json
import shutil
import base64
import mimetypes
from ssl import SSLError
from socket import gaierror
from imaplib import IMAP4_SSL
from tnefparse.tnef import TNEF
from exchangelib.version import EXCHANGE_O365
from imap_tools import utils, MailBox, MailBoxTls, MailBoxUnencrypted
from exchangelib import Account, OAuth2Credentials, Configuration, OAUTH2, IMPERSONATION, Version, FileAttachment


class Mail:
    def __init__(self, auth_method, oauth, exchange, host, port, login, pwd, ws, smtp):
        self.ws = ws
        self.pwd = pwd
        self.conn = None
        self.port = port
        self.host = host
        self.SMTP = smtp
        self.oauth = oauth
        self.login = login
        self.exchange = exchange
        self.auth_method = auth_method

    def send_notif(self, msg, step):
        if self.SMTP.isUp:
            self.SMTP.send_email(message=msg, step=step)

    def generate_oauth_token(self):
        """
        Generate a token for oauth (Open Authentication)
        :return: token result
        """
        app = msal.ConfidentialClientApplication(self.oauth['client_id'],
                                                 authority=self.oauth['authority'] + self.oauth['tenant_id'],
                                                 client_credential=self.oauth['secret'])

        result = app.acquire_token_silent([self.oauth['scopes']], account=None)

        if not result:
            # No suitable token in cache.  Getting a new one.
            result = app.acquire_token_for_client(scopes=[self.oauth['scopes']])

        if "access_token" in result:
            # Token generated with success.
            return result

        # Error while generated token.
        print(result.get("error"))
        print(result.get("error_description"))
        print(result.get("correlation_id"))
        sys.exit()

    def generate_auth_string(self, token):
        """
        Generate Oauth string based on user and token
        :param token: Oauth token
        :return: string
        """
        return f"user={self.login}\x01auth=Bearer {token}\x01\x01"

    def test_connection(self, secured_connection):
        """
        Test the connection to the IMAP server
        :param secured_connection: boolean
        """

        if self.auth_method == 'exchange':
            credentials = OAuth2Credentials(
                tenant_id=self.exchange['tenant_id'],
                client_id=self.exchange['client_id'],
                client_secret=self.exchange['secret']
            )

            config = Configuration(
                auth_type=OAUTH2,
                credentials=credentials,
                version=Version(build=EXCHANGE_O365),
                service_endpoint=self.exchange['endpoint']
            )

            self.conn = Account(self.login, credentials=credentials, config=config, access_type=IMPERSONATION)
        else:
            try:
                if secured_connection == 'SSL':
                    self.conn = MailBox(host=self.host, port=self.port)
                elif secured_connection == 'STARTTLS':
                    self.conn = MailBoxTls(host=self.host, port=self.port)
                else:
                    self.conn = MailBoxUnencrypted(host=self.host, port=self.port)
            except (gaierror, SSLError) as _e:
                error = 'IMAP Host ' + self.host + ' on port ' + self.port + ' is unreachable : ' + str(_e)
                print(error)
                self.send_notif(error, 'de la connexion IMAP')
                sys.exit()

            try:
                if self.auth_method == 'basic':
                    self.conn.login(self.login, self.pwd)
                elif self.auth_method == 'oauth':
                    result = self.generate_oauth_token()
                    self.conn.client.authenticate("XOAUTH2",
                                                  lambda x: self.generate_auth_string(result['access_token']).encode(
                                                      "utf-8"))

            except IMAP4_SSL.error as err:
                error = 'Authentication method : ' + self.auth_method + ' - Error while trying to login to ' \
                        + self.host + ' using ' + self.login + ' : ' + str(err)
                print(error)
                self.send_notif(error, 'de l\'authentification IMAP')
                sys.exit()

    def check_if_folder_exist(self, folder):
        """
        Check if a folder exist into the IMAP mailbox

        :param folder: Folder to check
        :return: Boolean
        """

        if self.auth_method == 'exchange':
            for _f in self.conn.root.walk():
                if folder == _f.name:
                    return True
        else:
            folders = self.conn.folder.list()
            for _f in folders:
                if folder == _f.name:
                    return True
        return False

    def select_folder(self, folder):
        """
        Select a folder to find mail into

        :param folder: Folder to select
        """
        if self.auth_method != 'exchange':
            self.conn.folder.set(folder)

    def retrieve_message(self, folder_to_crawl):
        """
        Retrieve all the messages into the selected mailbox

        :return: list of mails
        """

        emails = []
        if self.auth_method == 'exchange':
            for _f in self.conn.root.walk():
                if folder_to_crawl == _f.name:
                    for mail in _f.all().order_by('-datetime_received'):
                        emails.append(mail)
        else:
            for mail in self.conn.fetch():
                emails.append(mail)
        return emails

    def construct_dict_before_send_to_mem(self, msg, cfg, backup_path, log):
        """
        Construct a dict with all the data of a mail (body and attachments)

        :param msg: Mailbox object containing all the data of mail
        :param cfg: Config Object
        :param backup_path: Path to backup of the e-mail
        :param log: Log object
        :return: dict of Args and file path
        """

        if self.auth_method == 'exchange':
            msg_id = str(msg.conversation_id.id)
            from_val = msg.sender.name + ' <' + msg.sender.email_address + '>'
            to_values = [msg.received_by] if not isinstance(msg.received_by, list) else msg.received_by
            try:
                cc_values = [msg.cc_recipients] if not isinstance(msg.cc_recipients, list) else msg.cc_recipients
            except AttributeError:
                cc_values = []

            try:
                reply_to_values = [msg.reply_to_item] if not isinstance(msg.reply_to_item, list) else msg.reply_to_item
            except AttributeError:
                reply_to_values = []
            document_date = msg.datetime_created
        else:
            msg_id = msg.uid
            document_date = msg.date
            cc_values = msg.cc_values
            to_values = msg.to_values
            from_val = msg.from_values.full
            reply_to_values = msg.reply_to_values

        to_str, cc_str, reply_to = ('', '', '')
        try:
            for to in to_values:
                if self.auth_method == 'exchange':
                    to_str += to.name + ' <' + to.email_address + '>;'
                else:
                    to_str += to.full + ';'
        except (TypeError, AttributeError):
            pass

        try:
            for cc in cc_values:
                if self.auth_method == 'exchange':
                    cc_str += cc.name + ' <' + cc.email_address + '>;'
                else:
                    cc_str += cc.full + ';'
        except (TypeError, AttributeError):
            pass

        try:
            for rp_to in reply_to_values:
                if self.auth_method == 'exchange':
                    reply_to += rp_to.name + ' <' + rp_to.email_address + '>;'
                else:
                    reply_to += rp_to.full + ';'
        except (TypeError, AttributeError):
            pass

        if self.auth_method != 'exchange' and len(msg.html) == 0:
            file_format = 'txt'
            file = backup_path + '/mail_' + msg_id + '/mail_origin/body.txt'
        else:
            file_format = 'html'
            file = backup_path + '/mail_' + msg_id + '/mail_origin/body.html'

        data = {
            'mail': {
                'file': file,
                'priority': cfg['priority'],
                'status': cfg['status'],
                'chrono': True if cfg['generate_chrono'] == 'True' else '',
                'doctype': cfg['doctype'],
                'modelId': cfg['model_id'],
                'format': file_format,
                'typist': cfg['typist'],
                'subject': msg.subject,
                'destination': cfg['destination'],
                'documentDate': str(document_date),
                'from': from_val,
                'customFields': {},
            },
            'attachments': []
        }

        from_is_reply_to = str2bool(cfg['from_is_reply_to'])
        if from_is_reply_to and len(reply_to_values) > 0:
            data['mail']['from'] = reply_to_values[0].email
        else:
            data['mail']['from'] = from_val

        # Add custom if specified
        if cfg.get('custom_mail_from') not in [None, ''] and self.check_custom_field(cfg['custom_mail_from'], log):
            data['mail']['customFields'].update({
                cfg['custom_mail_from']: from_val
            })

        if cfg.get('custom_mail_to') not in [None, ''] and to_str != '' and self.check_custom_field(
                cfg['custom_mail_to'], log):
            data['mail']['customFields'].update({
                cfg['custom_mail_to']: to_str[:-1]
            })

        if cfg.get('custom_mail_cc') not in [None, ''] and cc_str != '' and self.check_custom_field(
                cfg['custom_mail_cc'], log):
            data['mail']['customFields'].update({
                cfg['custom_mail_cc']: cc_str[:-1]
            })

        if cfg.get('custom_mail_reply_to') not in [None, ''] and reply_to != '' and self.check_custom_field(
                cfg['custom_mail_reply_to'], log):
            data['mail']['customFields'].update({
                cfg['custom_mail_reply_to']: reply_to[:-1]
            })

        attachment_content_id_in_html = None
        attachments = self.retrieve_attachment(msg)
        attachments_path = backup_path + '/mail_' + msg_id + '/attachments/'
        for pj in attachments:
            if pj['format'] is None:
                log.error(f"Attachment {pj['filename']} doesn't have extension, skipping it")
                continue

            if (os.path.isfile(file) or file) and file_format == 'html':
                with open(file, 'r', encoding='UTF-8') as f:
                    html_content = f.read()
                    attachment_content_id_in_html = re.search(r'src="cid:\s*' + re.escape(pj['content_id']), html_content)
                    if attachment_content_id_in_html:
                        updated_html = re.sub(r'src="cid:\s*' + re.escape(pj['content_id']),
                                              f"src='data:image/{pj['format'].replace('.', '')};"
                                              f"base64, {base64.b64encode(pj['content']).decode('UTF-8')}'",
                                              html_content)

                        with open(file, 'w', encoding='UTF-8') as new_file:
                            new_file.write(updated_html)
                            new_file.close()

            if not attachment_content_id_in_html:
                path = attachments_path + sanitize_filename(pj['filename']) + pj['format']
                if not os.path.isfile(path):
                    pj['format'] = '.txt'
                    with open(path, 'w', encoding='UTF-8') as f:
                        f.write('Erreur lors de la remontée de cette pièce jointe')
                        f.close()

                data['attachments'].append({
                    'status': 'TRA',
                    'collId': 'letterbox_coll',
                    'table': 'res_attachments',
                    'subject': pj['filename'] + pj['format'],
                    'filename': sanitize_filename(pj['filename']),
                    'format': pj['format'][1:],
                    'file': path,
                })
        return data, file

    def backup_email(self, msg, backup_path, force_utf8, log):
        """
        Backup e-mail into path before send it to MEM Courrier

        :param force_utf8: Force HTML UTF-8 encoding
        :param msg: Mail data
        :param backup_path: Backup path
        :param log: Log class instance
        :return: Boolean
        """
        # Backup mail
        if self.auth_method == 'exchange':
            msg_id = str(msg.conversation_id.id)
            html_body = msg.body
        else:
            msg_id = str(msg.uid)
            html_body = msg.html

        primary_mail_path = backup_path + '/mail_' + msg_id + '/mail_origin/'
        os.makedirs(primary_mail_path)

        # Start with headers
        if msg.headers is not None:
            with open(primary_mail_path + 'header.txt', 'w', encoding='UTF-8') as fp:
                for header in msg.headers:
                    if self.auth_method == 'exchange':
                        header_name = header.name
                        header_value = header.value
                    else:
                        header_name = header
                        header_value = msg.headers[header][0]

                    try:
                        fp.write(header_name + ' : ' + header_value + '\n')
                    except UnicodeEncodeError:
                        fp.write(header_name + ' : ' + header_value.encode('utf-8', 'surrogateescape')
                                 .decode('utf-8', 'replace') + '\n')
                fp.close()

        # Then body
        if self.auth_method != 'exchange' and len(msg.html) == 0:
            with open(primary_mail_path + 'body.txt', 'w', encoding='UTF-8') as fp:
                if len(msg.text) != 0:
                    fp.write(msg.text)
                else:
                    fp.write(' ')
        else:
            with open(primary_mail_path + 'body.html', 'w', encoding='UTF-8') as fp:
                if force_utf8:
                    utf_8_charset = '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
                    if (not re.search(utf_8_charset.lower(), html_body.lower()) or
                            re.search(utf_8_charset.lower() + '\s*-->', html_body.lower()) or
                            re.search('<!--\s*' + utf_8_charset.lower(), html_body.lower())):
                        fp.write(utf_8_charset)
                        fp.write('\n')
                fp.write(html_body)
            fp.close()

        if self.auth_method != 'exchange':
            # For safety, backup original stream retrieve from IMAP directly
            with open(primary_mail_path + 'orig.txt', 'w', encoding='UTF-8') as fp:
                for payload in msg.obj.get_payload():
                    try:
                        fp.write(str(payload))
                    except KeyError:
                        break
                fp.close()

        # Backup attachments
        attachments = self.retrieve_attachment(msg)

        if len(attachments) > 0:
            attachment_path = backup_path + '/mail_' + msg_id + '/attachments/'
            os.mkdir(attachment_path)
            for file in attachments:
                if file['format'] is None:
                    log.error(f"Attachment {file['filename']} doesn't have extension, skipping it")
                    continue

                file_path = os.path.join(attachment_path + sanitize_filename(file['filename']) + file['format'])
                if not os.path.isfile(file_path) and file['format'] and not os.path.isdir(file_path):
                    with open(file_path, 'wb') as fp:
                        fp.write(file['content'])
        return True

    def move_to_destination_folder(self, msg, destination, log):
        """
        Move e-mail to selected destination IMAP folder (if action is set to move)

        :param log: Log class instance
        :param msg: Mail data
        :param destination: IMAP folder destination
        :return: Boolean
        """
        if self.auth_method == 'exchange':
            for _f in self.conn.root.walk():
                if destination == _f.name:
                    msg.move(_f)
        else:
            try:
                self.conn.move(msg.uid, destination)
                return True
            except utils.UnexpectedCommandStatusError as e:
                log.error('Error while moving mail to ' + destination + ' folder : ' + str(e))
                pass

    def delete_mail(self, msg, trash_folder, log):
        """
        Move e-mail to trash IMAP folder (if action is set to delete) if specified. Else, delete it (can't be retrieved)

        :param log: Log class instance
        :param msg: Mail Data
        :param trash_folder: IMAP trash folder
        """
        if self.auth_method == 'exchange':
            folder_found = False
            for _f in self.conn.root.walk():
                if trash_folder == _f.name:
                    msg.move(_f)
                    folder_found = True
            if not folder_found:
                msg.move_to_trash()
        else:
            try:
                if not self.check_if_folder_exist(trash_folder):
                    log.info('Trash folder (' + trash_folder + ') doesnt exist, delete mail (couldn\'t be retrieve)')
                    self.conn.delete(msg.uid)
                else:
                    self.move_to_destination_folder(msg, trash_folder, log)
            except utils.UnexpectedCommandStatusError as e:
                log.error('Error while deleting mail : ' + str(e))
                pass

    @staticmethod
    def retrieve_attachment(msg):
        """
        Retrieve all attachments from a given mail

        :param msg: Mail Data
        :return: List of all the attachments for a mail
        """
        args = []
        for att in msg.attachments:
            if isinstance(att, FileAttachment):
                args.append({
                    'filename': os.path.splitext(att.name.replace(' ', '_'))[0],
                    'format': os.path.splitext(att.name)[1],
                    'content': att.content,
                    'mime_type': att.content_type
                })
            else:
                if att.filename == 'winmail.dat':
                    mime_type = ''
                    winmail = TNEF(att.payload, do_checksum=True)
                    for att in winmail.attachments:
                        for attr in att.mapi_attrs:
                            if attr.attr_type == 30 and attr.name == 14094:
                                mime_type = attr.raw_data[0]
                        file_format = os.path.splitext(att.name)[1]
                        args.append({
                            'filename': os.path.splitext(att.name)[0].replace(' ', '_'),
                            'format': file_format,
                            'content': att.data,
                            'mime_type': mime_type
                        })
                else:
                    file_format = os.path.splitext(att.filename)[1]
                    if not att.filename and not file_format:
                        continue
                    elif not file_format or file_format in ['.']:
                        file_format = mimetypes.guess_extension(att.content_type, strict=False)

                    args.append({
                        'filename': os.path.splitext(att.filename)[0].replace(' ', '_'),
                        'format': file_format,
                        'content': att.payload,
                        'content_id': att.content_id,
                        'mime_type': att.content_type
                    })
        return args

    def check_custom_field(self, field, log):
        list_of_custom = self.ws.retrieve_custom_fields()
        for custom in list_of_custom['customFields']:
            if int(field) == int(custom['id']):
                return True
        log.error('The following custom field doesn\'t exist in MEM Courrier database : ' + field)
        return False


def move_batch_to_error(batch_path, error_path, smtp, process, msg, res):
    """
    If error in batch process, move the batch folder into error folder

    :param res: return of MEM Courrier WS
    :param process: Process name
    :param msg: Contain the msg metadata
    :param smtp: instance of SMTP class
    :param batch_path: Path to the actual batch
    :param error_path: path to the error path
    """
    try:
        os.makedirs(error_path)
    except FileExistsError:
        pass

    try:
        shutil.move(batch_path, error_path)
        if smtp.enabled is not False:
            error = ''
            if res:
                try:
                    error = json.loads(res)['errors']
                except ValueError:
                    error = res
            smtp.send_email(
                message='    - Nom du batch : ' + os.path.basename(batch_path) + '/ \n' +
                        '    - Nom du process : ' + process + '\n' +
                        '    - Chemin vers le batch en erreur : _ERROR/' + process + '/' + os.path.basename(
                    error_path) + '/' + os.path.basename(batch_path) + ' \n' +
                        '    - Sujet du mail : ' + msg['subject'] + '\n' +
                        '    - Date du mail : ' + msg['date'] + '\n' +
                        '    - UID du mail : ' + msg['uid'] + '\n' +
                        '\n\n'
                        '    - Informations sur l\'erreur : ' + error + '\n',
                step='du traitement du mail suivant')
    except (FileNotFoundError, FileExistsError, shutil.Error):
        pass


def send_email_error_pj(batch_path, process, msg, res, smtp, attachment):
    if smtp.enabled is not False:
        error = ''
        if res:
            error = str(json.loads(res)['errors'])
        smtp.send_email(
            message='    - Nom du batch : ' + os.path.basename(batch_path) + '/ \n' +
                    '    - Nom du process : ' + process + '\n' +
                    '    - Sujet du mail : ' + msg['subject'] + '\n' +
                    '    - Sujet de la pièce jointe : ' + attachment['subject'] + '\n' +
                    '    - Date du mail : ' + msg['date'] + '\n' +
                    '    - UID du mail : ' + msg['uid'] + '\n' +
                    '\n\n'
                    '    - Informations sur l\'erreur générée par la pièce jointe : ' + error + '\n',
            step='du traitement du mail suivant')


def str2bool(value):
    """
    Function to convert string to boolean

    :return: Boolean
    """
    return value.lower() in "true"


def sanitize_filename(s):
    def safe_char(c):
        if c.isalnum():
            return c
        else:
            return "_"

    return "".join(safe_char(c) for c in s).rstrip("_")
