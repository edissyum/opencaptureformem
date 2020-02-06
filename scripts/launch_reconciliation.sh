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
# @dev : Pierre-Yvon Bezert <pierreyvon.bezert@edissyum.com>


# Variables
script="RECONCILIATION"
# Made 14 char for name, to have the same layout in log as OC application
# Made 24 char for filename, to have the same layout in log as OC application
spaces="              "
name="$script"
name=${name:0:14}${spaces:0:$((14-${#name}))}

spaces="                        "
scriptName="launch_$script.sh"
scriptName=${scriptName:0:24}${spaces:0:$((24-${#scriptName}))}

tmp_dir=/tmp
process_pj=reconciliation_default
process_attfnd=reconciliation_found
dispatcher_path="/opt/maarch/OpenCapture/"
logFile="$dispatcher_path/data/log/OCforMaarch.log"

echo "[$name] [$scriptName] $(date +"%d-%m-%Y %T") INFO Launching $script script" >> "$logFile"

# Define functions

convertToJpg(){
    # This command convert first page of the pdf to jpg and crop only the bottom of the image using "x500+0+1500"
    # If you want to crop the top use, for example, "x500+0+0"
    # -alpha remove avoid the black background after the convert in a random way
    convert -density 200 "$1[0]" -quality 100 -alpha remove -geometry x2000 -crop x500+0+1500 "$2"
}

readBarCode(){
    # Read the barcode and retrieve the informations it contains
    zbarimg -q --xml -Sdisable -Sqr.enable "$1" | grep -oP 'CDATA\[[^\]]*' | sed -e "s#CDATA\[##g"
}

check_attachment(){
    # Using Maarch WebService, check if the chrono number is related to an attachment
    python3 ${dispatcher_path}/src/process/checkAttachment.py -c "$dispatcher_path/src/config/config.ini" -chrono "$1"
}

defaultProcess(){
    # If barcode couldn't be read or isn't present, use default process
    # Same if the barcode is read but the attachment doesn't exist on Maarch database
    python3 ${dispatcher_path}/launch_worker.py -c "$dispatcher_path/src/config/config.ini" --read-destination-from-filename --process ${process_pj} -f "$1"
}

reconciliationProcess(){
    # If all things went good, start the reconciliation process and insert the document as a Maarch attachment
    python3 ${dispatcher_path}/launch_worker.py -c "$dispatcher_path/src/config/config.ini" --process "$process_attfnd" -f "$1" -resid "$2" -chrono "$3"
}


# Main

inputPath="$1"

#sleep 5 # sleep to avoid broken file during file transfert

if [[ ! -f "$1" ]]
then
        echo "[$name] [$scriptName] $(date +"%d-%m-%Y %T") ERROR $inputPath is not a valid file" >> "$logFile"
        exit 0
fi

fileName=$(basename $1)
# service is the parent folder name. e.g : /var/share/sortant/DGS/test.pdf --> $service will be DGS
service=$(echo "$inputPath" | sed -e 's#/[^/]*$##' -e 's#.*/##')

tmpPath="$tmp_dir"/"$service"_"$fileName"
mv "$inputPath" "$tmpPath"

# Start process

imgFile="${tmp_dir}/${fileName//.*}.jpg"
convertToJpg "$tmpPath" "$imgFile"
barcode=$(readBarCode "$imgFile")

rm "$imgFile"

if [[ -z "$barcode" ]]
then
	echo "[$name] [$scriptName] $(date +"%d-%m-%Y %T") INFO Start DEFAULT process" >> "$logFile"
    defaultProcess "$tmpPath"
else
    resid=${barcode%%#*}
    chrono=${barcode/*#/}

    attachmentOK=$(check_attachment "$chrono")
    if [[ "$attachmentOK" == "OK" ]]
    then
        echo "[$name] [$scriptName] $(date +"%d-%m-%Y %T") INFO Start RECONCILIATION process" >> "$logFile"
        reconciliationProcess "$tmpPath" "$resid" "$chrono"
    else
        echo "[$name] [$scriptName] $(date +"%d-%m-%Y %T") INFO Start DEFAULT process" >> "$logFile"
        defaultProcess "$tmpPath"
    fi
fi