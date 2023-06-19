# This file is part of Open-Capture For MEM Courrier.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture For MEM Courrier is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture For MEM Courrier.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import sys
import argparse
from configparser import ConfigParser, ExtendedInterpolation

from PIL import Image
from pyzbar.pyzbar import decode


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-f', '--file', required=True, help="path to file")
    ap.add_argument('-c', '--config', required=True, help="path to config file")
    args = vars(ap.parse_args())

    if not args['file']:
        sys.exit('No file was given')
    if not args['config']:
        sys.exit('No config was given')

    parser = ConfigParser(interpolation=ExtendedInterpolation())
    parser.read(args['config'])
    config = {}
    for section in parser.sections():
        config[section] = {}
        for info in parser[section]:
            config[section][info] = parser[section][info]

    if 'reconciliationtype' not in config['OCForMEM']:
        reconciliation_type = 'QRCODE'
    else:
        reconciliation_type = config['OCForMEM']['reconciliationtype']

    detected_barcode = decode(Image.open(args['file']))
    for barcode in detected_barcode:
        if barcode.type == reconciliation_type:
            print(barcode.data.decode("utf-8"))
            break
