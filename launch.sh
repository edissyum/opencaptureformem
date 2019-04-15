#!/bin/bash

filepath=$1
filename=$(basename "$filepath")

OCPath="/opt/maarch/OpenCapture/"
tmpFilepath="$OCPath/data/pdf/"

mv "$filepath" "$tmpFilepath"

python3 "$OCPath"/worker.py -c "$OCPath"/src/config/config.ini -f "$OCPath"/data/pdf/"$filename" --read-destination-from-filename -process incoming
