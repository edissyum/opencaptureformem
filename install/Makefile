apt update
cat apt-requirements.txt | xargs apt install -y
pip3 install -r pip-requirements.txt

git clone -b4.0.0 https://github.com/tesseract-ocr/tesseract
cd tesseract
mkdir build && cd build
cmake .. && make
make install
