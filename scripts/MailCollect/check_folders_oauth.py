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

# @dev : Oussama BRICH <oussama.brich@edissyum.com>

from imap_tools import MailBox
import msal

args = {
    "authority": "https://login.microsoftonline.com/",
    "scopes": ["https://outlook.office365.com/.default"],
    "tenant_id": "",
    "client_id": "",
    "secret": "",
    "host": "outlook.office365.com",
    "login": "",
}


def generate_auth_string(user, token):
    return f"user={user}\x01auth=Bearer {token}\x01\x01"


if __name__ == "__main__":
    app = msal.ConfidentialClientApplication(args['client_id'], authority=args['authority'] + args['tenant_id'],
                                             client_credential=args['secret'])

    result = app.acquire_token_silent(args['scopes'], account=None)

    if not result:
        print("No suitable token in cache.  Get new one.")
        result = app.acquire_token_for_client(scopes=args['scopes'])

    if "access_token" in result:
        print("Token generated with success.\n")
    else:
        print(result.get("error"))
        print(result.get("error_description"))
        print(result.get("correlation_id"))

    mailbox = MailBox(args['host'])
    mailbox.client.authenticate("XOAUTH2",
                                lambda x: generate_auth_string(args['login'], result['access_token'])
                                .encode("utf-8"))
    folders = mailbox.folder.list()
    for f in folders:
        print(f.name)
