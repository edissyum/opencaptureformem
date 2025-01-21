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

import json
from .. import app
from flask.helpers import send_file
from ..connector import process_mail
from flask import render_template, request
from ..controllers.custom import get_custom_mail_config_file_path, get_custom_config_mail_process_list


@app.route("/getProcessList")
def get_process():
    custom_id = request.args.get('custom_id')
    if not custom_id:
        return ({"message": "NO CUSTOM"}), 400

    error_message = None
    process_list = []
    message, error = get_custom_config_mail_process_list(custom_id)
    if error:
        error_message = message['message']
    else:
        process_list = message
    return render_template("taskpane.html", process_list=process_list, error_message=error_message,
                           custom_id=custom_id)


@app.route("/exec_process", methods=['POST'])
def exec_process():
    data = json.loads(request.data)
    _, error = get_custom_mail_config_file_path(data['custom_id'])
    if error:
        return ({"message": error}), 400

    res = process_mail(data['mail_id'], data['custom_id'], data['process'])
    return res


@app.route("/assets/<asset_name>")
def icon16(asset_name):
    return send_file(f"addin_outlook/static/assets/{asset_name}", mimetype='image/png')


@app.route("/static/taskpane.css")
def get_taskpane_css():
    return send_file("addin_outlook/static/taskpane.css", mimetype='text/css')


@app.route("/static/<image_name>")
def get_static_image(image_name):
    return send_file(f"addin_outlook/static/assets/{image_name}", mimetype='image/png')


@app.route("/static/taskpane.js")
def get_taskpane_js():
    return send_file("addin_outlook/static/taskpane.js", mimetype='text/javascript')


@app.route('/favicon.ico')
def favicon():
    return send_file('addin_outlook/static/favicon.ico', mimetype='image/vnd.microsoft.icon')


