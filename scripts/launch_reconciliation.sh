#!/bin/bash

# Variables
tmp_dir=/tmp
process_pj=reconciliation_default
process_attfnd=reconciliation_found
dispatcher_path=/home/nathan/PycharmProjects/oc_test/

# Define functions

convertToJpg(){
    # This command convert first page of the pdf to jpg and crop only the bottom of the image using "x500+0+1500"
    # If you want to crop the top use, for example, "x500+0+0"
    convert -density 200 "$1[0]" -quality 100 -geometry x2000 -crop x500+0+1500 "$2"
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
    # If barcode couldn't be read or isn't present use default process
    # Same if the barcode is read but the attachment doesn't exist on Maarch database
    python3 ${dispatcher_path}/worker.py -c "$dispatcher_path/src/config/config.ini" --read-destination-from-filename --process "$process_pj" -f "$1"
}

reconciliationProcess(){
    # If all things went good, start the reconciliation process and insert the document as a Maarch attachment
    python3 ${dispatcher_path}/worker.py -c "$dispatcher_path/src/config/config.ini" --process "$process_attfnd" --resid "$2" --chrono "$3" -f "$1"
}


defaultProcess /home/nathan/PycharmProjects/oc_test/data/pdf/DGS_maarch.pdf