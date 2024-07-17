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

import jwt
import datetime
from functools import wraps
from flask import request, jsonify
from src.app.controllers.custom import get_custom_config_file_path, get_custom_config_value


def generate_token(secret_key, token_expiration_time):
    payload = {
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=token_expiration_time),
        'iat': datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


def verify_jwt(token, secret_key):
    try:
        decoded = jwt.decode(token, secret_key, algorithms=['HS256'])
        return decoded
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def check_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        custom_id = request.json.get('custom_id')

        if not token or not custom_id:
            return jsonify({"message": "Token or custom_id is missing"}), 401

        if token.startswith("Bearer "):
            token = token[7:]

        config_file_path, error = get_custom_config_file_path(custom_id)
        if error:
            return jsonify({"message": error}), 400

        config_secret_key, error = get_custom_config_value(config_file_path, 'secret_key')
        if error:
            return jsonify({"message": error}), 400

        decoded = verify_jwt(token, config_secret_key)
        if not decoded:
            return jsonify({"message": "Invalid or expired token"}), 401

        return f(*args, **kwargs)

    return decorated_function
