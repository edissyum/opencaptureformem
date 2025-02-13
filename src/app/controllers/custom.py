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
import src.classes.Config as configClass
from flask import current_app as app, jsonify, request


def get_custom_config_file_path(custom_id):
    for custom in app.config['CUSTOMS']:
        if custom['custom_id'] == custom_id:
            if os.path.isfile(custom['config_file_path']):
                return custom['config_file_path'], None
            else:
                return None, f"Configuration file not found for custom_id: {custom_id}"
    return None, f"custom_id {custom_id} not found in custom.json"


def get_custom_mail_config_file_path(custom_id):
    for custom in app.config['CUSTOMS']:
        if custom['custom_id'] == custom_id:
            if os.path.isfile(custom['config_mail_file_path']):
                return custom['config_mail_file_path'], None
            else:
                return None, f"Configuration mail file not found for custom_id: {custom_id}"
    return None, f"custom_id {custom_id} not found in custom.json"


def get_custom_config_value(config_file_path, key, master_key="API"):
    config = configClass.Config()
    config.load_file(config_file_path)
    if master_key not in config.cfg:
        return None, f"['{master_key}'] Block not found in config file {config_file_path}"

    if key in config.cfg[master_key]:
        if config.cfg[master_key][key] != "":
            return config.cfg[master_key][key], None
        return None, f"Key ['{master_key}']['{key}'] is empty in config file {config_file_path}"
    return None, f"Key ['{master_key}']['{key}'] not found in config file {config_file_path}"


def get_custom_config_process_list(config_file_path):
    process_list_str, error = get_custom_config_value(config_file_path, "process_available", "OCForMEM")
    if error:
        return jsonify({"message": error}), 400

    process_list = []
    for process in process_list_str.split(','):
        process_list.append(process)

    return process_list, None


def get_custom_config_mail_process_list(custom_id):
    config_file_path, error = get_custom_config_file_path(custom_id)
    if error:
        return ({"message": error}), 400

    config_secret_key, error = get_custom_config_value(config_file_path, 'secret_key')
    if error:
        return ({"message": error}), 400

    secret_key = request.args.get('secret_key')
    if not secret_key or secret_key != config_secret_key:
        return ({"message": "Invalid secret key"}), 401

    config_mail_file_path, error = get_custom_mail_config_file_path(custom_id)
    if error:
        return ({"message": error}), 400

    config_mail = configClass.Config()
    config_mail.load_file(config_mail_file_path)

    tenant_id = config_mail.cfg['GRAPHQL']['tenant_id']
    client_id = config_mail.cfg['GRAPHQL']['client_id']
    client_secret = config_mail.cfg['GRAPHQL']['client_secret']
    if not tenant_id or not client_id or not client_secret:
        return ({"message": "Erreur lors de la connexion GraphQL"}), 400

    process_list = []
    for section in config_mail.cfg:
        if section not in ['GLOBAL', 'OAUTH', 'EXCHANGE', 'GRAPHQL']:
            process_list.append(section)
    return process_list, None
