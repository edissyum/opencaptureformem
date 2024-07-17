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
# @dev : Arthur Mondon <arthur@mondon.pro>


import os
from flask import current_app as app
import src.classes.Config as configClass


def get_custom_config_file_path(custom_id):
    for custom in app.config['CUSTOMS']:
        if custom['custom_id'] == custom_id:
            if os.path.isfile(custom['config_file_path']):
                return custom['config_file_path']
    return None


def get_secret_key_from_config(config_file_path):
    config = configClass.Config()
    config.load_file(config_file_path)
    return config.cfg['API']['secret_key']


def get_tmp_api_directory_from_config(config_file_path):
    config = configClass.Config()
    config.load_file(config_file_path)
    return config.cfg['API']['tmp_api']
