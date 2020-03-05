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

script="MAIL"
# Made 14 char for name, to have the same layout in log as OC application
# Made 24 char for filename, to have the same layout in log as OC application
spaces="              "
name="$script.sh"
name=${name:0:14}${spaces:0:$((14-${#name}))}

spaces="                        "
scriptName="launch_$script.sh"
scriptName=${scriptName:0:24}${spaces:0:$((24-${#scriptName}))}

OCPath="/home/nathan/PycharmProjects/oc_for_maarch/"
logFile="$OCPath"/data/log/OCforMaarch.log
PID=/tmp/securite-$script-$$.pid

echo "[$name] [$scriptName] $(date +"%d-%m-%Y %T") INFO Launching $script script" >> "$logFile"

if ! test -e $PID;
then
  touch $PID
  echo $$ > $PID

  python3 "$OCPath"/launch_worker_mail.py -c "$OCPath"/src/config/config.ini -cm "$OCPath"/src/config/mail.ini --process MAIL_1

  rm -f $PID
else
  echo "[$name] [$scriptName] $(date +"%d-%m-%Y %T") WARNING MAIL capture is already active : PID exists : $PID" >> "$logFile"
fi

