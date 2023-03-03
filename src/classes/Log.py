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

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import os
import logging
import logging.handlers
from inspect import getframeinfo, stack


def caller_reader(f):
    """This wrapper updates the context with the callor infos"""
    def wrapper(self, *args):
        caller = getframeinfo(stack()[1][0])
        self._filter.file = os.path.basename(caller.filename)
        self._filter.line_n = caller.lineno
        return f(self, *args)
    return wrapper


class RotatingFileHandlerUmask(logging.handlers.RotatingFileHandler):
    def _open(self):
        prevumask = os.umask(0o000)  # -rw-rw-rw-
        rtv = logging.handlers.RotatingFileHandler._open(self)
        os.umask(prevumask)
        return rtv


class Log:
    def __init__(self, path):
        self.LOGGER = logging.getLogger('Open-Capture')
        if self.LOGGER.hasHandlers():
            self.LOGGER.handlers.clear()  # Clear the handlers to avoid double logs
        log_file = RotatingFileHandlerUmask(path, mode='a', maxBytes=5 * 1024 * 1024, backupCount=2)
        formatter = logging.Formatter('[%(threadName)-14s] [%(file)-22sline %(line_n)-4s] %(asctime)s %(levelname)s %(message)s', datefmt='%d-%m-%Y %H:%M:%S')
        log_file.setFormatter(formatter)
        self.LOGGER.addHandler(log_file)

        self.LOGGER.filters.clear()
        self._filter = CallerFilter()
        self.LOGGER.addFilter(self._filter)
        self.LOGGER.setLevel(logging.DEBUG)

    @caller_reader
    def info(self, msg):
        self.LOGGER.info(msg)

    @caller_reader
    def error(self, msg):
        self.LOGGER.error(msg)


class CallerFilter(logging.Filter):
    """ This class adds some context to the log record instance """
    file = ''
    line_n = ''

    def filter(self, record):
        record.file = self.file
        record.line_n = self.line_n
        return True

