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

from configparser import ConfigParser, ExtendedInterpolation, Error


class Config:
    def __init__(self):
        self.cfg = {}

    def load_file(self, path):
        # ExtendedInterpolation is needed to use var into the config.ini file
        try:
            parser = ConfigParser(interpolation=ExtendedInterpolation())
            parser.read(path)
            for section in parser.sections():
                self.cfg[section] = {}
                for info in parser[section]:
                    self.cfg[section][info] = parser[section][info]
            return True
        except Error as e:
            print('Error while parse .INI file : ' + str(e))
            return False
