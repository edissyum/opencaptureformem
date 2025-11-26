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


class FindSubject(Thread):
    def __init__(self, text, locale, log, config):
        Thread.__init__(self, name='subjectThread')
        self.Log = log
        self.text = text
        self.subject = None
        self.Locale = locale
        self.config = config

        ia_cfg = config.cfg.get('IA', {})
        self.url_chatbot = ia_cfg.get('url_chatbot')
        self.login_chatbot = ia_cfg.get('login_chatbot')
        self.password_chatbot = ia_cfg.get('password_chatbot')

        # Lecture de la clé API depuis le fichier mc_secret.key (dans le working directory)
        self.api_key = None
        try:
            with open("src/config/mc_secret.key", "r", encoding="utf-8") as f:
                self.api_key = f.read().strip()
        except FileNotFoundError:
            self.api_key = None
        except OSError as e:
            if self.Log:
                self.Log.error(f"Error reading mc_secret.key: {e}")
            self.api_key = None

        # Chatbot activé seulement si TOUT est présent : url + login + password + api_key
        self.chatbot_enabled = bool(
            self.url_chatbot
            and self.login_chatbot
            and self.password_chatbot
            and self.api_key
        )

        if not self.chatbot_enabled and self.Log:
            self.Log.info(
                "Chatbot disabled: missing url_chatbot, login_chatbot, "
                "password_chatbot or mc_secret.key"
            )

    def _ask_chatbot_for_subject(self):
        """
        Tente de trouver le sujet via le chatbot (API REST en streaming texte).
        Retourne le sujet SANS le préfixe 'Objet:' si succès, sinon None.
        NE JAMAIS lever d'exception vers l'extérieur.
        """
        if not self.chatbot_enabled:
            return None

        try:
            headers = {
                "accept": "text/plain",
                "Content-Type": "application/json",
                "X-Api-Key": self.api_key,
            }

            auth = requests.auth.HTTPBasicAuth(self.login_chatbot, self.password_chatbot)

            payload = {
                "query": "Donne moi l'objet (titre court sans date) de ce courrier  sous la forme \"Objet: X\"",
                "letter_context": [self.text],
                "no_rag": True,
                "no_context": True,
                "debugging": False,
            }

            response = requests.post(
                self.url_chatbot,
                headers=headers,
                json=payload,
                timeout=120,
                auth=auth,
            )

        except RequestException as e:
            #if self.Log:
                #self.Log.error(f"Chatbot subject detection failed (connection error): {e}")
            return None
        except Exception as e:
            # Pour être sûr de ne jamais faire planter le thread
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

        # On split par lignes pour enlever la première ligne JSON {"request_id": "..."}
        try:
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
                            # ligne de métadonnées -> on la zappe
                            continue
                        else:
                            body_lines.append(line)
                    except ValueError:
                        body_lines.append(line)
                else:
                    body_lines.append(line)

            raw_subject = "\n".join(body_lines).strip()
            if not raw_subject:
                if self.Log:
                    self.Log.error("Chatbot subject detection failed: no usable text in response")
                return None

            match = re.search(r"Objet\s*:\s*(.+)", raw_subject, flags=re.IGNORECASE)
            if match:
                cleaned = match.group(1).strip()
            else:
                cleaned = raw_subject.strip()

            return cleaned or None

        except Exception as e:
            if self.Log:
                self.Log.error(f"Chatbot subject parsing failed: {e}")
            return None

    def run(self):
        """
        1) Essayer le chatbot (si activé)
        2) Si échec ou sujet vide, fallback sur la détection OCR regex existante
        """
        # 1) Tentative via chatbot seulement s'il est activé
        self.subject = None
        if self.chatbot_enabled:
            try:
                self.subject = self._ask_chatbot_for_subject()
            except Exception as e:
                # Sécurité : ne jamais laisser une exception sortir du thread
                if self.Log:
                    self.Log.error(f"Chatbot subject detection crashed: {e}")
                self.subject = None

        # 2) Fallback OCR si pas de sujet retourné par le chatbot
        if not self.subject:
            subject_array = []
            for _subject in re.finditer(r"" + self.Locale.regexSubject, self.text, flags=re.IGNORECASE):
                if len(_subject.group()) > 3:
                    # Using the [:-2] to delete the ".*" of the regex
                    # Useful to keep only the subject and delete the left part
                    # (e.g : remove "Objet : " from "Objet : Candidature pour un emploi - Démo Salindres")
                    subject_array.append(_subject.group())

            # If there is more than one subject found, prefer the "Object" one instead of "Ref"
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
                self.subject = ''

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
                            if letter in not_allowed_symbol:  # Check if the line doesn't contain some specific char
                                find = True
                                break
                        if find:
                            continue
                        first_char = next_line[0]
                        if first_char.lower() == first_char:  # Check if first letter of line is not an upper one
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
