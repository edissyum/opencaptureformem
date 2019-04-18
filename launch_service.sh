#!/bin/bash

export LD_LIBRARY_PATH=/usr/local/lib

OS=$(lsb_release -si)

if [[ "$OS" = 'Debian' ]]
then
    export TESSDATA_PREFIX=/usr/share/tesseract-ocr/tessdata/
elif [[ "$OS" = 'Ubuntu' ]]
then
    export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/
fi

cd /opt/maarch/OpenCapture/
/usr/local/bin/kuyruk --app src.main.OCforMaarch worker
