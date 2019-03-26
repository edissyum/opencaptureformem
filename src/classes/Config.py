from configparser import ConfigParser, ExtendedInterpolation

class Config:
    def __init__(self, path):
        self.cfg = {}
        # ExtendedInterpolation is needed to use var into the config.ini file
        parser = ConfigParser(interpolation=ExtendedInterpolation())
        parser.read(path)
        for section in parser.sections():
            self.cfg[section] = {}
            for info in parser[section]:
                self.cfg[section][info] = parser[section][info]
