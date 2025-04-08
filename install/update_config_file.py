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
from configparser import RawConfigParser, Error, ConfigParser


def key_exists_in_old_config(section, key, old_config):
    for old_section in old_config.sections():
        if old_section == section:
            for old_info in old_config[old_section]:
                if old_info == key or old_info.lower() == key:
                    return True
    return False


if __name__ == '__main__':
    # This script is used to update the config.ini file with the new default config.ini file
    # It will add new informations and replace camelcase by snakecase

    # Change the path to the config.ini file if needed, to change mail.ini file for example

    OLD_CONFIG_FILE = '/opt/edissyum/opencaptureformem/src/config/config.ini'
    NEW_CONFIG_FILE = '/opt/edissyum/opencaptureformem/src/config/config.ini.default'

    try:
        new_parser = ConfigParser(comment_prefixes="", allow_no_value=True, strict=False)
        new_parser.optionxform = str
        with open(NEW_CONFIG_FILE, 'r', encoding='utf-8') as file:
            new_parser.read_file(file)

        old_parser = ConfigParser(comment_prefixes="", allow_no_value=True, strict=False)
        old_parser.optionxform = str
        with open(OLD_CONFIG_FILE, 'r', encoding='utf-8') as file:
            old_parser.read_file(file)

        # Check if camelcase remain in old config file
        for new_section in new_parser.sections():
            for new_info in new_parser[new_section]:
                if not new_info[0] == ';':
                    if not key_exists_in_old_config(new_section, new_info, old_parser):
                        tmp_info = new_info.split('_')
                        for i in range(1, len(tmp_info)):
                            tmp_info[i] = tmp_info[i].capitalize()
                        tmp_info = ''.join(tmp_info)

                        if key_exists_in_old_config(new_section, tmp_info, old_parser):
                            os.system(f'sed -i "s/{tmp_info}/{new_info}/g" {OLD_CONFIG_FILE}')

            old_parser = RawConfigParser(comment_prefixes="", allow_no_value=True, strict=False)
            old_parser.optionxform = str
            with open(OLD_CONFIG_FILE, 'r', encoding='utf-8') as file:
                old_parser.read_file(file)

            # Check if new informations exists to fill old config file
            for new_section in new_parser.sections():
                if not old_parser.has_section(new_section):
                    old_parser[new_section] = new_parser[new_section]

                for new_info in new_parser[new_section]:
                    if not new_info[0] == ';':
                        if not key_exists_in_old_config(new_section, new_info, old_parser):
                            tmp_info = new_info.split('_')
                            for i in range(1, len(tmp_info)):
                                tmp_info[i] = tmp_info[i].capitalize()
                            TMP_INFO = ''.join(tmp_info)

                            if not key_exists_in_old_config(new_section, tmp_info, old_parser):
                                old_parser[new_section][new_info] = new_parser[new_section][new_info]

            with open(OLD_CONFIG_FILE, 'w', encoding='utf-8') as file:
                old_parser.write(file)
    except Error as e:
        print('Error while parse .INI file : ' + str(e))
