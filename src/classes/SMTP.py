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
import pathlib
import sys

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class SMTP:
    def __init__(self, enabled, host, port, login, pwd, ssl, starttls, dest_mail, delay, auth, from_mail):
        self.enabled = str2bool(enabled)
        self.pwd = pwd
        self.conn = None
        self.port = port
        self.host = host
        self.login = login
        self.ssl = str2bool(ssl)
        self.auth = str2bool(auth)
        self.dest_mail = dest_mail
        self.from_mail = from_mail
        self.starttls = str2bool(starttls)
        self.isUp = False
        self.delay = int(delay)

        if self.enabled:
            self.test_connection()

    def test_connection(self):
        """
        Test the connection to the SMTP server

        """
        if self.ssl:
            try:
                self.conn = smtplib.SMTP_SSL(self.host, self.port)
                self.conn.ehlo()
                if self.starttls:
                    self.conn.starttls()
                    self.conn.ehlo()
            except (smtplib.SMTPException, OSError) as e:
                print('SMTP Host ' + self.host + ' on port ' + self.port + ' is unreachable : ' + str(e))
                sys.exit()
        else:
            try:
                self.conn = smtplib.SMTP(self.host, self.port)
                self.conn.ehlo()
                if self.starttls:
                    self.conn.starttls()
                    self.conn.ehlo()
            except (smtplib.SMTPException, OSError) as e:
                print('SMTP Host ' + self.host + ' on port ' + self.port + ' is unreachable : ' + str(e))
                sys.exit()
        try:
            if self.auth:
                self.conn.login(self.login, self.pwd)
        except (smtplib.SMTPException, OSError) as err:
            print('Error while trying to login to ' + self.host + ' using ' + self.login + '/' + self.pwd + ' as login/password : ' + str(err))
            sys.exit()

        self.isUp = True

    def send_email(self, message, step):
        """
        Send email with the error message coming from MailCollect, IMAP connector

        :param message: Message to send
        :param step: str with the specified step where the error was throw
        """
        file = 'last_mail.lock'
        diff_minutes = False
        if os.path.exists(file) and pathlib.Path(file).stat().st_size != 0:
            f = open(file, 'r')
            last_mail_send = datetime.strptime(f.read(), '%d/%m/%Y %H:%M')
            f.close()

            now = datetime.strptime(datetime.now().strftime('%d/%m/%Y %H:%M'), '%d/%m/%Y %H:%M')
            diff = now - last_mail_send
            diff_minutes = (diff.days * 1440 + diff.seconds / 60)

        msg = MIMEMultipart()
        msg['To'] = self.dest_mail
        if self.from_mail:
            msg['From'] = self.from_mail
        msg['Subject'] = '[MailCollect] Erreur lors de la capture IMAP'
        message = 'Une erreur est arrivée lors ' + step + ' : \n' + message
        if self.delay != 0:
            message += '\n\n Attention, durant les ' + str(self.delay) + ' dernières minutes, d\'autres erreurs ont pu arriver sans notifications.'

        msg.attach(MIMEText(message))

        try:
            if diff_minutes is not False and self.delay != 0 and diff_minutes < self.delay:
                pass
            else:
                self.conn.sendmail(from_addr='MailCollect@opencapture.com', to_addrs=self.dest_mail, msg=msg.as_string())
                f = open(file, 'w')
                f.write(datetime.now().strftime('%d/%m/%Y %H:%M'))
                f.close()
        except smtplib.SMTPException as e:
            print('Erreur lors de l\'envoi du mail : ' + str(e))


def str2bool(value):
    """
    Function to convert string to boolean

    :return: Boolean
    """
    return value.lower() in "true"
