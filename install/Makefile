apt update
cat apt-requirements.txt | xargs apt install -y
pip3 install -r pip-requirements.txt

git clone -b4.0.0 https://github.com/tesseract-ocr/tesseract
cd tesseract
mkdir build && cd build
cmake .. && make
make install
cd ../../
rm -rf tesseract
find -name ".gitkeep" -delete

sudo touch /etc/systemd/system/oc-worker.service
sudo cat > sudo /etc/systemd/system/oc-worker.service << EOF
"[Unit]
Description=Daemon for OpenCapture for Maarch

[Service]
Type=simple

User=edissyum
Group=edissyum
UMask=0022

WorkingDirectory=/opt/maarch/OpenCapture/
ExecStart=/usr/local/bin/kuyruk --app src.main.OCforMaarch worker

Restart=on-failure

# Configures the time to wait before service is stopped forcefully.
TimeoutStopSec=300

[Install]
WantedBy=multi-user.target"
EOF

sudo systemctl daemon-reload && sudo systemctl start oc-worker.service
