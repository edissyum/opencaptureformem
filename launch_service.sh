#!/bin/bash
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

export LD_LIBRARY_PATH=/usr/local/lib
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/

cd /opt/maarch/OpenCapture/
/usr/local/bin/kuyruk --app src.main.OCforMaarch worker
