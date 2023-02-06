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
import shutil
import argparse
import tempfile
import src.classes.Log as logClass
from src.main import recursive_delete
import src.classes.Config as configClass
import src.classes.Separator as separatorClass

ap = argparse.ArgumentParser()
ap.add_argument("-c", "--config", required=True, help="path to config.ini")
ap.add_argument("-f", "--file", required=False, help="path to file")
args = vars(ap.parse_args())

output_dir = os.path.dirname(args['file']) + '/'

config = configClass.Config()
config.load_file(args['config'])
log = logClass.Log(config.cfg['GLOBAL']['logfile'])
tmp_folder = tempfile.mkdtemp(dir=config.cfg['GLOBAL']['tmppath'])
separator = separatorClass.Separator(log, config, tmp_folder, 'OCForMEM_reconciliation_default')
separator.enabled = True
separator.run(args['file'])

if separator.pdf_list:
    for file in separator.pdf_list:
        filename, extension = os.path.splitext(os.path.basename(file))
        shutil.move(file, output_dir + filename + '_SEPARATED' + extension)
else:
    filename, extension = os.path.splitext(os.path.basename(args['file']))
    shutil.move(separator.output_dir + os.path.basename(args['file']), output_dir + filename + '_SEPARATED' + extension)

recursive_delete([tmp_folder, separator.output_dir, separator.output_dir_pdfa], log)
