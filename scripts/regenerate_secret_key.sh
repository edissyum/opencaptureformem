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
# @dev : Arthur Mondon <arthur@mondon.pro>

defaultPath=/opt/edissyum/opencaptureformem/
config_list_file="$defaultPath/src/config/custom.json"

echo "Available custom_ids:"
jq -r '.[].custom_id' $config_list_file

while true; do
    echo "Please enter a valid custom_id from the above list:"
    read -r custom_id

    if jq -e --arg cid "$custom_id" '.[] | select(.custom_id == $cid)' $config_list_file > /dev/null; then
        break
    else
        echo "Invalid custom_id. Try again."
    fi
done

echo "Warning : Every users sessions and tokens will be invalidated if you edit the secret_key!"
echo "If you want to continue, please write the following sentence: 'I confirm the secret_key regeneration'."

read -r confirmation

if [ "$confirmation" != "I confirm the secret_key regeneration" ]; then
    echo "Incorrect confirmation. Regeneration canceled"
    exit 1
fi

secret=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
config_file=$(jq -r --arg cid "$custom_id" '.[] | select(.custom_id == $cid) | .config_file_path' $config_list_file)

if grep -q 'secret_key' "$config_file"; then
    sed -i "s/^secret_key.*/secret_key = $secret/" "$config_file"
else
    echo "secret_key = $secret" >> "$config_file"
fi

chown "$user":"$group" "$config_file"
chmod 600 "$config_file"

echo "The secret_key has been regenerated in the configuration file"