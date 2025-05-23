#!/bin/bash
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

if [ "$EUID" -ne 0 ]
  then echo "update.sh needed to be launch by user with root privileges"
  exit 1
fi

# Put the default paths.
# Modify them if needed
currentDate=$(date +%m%d%Y-%H%M%S)
OCPath="/opt/edissyum/opencaptureformem/"
backupPath="/opt/edissyum/opencaptureformem.$currentDate/"

user=$(who am i | awk '{print $1}')

# Backup all the Open-Capture path
cp -r "$OCPath" "$backupPath"

if [ ! -f "/opt/edissyum/python-venv/opencaptureformem/bin/python3" ]; then
    echo "#######################################################################################"
    echo "            The default Python Virtual environment path doesn't exist"
    echo "  Do you want to exit update ? If no, the script will use default Python installation"
    echo "#######################################################################################"
    printf "Enter your choice [%s] : " "yes/${bold}no${normal}"
    read -r choice
    if [ "$choice" = "yes" ]; then
        exit
    else
        pythonVenv='false'
    fi
fi


# Force launch of apt and pip requirements
# in case of older version without somes packages/libs
cd "$OCPath/install/" || exit 1
apt update
xargs -a apt-requirements.txt apt install -y

"/opt/edissyum/python-venv/opencaptureformem/bin/python3" -m pip install --upgrade pip
"/opt/edissyum/python-venv/opencaptureformem/bin/python3" -m pip install --upgrade pillow
"/opt/edissyum/python-venv/opencaptureformem/bin/python3" -m pip install -r pip-requirements.txt
"/opt/edissyum/python-venv/opencaptureformem/bin/python3" -m pip install --upgrade -r pip-requirements.txt

cd $OCPath || exit 3
find . -name ".gitkeep" -delete

# Fix right on folder
chmod -R 775 $OCPath
chown -R "$user":"$user" $OCPath

# Restart worker
systemctl restart oc-worker.service