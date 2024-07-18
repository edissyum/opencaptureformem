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

from src.app import app
from flask import request, jsonify
from src.app.connector import process_files
from src.app.controllers.auth import generate_token, check_token
from src.app.controllers.custom import get_custom_config_file_path, get_custom_config_value


@app.route('/get_token', methods=['POST'])
def get_token():
    data = request.get_json()
    secret_key = data.get('secret_key')
    custom_id = data.get('custom_id')

    if not secret_key or not custom_id:
        return jsonify({"message": "Missing data"}), 400

    config_file_path, error = get_custom_config_file_path(custom_id)
    if error:
        return jsonify({"message": error}), 400

    config_secret_key, error = get_custom_config_value(config_file_path, 'secret_key')
    if error:
        return jsonify({"message": error}), 400

    token_expiration_time, error = get_custom_config_value(config_file_path, 'token_expiration_time')
    if error:
        return jsonify({"message": error}), 400
    try:
        token_expiration_time = float(token_expiration_time)
    except ValueError:
        return jsonify({"message": "Invalid token expiration time"}), 500

    if secret_key != config_secret_key:
        return jsonify({"message": "Invalid secret key"}), 401

    token = generate_token(secret_key, token_expiration_time)
    return jsonify({"token": token})


@app.route('/upload', methods=['POST'])
@check_token
def upload_files():
    data = request.get_json()
    files = data.get('files')
    custom_id = data.get('custom_id')
    process_name = data.get('process_name')
    read_destination_from_filename = data.get('read_destination_from_filename', True)
    keep_pdf_debug = data.get('keep_pdf_debug', 'false')
    destination = data.get('destination', None)

    if not files or not custom_id or not process_name:
        return jsonify({"message": "Missing data"}), 400

    if not isinstance(files, list):
        return jsonify({"message": "Files must be a list"}), 400

    for file in files:
        if not isinstance(file, dict):
            return jsonify({"message": "Each file must be a dictionary"}), 400
        if 'file_name' not in file or 'file_content' not in file:
            return jsonify({"message": "Each file must have a 'file_name' and 'file_content' key"}), 400
        if not file['file_name'] or not file['file_content']:
            return jsonify({"message": "Each file must have a valid 'file_name' and 'file_content' value"}),

    response, status_code = process_files(files, custom_id, process_name, read_destination_from_filename,
                                          keep_pdf_debug, destination)

    return jsonify(response), status_code
