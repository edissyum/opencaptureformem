# This file is part of OpenCapture.

# OpenCapture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OpenCapture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with OpenCapture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import logging
from logging.handlers import RotatingFileHandler

class Log:
    def __init__(self, path):
        self.LOGGER = logging.getLogger('OpenCapture')
        if self.LOGGER.hasHandlers():
            self.LOGGER.handlers.clear() # Clear the handlers to avoid double logs
        logFile = RotatingFileHandler(path, mode='a', maxBytes=5 * 1024 * 1024,
                            backupCount=2, encoding=None, delay=0)
        formatter = logging.Formatter('[%(threadName)-14s] %(asctime)s %(levelname)s %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
        logFile.setFormatter(formatter)
        self.LOGGER.addHandler(logFile)
        self.LOGGER.setLevel(logging.DEBUG)

    def info(self, msg):
        self.LOGGER.info(msg)

    def error(self, msg):
        self.LOGGER.error(msg)
