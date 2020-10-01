#!/bin/bash
# This file is part of Open-Capture.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

if [ "$EUID" -ne 0 ]
  then echo "update.sh needed to be launch by user with root privileges"
  exit 1
fi

# Put the default paths.
# Modify them if needed
OCPath="/opt/maarch/OpenCapture/"
backupPath="/opt/maarch/OpenCapture.bck/"

user=$(who am i | awk '{print $1}')

# Backup all the Open-Capture path
cp -r "$OCPath" "$backupPath"

# Retrieve the last tags from gitlab
cd "$OCPath" || exit 1
git config --global user.email "update@ocformaarch"
git config --global user.name "Update Open-Capture"
git pull
git stash # Remove custom code if needed
latest_tag=$(git describe --tags "$(git rev-list --tags=*20.03 --max-count=1)")
git checkout "$latest_tag"
git config core.fileMode False

# Force launch of apt and pip requirements
# in case of older version without somes packages/libs
cd install/ || exit 2
xargs -a apt-requirements.txt apt install -y
pip3 install --upgrade pip
pip3 install -r pip-requirements.txt

cd $OCPath || exit 2
find . -name ".gitkeep" -delete

# Fix right on folder
chmod -R 775 $OCPath
chown -R "$user":"$user" $OCPath

# Restart worker
systemctl restart oc-worker.service