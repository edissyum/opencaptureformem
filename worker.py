# This file is part of OpenCapture.

# OpenCapture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# OpenCapture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with OpenCapture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import os
import sys
import argparse
from src.main import launch

# construct the argument parse and parse the arguments
ap      = argparse.ArgumentParser()
ap.add_argument("-f", "--file", required=False, help="path to file")
ap.add_argument("-c", "--config", required=True, help="path to config.xml")
ap.add_argument("-d", '--destination', required=False, help="Default destination")
ap.add_argument("-p", "--path", required=False, help="path to folder containing documents")
ap.add_argument("--read-destination-from-filename", '--RDFF', dest='RDFF', action="store_true", required=False, help="Read destination from filename")
args    = vars(ap.parse_args())

if args['path'] is None and args['file'] is None:
    sys.exit('No file or path were given')
elif args['path'] is not None and args['file'] is not None:
    sys.exit('Chose between path or file')

if not os.path.exists(args['config']):
    sys.exit('Config file couldn\'t be found')

launch(args)