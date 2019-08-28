#!/bin/bash

OS=$(lsb_release -si)
VER=$(lsb_release -r)

apt update

if [[ "$OS" = 'Debian' && "$VER" == *'9'* ]]
then
su -c 'cat > /etc/apt/sources.list.d/stretch-backports.list << EOF
deb http://http.debian.net/debian stretch-backports main contrib non-free
EOF'
    apt update
    apt install -y -t stretch-backports tesseract-ocr
    apt install -y -t stretch-backports tesseract-ocr-fra
    apt install -y -t stretch-backports tesseract-ocr-eng

elif [[ "$OS" = 'Ubuntu' || "$OS" == 'Debian' && $VER == *'10'* ]]
then
    apt install -y tesseract-ocr
    apt install -y tesseract-ocr-fra
    apt install -y tesseract-ocr-eng
fi


cat apt-requirements.txt | xargs apt install -y
pip3 install -r pip-requirements.txt

cd ../
find -name ".gitkeep" -delete

touch /etc/systemd/system/oc-worker.service
su -c 'cat > /etc/systemd/system/oc-worker.service << EOF
[Unit]
Description=Daemon for Open-Capture for Maarch

[Service]
Type=simple

User=edissyum
Group=edissyum
UMask=0022

ExecStart=/opt/maarch/OpenCapture/scripts/service.sh

Restart=on-failure

# Configures the time to wait before service is stopped forcefully.
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target
EOF'


systemctl daemon-reload && systemctl start oc-worker.service
