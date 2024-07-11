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
import base64
from src.app import app
from src.app.connector import process_files
from src.app.controllers.auth import generate_token, check_token


@app.route('/get-token', methods=['POST'])
def get_token():
    secret_key = request.json.get('secret_key')
    if secret_key != app.config['SECRET_KEY']:
        return jsonify({"message": "Invalid secret key"}), 401

    token = generate_token(app.config['SECRET_KEY'])
    return jsonify({"token": token})


@app.route('/upload', methods=['POST'])
@check_token
def upload_files():
    data = request.get_json()
    files = data.get('files')
    custom_id = data.get('custom_id')
    process_name = data.get('process_name')

    if not files or not custom_id or not process_name:
        return jsonify({"message": "Missing data"}), 400

    decoded_files = []
    for file in files:
        decoded_files.append(base64.b64decode(file))

    try:
        process_files(decoded_files, custom_id, process_name)
    except Exception as e:
        return jsonify({"message": f"Error processing files: {str(e)}"}), 500

    return jsonify({"message": "Files processed successfully"}), 200
