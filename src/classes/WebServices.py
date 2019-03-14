from requests.auth import HTTPBasicAuth
import requests
import json
import base64
import sys

class WebServices:
    def __init__(self, host, user, pwd):
        self.baseUrl    = host
        self.auth       = HTTPBasicAuth(user, pwd)

    def retrieve_contact_by_mail(self, mail):
        res = requests.get(self.baseUrl + 'getContactByMail', auth=self.auth, params={'mail' : mail})
        if res.status_code != 200:
            print('GetContactByMailError : ' + str(res.status_code))
            return False
        else:
            return json.loads(res.text)

    def retrieve_contact_by_url(self, url):
        url = url.replace('http://', '').replace('https://', '').replace('www.', '')
        res = requests.get(self.baseUrl + 'getContactByUrl', auth=self.auth, params={'url': url})

        if res.status_code != 200:
            print('GetContactByUrlError : ' + str(res.status_code))
            return False
        else:
            return json.loads(res.text)

    def insert_with_contact_info(self, file, Config, contact):
        data = {
            'encodedFile'   : base64.b64encode(open(file, 'rb').read()).decode("utf-8"),
            'priority'      : Config.cfg['RESOURCES']['priority'],
            'status'        : Config.cfg['RESOURCES']['status'],
            'type_id'       : Config.cfg['RESOURCES']['type_id'],
            'format'        : Config.cfg['RESOURCES']['format'],
            'category_id'   : Config.cfg['RESOURCES']['category_id'],
            'address_id'    : contact['id'],
            'exp_contact_id': contact['contact_id']
        }
        res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=data)
        if res.status_code != 200:
            print('InsertIntoMaarch : ' + str(res.status_code))
            return False
        else:
            return res.text

