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

name="IN"
OCPath="/opt/maarch/OpenCapture/"
logFile="$OCPath"/data/log/OCforMaarch.log
errFilepath="$OCPath/data/error/$name/"
tmpFilepath="$OCPath/data/pdf/"
PID=/tmp/securite-$name-$$.pid

echo "[$name.sh      ] $(date +"%d-%m-%Y %T") INFO Launching $name.sh script" >> "$logFile"

filepath=$1
filename=$(basename "$filepath")
ext=$(file -b -i "$filepath")

if ! test -e $PID && test "$ext" = 'application/pdf; charset=binary' && test -f "$filepath";
then
    touch $PID
    echo $$ > $PID
    echo "[$name.sh      ] $(date +"%d-%m-%Y %T") INFO $filepath is a valid file and PID file created" >> "$logFile"

    mv "$filepath" "$tmpFilepath"

    python3 "$OCPath"/worker.py -c "$OCPath"/src/config/config.ini -f "$tmpFilepath"/"$filename" --read-destination-from-filename -process incoming

    rm -f $PID

elif test -f "$filepath" && test "$ext" != 'application/pdf; charset=binary';
then
    echo "[$name.sh      ] $(date +"%d-%m-%Y %T") ERROR $filename is a not valid PDF file" >> "$logFile"
    mkdir -p "$errFilepath"
    mv "$filepath" "$errFilepath"
else
    echo "[$name.sh      ] $(date +"%d-%m-%Y %T") WARNING capture on $filepath aready active : PID exists : $PID" >> "$logFile"
fi

