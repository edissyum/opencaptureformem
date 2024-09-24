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

# @dev : Nathan CHEVAL <nathan.cheval@edissyum.com>

import sys
import requests

graphql_args = {
    "get_token_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
    "users_url": "https://graph.microsoft.com/v1.0/users",
    "scope": "https://graph.microsoft.com/.default",
    "grant_type": "client_credentials",
    "tenant_id": "",
    "client_id": "",
    "client_secret": "",
    "login": "",
}


def generate_graphql_access_token(data):
    get_token_url = data['get_token_url'].replace('{tenant_id}', data['tenant_id'])
    return graphql_request(get_token_url, 'POST', data, [])


def graphql_request(url, method, data, headers):
    if method == 'GET':
        return requests.get(url, headers=headers, timeout=30)

    if method == 'POST':
        return requests.post(url, data=data, headers=headers, timeout=30)


if __name__ == "__main__":
    access_token = generate_graphql_access_token(graphql_args)
    if access_token.status_code != 200:
        ERROR = 'Error while trying to get access token from GraphQL API : ' + str(access_token.text)
        print(ERROR)
        sys.exit()

    graphql_headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + access_token.json()['access_token']
    }
    users_list = graphql_request(graphql_args['users_url'], 'GET', None, graphql_headers)
    if users_list.status_code != 200:
        ERROR = 'Error while trying to get users list from GraphQL API : ' + str(users_list.text)
        print(ERROR)
        sys.exit()

    for user in users_list.json()['value']:
        if user['mail'] == graphql_args['login']:
            graphql_user = user

    if graphql_user is None:
        ERROR = 'User ' + graphql_args['login'] + ' not found in the list of users from GraphQL API'
        print(ERROR)

    # Now we can list the folders of the user
    folders_url = graphql_args['users_url'] + '/' + graphql_user['id'] + '/mailFolders'
    folders_list = graphql_request(folders_url, 'GET', None, graphql_headers)
    if folders_list.status_code != 200:
        ERROR = 'Error while trying to get folders list from GraphQL API : ' + str(folders_list.text)
        print(ERROR)
        sys.exit()

    for folder in folders_list.json()['value']:
        if folder['childFolderCount'] and folder['childFolderCount'] > 0:
            subfolders_url = folders_url + '/' + folder['id'] + '/childFolders'
            subfolders_list = graphql_request(subfolders_url, 'GET', None, graphql_headers)
            if subfolders_list.status_code != 200:
                ERROR = 'Error while trying to get subfolders list from GraphQL API : ' + str(subfolders_list.text)
                print(ERROR)
                sys.exit()

            for subfolder in subfolders_list.json()['value']:
                print(folder['displayName'] + '/' + subfolder['displayName'])
        else:
            print(folder['displayName'])