OS=$(lsb_release -si)

apt update

if [[ "$OS" = 'Debian' ]]
then
su -c 'cat > /etc/apt/sources.list.d/stretch-backports.list.test << EOF
deb http://http.debian.net/debian stretch-backports main contrib non-free
EOF'
    apt update
    apt install -t stretch-backports tesseract-ocr
    apt install -t stretch-backports tesseract-ocr-fra
    apt install -t stretch-backports tesseract-ocr-eng

elif [[ "$OS" = 'Ubuntu' ]]
then
    apt install tesseract-ocr
    apt install tesseract-ocr-fra
    apt install tesseract-ocr-eng
fi


cat apt-requirements.txt | xargs apt install -y
pip3 install -r pip-requirements.txt

cd ../
find -name ".gitkeep" -delete

touch /etc/systemd/system/oc-worker.service
su -c 'cat > /etc/systemd/system/oc-worker.service << EOF
[Unit]
Description=Daemon for OpenCapture for Maarch

[Service]
Type=simple

User=edissyum
Group=edissyum
UMask=0022

ExecStart=/opt/maarch/OpenCapture/launch_service.sh

Restart=on-failure

# Configures the time to wait before service is stopped forcefully.
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target
EOF'


systemctl daemon-reload && systemctl start oc-worker.service
