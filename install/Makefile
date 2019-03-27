sudo apt update
cat apt-requirements.txt | xargs sudo apt install -y
pip3 install -r pip-requirements.txt

git clone https://github.com/tesseract-ocr/tesseract
cd tesseract
mkdir build && cd build
cmake ../ && make
sudo make install
export LD_LIBRARY_PATH=/usr/local/lib
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/tessdata/