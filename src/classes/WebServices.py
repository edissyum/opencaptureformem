from requests.auth import HTTPBasicAuth
import requests

class WebServices:
    def __init__(self, host, user, pwd):
        self.baseUrl    = host
        self.auth       = HTTPBasicAuth(user, pwd)

    def retrieveContactByMail(self, mail):
        res = requests.get(self.baseUrl + 'getContactByMail', auth=self.auth, params={'mail' : mail})
        print(res.text)