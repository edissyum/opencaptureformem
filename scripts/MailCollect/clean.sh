#!/bin/bash
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

# Bash script to clean MailCollect batches and log

batch_path='/opt/edissyum/opencaptureformem/data/MailCollect/'
conservation_time=7
conservation_time_error_folder=14

for dir in "$batch_path"/*/; do
    if [ -d "$dir" ]; then
        if [[ $dir != *"_ERROR"* ]]; then
            find "$dir" -mindepth 1 -maxdepth 1 -type d -mtime +$conservation_time -exec rm -rf {} ';'
        else
            find "$dir" -mindepth 2 -maxdepth 2 -type d -mtime +$conservation_time_error_folder -exec rm -rf {} ';'
        fi
    fi
done

find "$batch_path" -name "unique_id_already_processed_*" -exec rm -rf {} ';'