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

import os
import sys
import argparse
from src.main import launch

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument('-resid', "--resid", required=False)
ap.add_argument('-chrono', "--chrono", required=False)
ap.add_argument("-f", "--file", required=False, help="path to file")
ap.add_argument('-internal-note', "--isinternalnote", required=False, action="store_true")
ap.add_argument("-c", "--config", required=True, help="path to config.ini")
ap.add_argument('-process', "--process", required=False, default='incoming')
ap.add_argument('-kpdfd', "--keep-pdf-debug", required=False, default='false')
ap.add_argument("-d", '--destination', required=False, help="Default destination")
ap.add_argument("-s", '--script', required=False, help="Script name")
ap.add_argument("--read-destination-from-filename", '--RDFF', dest='RDFF', action="store_true", required=False, help="Read destination from filename")
args = vars(ap.parse_args())

if args['file'] is None:
    sys.exit('No file was given')

if not os.path.exists(args['config']):
    sys.exit('Config file couldn\'t be found')

launch(args)
