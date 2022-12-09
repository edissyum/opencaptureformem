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
import json
import os
import sys
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from classes.Log import Log
from classes.Config import Config
from classes.WebServices import WebServices

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-chrono", "--chrono", required=True, help="path to file")
ap.add_argument("-c", "--config", required=True, help="path to config.xml")
args = vars(ap.parse_args())

if __name__ == '__main__':
    # Init all the var
    config = Config()
    config.load_file(args['config'])
    Log = Log(config.cfg['GLOBAL']['logfile'])
    WebService = WebServices(
        config.cfg['OCForMEM']['host'],
        config.cfg['OCForMEM']['user'],
        config.cfg['OCForMEM']['password'],
        Log,
        config.cfg['GLOBAL']['timeout'],
        config.cfg['OCForMEM']['certpath']
    )

    chrono = args['chrono']
    try:
        chrono = json.loads(chrono)
        chrono = chrono['chrono']
    except (json.decoder.JSONDecodeError, TypeError):
        pass

    response = WebService.check_attachment(chrono)
    if response:
        print(response['result'])
    else:
        print('KO')
