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

import re
from threading import Thread


class FindChrono(Thread):
    def __init__(self, text, process):
        Thread.__init__(self, name='chronoThread')
        self.text = text
        self.chrono = None
        self.process = process

    def run(self):
        """
        Override the default run function of threading package
        This will search for a chrono number into the text of original PDF

        """
        for _chrono in re.finditer(r"" + self.process['chronoregex'] + "", self.text):
            self.chrono = _chrono.group()
