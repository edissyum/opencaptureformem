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
import smtplib
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.classes.SMTP import SMTP

hostname = 'smtp.gmail.com'
port = 587
isSSL = 'False'
isSTARTLS = 'True'
login = ''
password = ''
mail_dest = ''
mail_from = ''

SMTP = SMTP('True', hostname, port, login, password, isSSL, isSTARTLS, mail_dest, 0, 'True', mail_from)

if SMTP.isUp:
    msg = MIMEMultipart()
    msg['To'] = mail_dest
    msg['Subject'] = "[MailCollect] Test d'envoi de mail"
    message = "Test d'envoi d'un mail depuis MailCollect"
    msg.attach(MIMEText(message))
    try:
        SMTP.conn.sendmail(from_addr='MailCollect', to_addrs=mail_dest, msg=msg.as_string())
        print('E-mail sent without errors')
    except smtplib.SMTPException as e:
        print('Error while sending e-mail test : ' + str(e))
