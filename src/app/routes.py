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

from flask import request, jsonify
from src.app import app
from src.app.connector import process_files
from src.app.controllers.auth import generate_token, check_token
from src.app.controllers.custom import get_custom_config_file_path, get_secret_key_from_config


@app.route('/get_token', methods=['POST'])
def get_token():
    data = request.get_json()
    secret_key = data.get('secret_key')
    custom_id = data.get('custom_id')

    if not secret_key or not custom_id:
        return jsonify({"message": "Missing data"}), 400

    config_file_path = get_custom_config_file_path(custom_id)
    if not config_file_path:
        return jsonify({"message": "Invalid custom id"}), 400

    config_secret_key = get_secret_key_from_config(config_file_path)

    if not config_secret_key:
        return jsonify({"message": "Could not read secret key from config"}), 500

    if secret_key != config_secret_key:
        return jsonify({"message": "Invalid secret key"}), 401

    token = generate_token(secret_key)
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

    response, status_code = process_files(files, custom_id, process_name, read_destination_from_filename, keep_pdf_debug, destination)

    return jsonify(response), status_code
