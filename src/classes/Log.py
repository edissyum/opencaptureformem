# This file is part of Open-Capture.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import logging
from logging.handlers import RotatingFileHandler

class Log:
    def __init__(self, path):
        self.LOGGER = logging.getLogger('Open-Capture')
        if self.LOGGER.hasHandlers():
            self.LOGGER.handlers.clear() # Clear the handlers to avoid double logs
        self.logFile = RotatingFileHandler(path, mode='a', maxBytes=5 * 1024 * 1024,
                            backupCount=2, encoding=None, delay=0)
        formatter = logging.Formatter('[%(threadName)-14s] [%(filename)s:%(lineno)-15s] %(asctime)s %(levelname)s %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
        self.logFile.setFormatter(formatter)
        self.LOGGER.addHandler(self.logFile)
        self.LOGGER.setLevel(logging.DEBUG)

    def info(self, msg, filename, lineno):
        self.logFile.setFormatter(logging.Formatter('[%(threadName)-14s] [%(customFilename)-15sline %(customLineNumber)-4s] %(asctime)s %(levelname)s %(message)s', datefmt='%d-%m-%Y %H:%M:%S'))
        self.LOGGER.info(msg, extra={'customFilename': filename, 'customLineNumber' : lineno})

    def error(self, msg,filename, lineno):
        self.logFile.setFormatter(logging.Formatter('[%(threadName)-14s] [%(customFilename)-15sline %(customLineNumber)-4s] %(asctime)s %(levelname)s %(message)s', datefmt='%d-%m-%Y %H:%M:%S'))
        self.LOGGER.error(msg, extra={'customFilename': filename, 'customLineNumber' : lineno})
