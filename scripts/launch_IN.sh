#!/bin/bash
# This file is part of OpenCapture.

# OpenCapture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OpenCapture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with OpenCapture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>
# @dev : Pierre-Yvon Bezert <pierreyvon.bezert@edissyum.com>

OCPath="/opt/maarch/OpenCapture/"
tmpFilepath="$OCPath/data/pdf/"
logFile="$OCPath"/data/log/OCforMaarch.log

echo "[IN.SH         ] $(date +"%d-%m-%Y %T") INFO Launching IN.SH script" >> "$logFile"

filepath=$1
filename=$(basename "$filepath")

if [[ ! -f "$1" ]]
then
        echo "[IN.SH         ] $(date +"%d-%m-%Y %T") ERROR $1 is not a valid file" >> "$logFile"
        exit 0
fi

mv "$filepath" "$tmpFilepath"

python3 "$OCPath"/worker.py -c "$OCPath"/src/config/config.ini -f "$OCPath"/data/pdf/"$filename" --read-destination-from-filename -process incoming
