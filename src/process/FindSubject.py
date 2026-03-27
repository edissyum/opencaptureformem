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
# @dev: Serena tetart <serena.tetart@edissyum.com>

import re
import json
from threading import Thread

import requests
from requests.exceptions import RequestException

from .AuthJWT import (
    build_jwt_headers,
    clear_jwt_cache,
    get_ca_crt_path,
    get_runtime_files_state,
)


class FindSubject(Thread):
    def __init__(self, text, locale, log, config):
        Thread.__init__(self, name='subjectThread')
        self.Log = log
        self.text = text
        self.subject = None
        self.summary_AI = None
        self.tone_AI = None
        self.Locale = locale
        self.config = config

        ia_cfg = config.cfg.get('IA', {})
        self.url_chatbot = ia_cfg.get('chatbot_url')
        self.timeout = int(ia_cfg.get('chatbot_timeout', 120))

        # Chatbot activé si l'URL est configurée.
        # L'authentification se fait désormais par JWT signé via client_private.pem.
        self.chatbot_enabled = bool(self.url_chatbot)

    def _strip_request_id_header(self, raw_stream: str) -> str:
        """
        Supprime la première ligne JSON {"request_id": "..."} si elle existe.
        """
        if not raw_stream:
            return ""

        lines = raw_stream.splitlines()
        body_lines = []
        first_non_empty_seen = False

        for line in lines:
            if not line.strip():
                continue

            if not first_non_empty_seen:
                first_non_empty_seen = True
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict) and "request_id" in obj:
                        continue
                    body_lines.append(line)
                except ValueError:
                    body_lines.append(line)
            else:
                body_lines.append(line)

        return "\n".join(body_lines).strip()

    def _parse_llm_fields(self, text: str) -> dict:
        """
        Parse Objet/summary_AI/tone_AI depuis l'output du LLM.
        """
        if not text:
            return {"subject": None, "summary_AI": None, "tone_AI": None}

        cleaned = text.strip()

        pattern = re.compile(
            r"(?im)^\s*(objet|resume|résumé|tonalite|tonalité)\s*:\s*(.*?)(?=^\s*(?:objet|resume|résumé|tonalite|tonalité)\s*:|\Z)",
            flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )

        fields = {"subject": None, "summary_AI": None, "tone_AI": None}
        for key, value in pattern.findall(cleaned):
            k = key.strip().lower()
            v = value.strip()

            if k == "objet":
                fields["subject"] = v
            elif k in ("resume", "résumé"):
                fields["summary_AI"] = v
            elif k in ("tonalite", "tonalité"):
                fields["tone_AI"] = v

        if not fields["subject"] and cleaned:
            m = re.search(r"(?im)Objet\s*:\s*(.+)", cleaned)
            fields["subject"] = m.group(1).strip() if m else cleaned.strip()

        return fields

    def _ask_chatbot_for_infos(self):
        """
        Tente de trouver Objet/summary_AI/tone_AI via le chatbot.
        Retourne un dict: {"subject": ..., "summary_AI": ..., "tone_AI": ...} ou None si échec.
        """
        if not self.chatbot_enabled:
            return None

        ia_cfg = self.config.cfg.get('IA', {})

        files_ok, files_error = get_runtime_files_state(ia_cfg, "chatbot")
        if not files_ok:
            if self.Log:
                self.Log.error(f"Chatbot subject detection failed: {files_error}")
            return None

        ca_cert = get_ca_crt_path(ia_cfg, "chatbot")

        try:
            headers = build_jwt_headers(ia_cfg, "chatbot", content_type="application/json")
            headers["Accept"] = "text/plain"

            payload = {"letter_context": self.text}

            response = requests.post(
                self.url_chatbot,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=ca_cert,
            )

            if response.status_code == 401:
                clear_jwt_cache(ia_cfg, "sender")
                headers = build_jwt_headers(ia_cfg, "chatbot", content_type="application/json", force_refresh=True)
                headers["Accept"] = "text/plain"

                response = requests.post(
                    self.url_chatbot,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                    verify=ca_cert,
                )

        except RequestException as e:
            if self.Log:
                self.Log.error(f"Chatbot subject detection failed (connection error): {e}")
            return None
        except Exception as e:
            if self.Log:
                self.Log.error(f"Chatbot subject detection failed (unexpected error): {e}")
            return None

        if response.status_code != 200:
            if self.Log:
                self.Log.error(
                    f"Chatbot subject detection failed (status {response.status_code}): {response.text}"
                )
            return None

        raw_stream = response.text
        if not raw_stream:
            if self.Log:
                self.Log.error("Chatbot subject detection failed: empty response")
            return None

        try:
            body = self._strip_request_id_header(raw_stream)
            if not body:
                if self.Log:
                    self.Log.error("Chatbot subject detection failed: no usable text in response")
                return None
            fields = self._parse_llm_fields(body)
            return fields
        except Exception as e:
            if self.Log:
                self.Log.error(f"Chatbot subject parsing failed: {e}")
            return None

    def run(self):
        """
        1) Try Chatbot
        2) If Chatbot failed or empty subject try REGEX (OCR)
        """
        self.subject = None
        self.summary_AI = None
        self.tone_AI = None

        if self.chatbot_enabled and not self.subject and self.text != None:
            try:
                infos = self._ask_chatbot_for_infos()
                if infos:
                    self.subject = infos.get("subject") or None
                    self.summary_AI = infos.get("summary_AI") or None
                    self.tone_AI = infos.get("tone_AI") or None
                if self.subject:
                    self.Log.info("Find the following subject with AI : " + self.subject)
                if self.summary_AI:
                    self.Log.info("Find the following summary_AI with AI : " + self.summary_AI)
                if self.tone_AI:
                    self.Log.info("Find the following tone_AI with AI : " + self.tone_AI)
            except Exception as e:
                if self.Log:
                    self.Log.error(f"Chatbot subject detection crashed: {e}")
                self.subject = None
                self.summary_AI = None
                self.tone_AI = None

        if not self.subject:
            subject_array = []
            for _subject in re.finditer(r"" + self.Locale.regexSubject, self.text, flags=re.IGNORECASE):
                if len(_subject.group()) > 3:
                    subject_array.append(_subject.group())

            if len(subject_array) > 1:
                subject = loop_find_subject(subject_array, self.Locale.subjectOnly)
                if subject:
                    self.subject = re.sub(r"^" + self.Locale.subjectOnly[:-2], '', subject, flags=re.IGNORECASE).strip()
                else:
                    subject = loop_find_subject(subject_array, self.Locale.refOnly)
                    if subject:
                        self.subject = re.sub(r"^" + self.Locale.refOnly[:-2], '', subject, flags=re.IGNORECASE).strip()
            elif len(subject_array) == 1:
                self.subject = re.sub(r"^" + self.Locale.regexSubject[:-2], '', subject_array[0], flags=re.IGNORECASE).strip()
            else:
                self.subject = None

            if self.subject:
                self.subject = re.sub(r"(RE|TR|FW)\s*:", '', self.subject, flags=re.IGNORECASE).strip()
                self.search_subject_second_line()
                self.Log.info("Find the following subject : " + self.subject)

    def search_subject_second_line(self):
        not_allowed_symbol = [':', '.']
        text = self.text.split('\n')
        cpt = 0
        if not self.subject:
            return

        for line in text:
            if line:
                find = False
                if self.subject in line:
                    next_line = text[cpt + 1]
                    if next_line:
                        for letter in next_line:
                            if letter in not_allowed_symbol:
                                find = True
                                break
                        if find:
                            continue
                        first_char = next_line[0]
                        if first_char.lower() == first_char:
                            self.subject += ' ' + next_line
                            break
                char_cpt = 0
                for char in self.subject:
                    if char in not_allowed_symbol:
                        self.subject = self.subject[:char_cpt]
                        break
                    char_cpt = char_cpt + 1
            cpt = cpt + 1


def loop_find_subject(array, compile_pattern):
    """
    Simple loop to find subject when multiple subject are found

    :param array: Array of subject
    :param compile_pattern: Choose between subject of ref to choose between all the subject in array
    :return: Return the best subject, or None
    """
    pattern = re.compile(compile_pattern, flags=re.IGNORECASE)
    for value in array:
        if pattern.search(value):
            return value
    return None
