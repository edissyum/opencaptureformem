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
import base64
from src.main import launch
from src.app.controllers.custom import get_custom_config_file_path, get_custom_config_value


def process_files(files, custom_id, process_name, read_destination_from_filename, keep_pdf_debug, destination,
                  custom_fields):
    config_file_path, error = get_custom_config_file_path(custom_id)
    if error:
        return {"message": error}, 400

    config_temp_dir, error = get_custom_config_value(config_file_path, 'tmppath', 'GLOBAL')
    if error:
        return {"message": error}, 400

    if not os.path.exists(config_temp_dir):
        os.makedirs(config_temp_dir, exist_ok=True)

    errors = []
    for _, file in enumerate(files):
        tmp_file_path = config_temp_dir + '/' + file['file_name']
        with open(tmp_file_path, 'wb') as temp_file:
            temp_file.write(base64.b64decode(file["file_content"]))
        temp_file.close()

        os.chmod(tmp_file_path, 0o644)

        args = {
            'script': 'API',
            'file': tmp_file_path,
            'process': process_name,
            'config': config_file_path,
            'destination': destination,
            'custom_fields': custom_fields,
            'keep_pdf_debug': keep_pdf_debug,
            'RDFF': read_destination_from_filename
        }

        try:
            launch(args)
        except Exception as e:
            errors.append({"file_name": file["file_name"], "error": str(e)})

    if errors:
        return {"message": "Some files encountered errors", "errors": errors}, 500
    else:
        return {"message": "All files processed successfully"}, 200
