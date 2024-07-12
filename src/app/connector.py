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
import subprocess
import base64

def process_files(files, custom_id, process_name):
    with tempfile.TemporaryDirectory() as temp_dir:
        decoded_files = []
        for file in files:
            decoded_files.append(base64.b64decode(file))

        for file in decoded_files:
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix=".pdf")
            temp_file.write(file)
            temp_file_path = temp_file.name
            temp_file.close()

            os.chmod(temp_file_path, 0o644)

            subprocess.run(["/bin/bash", "/opt/edissyum/opencaptureformem/scripts/launch_IN.sh", temp_file_path])
