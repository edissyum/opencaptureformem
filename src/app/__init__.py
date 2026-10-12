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

# @dev : Nathan Cheval <nathan.cheval@edissyum.com>
# @dev : Arthur Mondon <arthur@mondon.pro>

import os
import sys
import json
from flask import Flask
from flask_cors import CORS


app = Flask(__name__, template_folder='addin_outlook/templates')
CORS(app, origins=[
    "https://outlook.cloud.microsoft",
    r"^https://[a-z0-9-]+\.cloud\.microsoft$",
])


@app.after_request
def add_headers(response):
    response.headers['Content-Security-Policy'] = (
        "frame-ancestors https://outlook.cloud.microsoft "
        "https://*.cloud.microsoft"
    )
    return response


base_dir = os.path.abspath(os.path.dirname(__file__))
custom_config_path = os.path.join(base_dir, '../config/custom.json')

if not os.path.exists(custom_config_path):
    sys.exit('Error: custom.json not found')

with open(custom_config_path, 'r', encoding='UTF-8') as file:
    app.config['CUSTOMS'] = json.load(file)

from src.app import routes
from src.app.addin_outlook import addin_routes
