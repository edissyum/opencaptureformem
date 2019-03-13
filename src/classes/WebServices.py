from requests.auth import HTTPBasicAuth
import requests
import json
import base64

class WebServices:
    def __init__(self, host, user, pwd):
        self.baseUrl    = host
        self.auth       = HTTPBasicAuth(user, pwd)

    def retrieveContactByMail(self, mail):
        res = requests.get(self.baseUrl + 'getContactByMail', auth=self.auth, params={'mail' : mail})
        if res.status_code != 200:
            print('GetContactByMailError : ' + str(res.status_code))
            return False
        else:
            return json.loads(res.text)

    def retrieveContactByUrl(self, url):
        res = requests.get(self.baseUrl + 'getContactByUrl', auth=self.auth, params={'url': url})
        if res.status_code != 200:
            print('GetContactByUrlError : ' + str(res.status_code))
            return False
        else:
            return json.loads(res.text)

    def insert(self, data):
        res = requests.post(self.baseUrl + 'resources', auth=self.auth, data=data)
        if res.status_code != 200:
            print('InsertIntoMaarch : ' + str(res.status_code))
            return False
        else:
            return res.text

