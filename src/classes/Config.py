import configparser

class Config:
    def __init__(self, path):
        self.cfg = {}
        xml = configparser.ConfigParser()
        xml.read(path)
        for section in xml.sections():
            self.cfg[section] = {}
            for info in xml[section]:
                self.cfg[section][info] = xml[section][info]
