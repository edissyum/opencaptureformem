from requests.auth import HTTPBasicAuth
import requests
import json
import base64
import sys

class WebServices:
    def __init__(self, host, user, pwd, Log):
        self.baseUrl    = host
        self.auth       = HTTPBasicAuth(user, pwd)
        self.Log        = Log

    def retrieve_contact_by_mail(self, mail):
        res = requests.get(self.baseUrl + 'getContactByMail', auth=self.auth, params={'mail' : mail})
        if res.status_code != 200:
            self.Log.error('GetContactByMailError : ' + str(res.status_code))
            return False
        else:
            return json.loads(res.text)

    def retrieve_contact_by_url(self, url):
        url = url.replace('http://', '').replace('https://', '').replace('www.', '')
        res = requests.get(self.baseUrl + 'getContactByUrl', auth=self.auth, params={'url': url})

        if res.status_code != 200:
            self.Log.error('GetContactByUrlError : ' + str(res.status_code))
            return False
        else:
            return json.loads(res.text)

    def insert_with_args(self, fileContent, Config, contact, subject, date, destination):
        if not contact:
            contact = {'id' : '', 'contact_id' : ''}
        data = {
            #'encodedFile'   : base64.b64encode(open(file, 'rb').read()).decode("utf-8"),
            'encodedFile'   : base64.b64encode(fileContent),
            #'encodedFile'   : "dGVzdA==",
            'priority'      : Config.cfg['OCForMaarch']['priority'],
            'status'        : Config.cfg['OCForMaarch']['status'],
            'type_id'       : Config.cfg['OCForMaarch']['type_id'],
            'format'        : Config.cfg['OCForMaarch']['format'],
            'category_id'   : Config.cfg['OCForMaarch']['category_id'],
            'subject'       : subject,
            'destination'   : destination,
            'address_id'    : contact['id'],
            'exp_contact_id': contact['contact_id'],
            'doc_date'      : date
        }

        res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=data)
        print(res, res.text, res.content)
        if res.status_code != 200:
            self.Log.error('InsertIntoMaarch : ' + str(res.status_code) + ' : ' + str(res.text))
            return False
        else:
            return res.text

