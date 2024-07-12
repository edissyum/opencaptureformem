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

import tempfile
import os
import base64
from flask import jsonify
from src.main import launch
from src.app.controllers.custom import get_custom_config_file_path, get_tmp_api_directory_from_config


def process_files(files, custom_id, process_name, read_destination_from_filename, keep_pdf_debug, destination):
    config_file_path = get_custom_config_file_path(custom_id)

    if not config_file_path:
        return jsonify({"message": "Invalid custom id"}), 400

    temp_dir = get_tmp_api_directory_from_config(config_file_path)

    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir, exist_ok=True)

    decoded_files = []
    for file in files:
        decoded_files.append(base64.b64decode(file))

    for file in decoded_files:
        temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix=".pdf")
        temp_file.write(file)
        temp_file_path = temp_file.name
        temp_file.close()

        os.chmod(temp_file_path, 0o644)

        args = {
            'file': temp_file_path,
            'config': config_file_path,
            'process': process_name,
            'script': 'IN',
            'read_destination_from_filename': read_destination_from_filename,
            'keep_pdf_debug': keep_pdf_debug,
            'destination': destination
        }

        launch(args)
