import logging

class Log:
    def __init__(self, path):
        self.path   = path
        self.LOGGER = logging.getLogger('ContestBot')
        logFile = logging.FileHandler(path)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        logFile.setFormatter(formatter)
        self.LOGGER.addHandler(logFile)
        self.LOGGER.setLevel(logging.DEBUG)

    def info(self, msg):
        self.LOGGER.info(msg)

    def error(self, msg):
        self.LOGGER.error(msg)