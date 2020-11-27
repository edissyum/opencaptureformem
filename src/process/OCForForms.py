# This file is part of Open-Capture.

# Open-Capture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Open-Capture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Open-Capture.  If not, see <https://www.gnu.org/licenses/>.

# @dev : Nathan Cheval <nathan.cheval@outlook.fr>

import os
import re
import json


def process_form(args, config, log):
    json_identifier = config.cfg['GLOBAL']['formpath'] + 'forms_identifier.json'
    if os.path.isfile(json_identifier):
        identifier = open(json_identifier, 'r').read()
        identifier = json.loads(identifier)
        process_found = False
        process = False
        for _process in identifier:
            subject = args['data']['subject']
            keyword_subject = identifier[_process]['keyword_subject']
            if keyword_subject in subject:
                process_found = True
                process = _process
                log.info('The e-mail will use the "' + process + '" form process')

        if process_found:
            json_file = config.cfg['GLOBAL']['formpath'] + identifier[process]['json_file']
            if os.path.isfile(json_file):
                data = open(json_file, 'r').read()
                data = json.loads(data)
                print(data)
        else:
            log.error('No process was found, the mail will be processed normally')
            return False, 'default'
    else:
        log.error("Could not find JSON config file : " + json_identifier)
