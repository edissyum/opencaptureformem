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
import mimetypes
import os
import re
import sys
import shutil
import msal # AMO01 OAUTH 19.04

from socket import gaierror
from imap_tools import utils, MailBox, MailBoxUnencrypted
from imaplib import IMAP4_SSL


class Mail:
    def __init__(self, auth_method, oauth, host, port, login, pwd, ws, smtp): # AMO01 OAUTH 19.04
        self.auth_method = auth_method # AMO01 OAUTH 19.04
        self.oauth = oauth # AMO01 OAUTH 19.04
        self.pwd = pwd
        self.conn = None
        self.port = port
        self.host = host
        self.login = login
        self.SMTP = smtp

    def send_notif(self, msg, step):
        if self.SMTP.isUp:
            self.SMTP.send_email(message=msg, step=step)

    # AMO01 OAUTH 19.04
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

    # END AMO01 OAUTH 19.04

    def test_connection(self, secured_connection):
        """
        Test the connection to the IMAP server
        :param secured_connection: boolean
        :param log: Log object
        """
        try:
            if secured_connection:
                self.conn = MailBox(host=self.host, port=self.port)
            else:
                self.conn = MailBoxUnencrypted(host=self.host, port=self.port)

        except gaierror as e:
            error = 'IMAP Host ' + self.host + ' on port ' + self.port + ' is unreachable : ' + str(e)
            print(error)
            self.send_notif(error, 'de la connexion IMAP')
            sys.exit()

        try:
            # AMO01 OAUTH 19.04
            print(self.auth_method)
            if self.auth_method == 'basic':
                self.conn.login(self.login, self.pwd)
            elif self.auth_method == 'oauth':
                result = self.generate_oauth_token()
                self.conn.client.authenticate("XOAUTH2", lambda x: self.generate_auth_string(result['access_token']).encode("utf-8"))
            # END AMO01 OAUTH 19.04

        except IMAP4_SSL.error as err:
            # AMO01 OAUTH 19.04
           error = 'Authentication method : ' + self.auth_method + ' - Error while trying to login to ' \
                                   + self.host + ' using ' + self.login + ' : ' + str(err)
           print(error)
           self.send_notif(error, 'de l\'authentification IMAP')
           sys.exit()
           # END AMO01 OAUTH 19.04

    def check_if_folder_exist(self, folder):
        """
        Check if a folder exist into the IMAP mailbox
        :param folder: Folder to check
        :return: Boolean
        """
        folders = self.conn.folder.list()
        for f in folders:
            if folder == f.name: # AMO01 OAUTH 19.04
                return True
        return False

    def select_folder(self, folder):
        """
        Select a folder to find mail into
        :param folder: Folder to select
        """
        self.conn.folder.set(folder)

    def retrieve_message(self):
        """
        Retrieve all the messages into the selected mailbox
        :return: list of mails
        """
        emails = []
        for mail in self.conn.fetch():
            emails.append(mail)
        return emails

    def construct_dict_before_send_to_maarch(self, msg, cfg, backup_path):
        """
        Construct a dict with all the data of a mail (body and attachments)
        :param msg: Mailbox object containing all the data of mail
        :param cfg: Config Object
        :param backup_path: Path to backup of the e-mail
        :return: dict of Args and file path
        """
        to_str, cc_str, reply_to = ('', '', '')
        try:
            for to in msg.to_values:
                to_str += to['full'] + ';'
        except TypeError:
            pass

        try:
            for cc in msg.cc_values:
                cc_str += cc['full'] + ';'
        except TypeError:
            pass

        try:
            for rp_to in msg.reply_to_values:
                reply_to += rp_to['full'] + ';'
        except TypeError:
            pass

        if len(msg.html) == 0:
            file_format = 'txt'
            file = backup_path + '/mail_' + str(msg.uid) + '/mail_origin/body.txt'
        else:
            file_format = 'html'
            file = backup_path + '/mail_' + str(msg.uid) + '/mail_origin/body.html'

        data = {
            'mail': {
                'file': file,
                'priority': cfg['priority'],
                'status': cfg['status'],
                'type_id': cfg['type_id'],
                'category_id': cfg['category_id'],
                'format': file_format,
                'typist': cfg['typist'],
                'subject': msg.subject,
                'destination': cfg['destination'],
                'doc_date': str(msg.date),
                'from': msg.from_,
            },
            'attachments': []
        }

        from_is_reply_to = str2bool(cfg['from_is_reply_to'])
        if from_is_reply_to and len(msg.reply_to) > 0:
            data['mail']['from'] = msg.reply_to[0]
        else:
            data['mail']['from'] = msg.from_

        # Add custom if specified
        if cfg.get('custom_mail_from') not in [None, '']:
            data['mail'][cfg['custom_mail_from']] = msg.from_values.email # AMO01 OAUTH 19.04

        if cfg.get('custom_mail_to') not in [None, ''] and to_str != '':# AMO01 OAUTH 19.04
            data['mail'][cfg['custom_mail_to']] = to_str[:-1][:254]  # 254 to avoid too long string (maarch custom is limited to 255 char)

        if cfg.get('custom_mail_cc') not in [None, ''] and cc_str != '': # AMO01 OAUTH 19.04
            data['mail'][cfg['custom_mail_cc']] = cc_str[:-1][:254]  # 254 to avoid too long string (maarch custom is limited to 255 char)

        if cfg.get('custom_mail_reply_to') not in [None, ''] and reply_to != '': # AMO01 OAUTH 19.04
            data['mail'][cfg['custom_mail_reply_to']] = reply_to[:-1][:254]  # 254 to avoid too long string (maarch custom is limited to 255 char)

        attachments = self.retrieve_attachment(msg)
        attachments_path = backup_path + '/mail_' + str(msg.uid) + '/attachments/'
        for pj in attachments:
            path = attachments_path + pj['filename'] + pj['format']
            if not os.path.isfile(path):
                pj['format'] = '.txt'
                f = open(attachments_path + pj['filename'] + pj['format'], 'w')
                f.write('Erreur lors de la remontée de cette pièce jointe')
                f.close()

            data['attachments'].append({
                'status': 'TRA',
                'collId': 'letterbox_coll',
                'table': 'res_attachments',
                'subject': pj['filename'] + pj['format'],
                'filename': pj['filename'],
                'format': pj['format'][1:],
                'file': attachments_path + pj['filename'] + pj['format'],
            })

        return data, file

    def backup_email(self, msg, backup_path, force_utf8):
        """
        Backup e-mail into path before send it to Maarch
        :param msg: Mail data
        :param backup_path: Backup path
        :return: Boolean
        """
        # Backup mail
        primary_mail_path = backup_path + '/mail_' + str(msg.uid) + '/mail_origin/'
        os.makedirs(primary_mail_path)

        # Start with headers
        fp = open(primary_mail_path + 'header.txt', 'w')
        for header in msg.headers:
            try:
                fp.write(header + ' : ' + msg.headers[header][0] + '\n')
            except UnicodeEncodeError:
                fp.write(header + ' : ' + msg.headers[header][0].encode('utf-8', 'surrogateescape').decode('utf-8', 'replace') + '\n')
        fp.close()

        # Then body
        if len(msg.html) == 0:
            fp = open(primary_mail_path + 'body.txt', 'w')
            if len(msg.text) != 0:
                fp.write(msg.text)
            else:
                fp.write(' ')
        else:
            fp = open(primary_mail_path + 'body.html', 'w')
            if force_utf8:
                utf_8_charset = '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">'
                if not re.search(utf_8_charset.lower(), msg.html.lower()):
                    fp.write(utf_8_charset)
                    fp.write('\n')
            fp.write(msg.html)
        fp.close()

        # For safety, backup original stream retrieve from IMAP directly
        fp = open(primary_mail_path + 'orig.txt', 'w')

        for payload in msg.obj.get_payload():
            try:
                fp.write(str(payload))
            except KeyError:
                break

        fp.close()

        # Backup attachments
        attachments = self.retrieve_attachment(msg)
        if len(attachments) > 0:
            attachment_path = backup_path + '/mail_' + str(msg.uid) + '/attachments/'
            os.mkdir(attachment_path)
            for file in attachments:
                file_path = os.path.join(attachment_path + file['filename'] + file['format'])

                if not os.path.isfile(file_path) and file['format'] and not os.path.isdir(file_path):
                    fp = open(file_path, 'wb')
                    fp.write(file['content'])
                    fp.close()
        return True

    def move_to_destination_folder(self, msg, destination, log):
        """
        Move e-mail to selected destination IMAP folder (if action is set to move)
        :param log: Log class instance
        :param msg: Mail data
        :param destination: IMAP folder destination
        :return: Boolean
        """
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
            file_format = os.path.splitext(att.filename)[1]
            if not file_format:
                file_format = mimetypes.guess_extension(att.content_type, strict=False)

            args.append({
                'filename': os.path.splitext(att.filename)[0].replace(' ', '_'),
                'format': file_format,
                'content': att.payload,
                'mime_type': att.content_type
            })
        return args


def move_batch_to_error(batch_path, error_path, smtp, process, msg):
    """
    If error in batch process, move the batch folder into error folder
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
        if smtp is not False:
            smtp.send_email(
                message='    - N° de batch : ' + os.path.basename(batch_path) + '/ \n' +
                        '    - Chemin vers le batch en erreur : _ERROR/' + process + '/' + os.path.basename(error_path) + '/' + os.path.basename(batch_path) + '/ \n' +
                        '    - Nom du process : ' + process + '\n' +
                        '    - Sujet du mail : ' + msg['subject'] + '\n' +
                        '    - Date du mail : ' + msg['date'] + '\n' +
                        '    - UID du mail : ' + msg['uid'] + '\n',
                step='du traitement du mail suivant')
    except (FileNotFoundError, FileExistsError, shutil.Error):
        pass



def str2bool(value):
    """
    Function to convert string to boolean
    :return: Boolean
    """
    return value.lower() in "true"
