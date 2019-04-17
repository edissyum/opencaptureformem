#!/bin/bash

export LD_LIBRARY_PATH=/usr/local/lib
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/tessdata

cd /opt/maarch/OpenCapture/
/usr/local/bin/kuyruk --app src.main.OCforMaarch worker
