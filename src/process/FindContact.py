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

import os
import re
import json
import torch
import requests
import subprocess
from thefuzz import fuzz
from threading import Thread

import transformers
import qwen_vl_utils

MAPPING = {
    'POSTAL_CODE': 'addressPostcode',
    'CITY': 'addressTown',
    'NUM_STREET': 'addressNumber',
    'STREET': 'addressStreet',
    'ADD_ADDRESS': 'addressAdditional1',
    'PHONE': 'phone',
    'EMAIL': 'email',
    'LASTNAME': 'lastname',
    'COMPANY': 'company',
    'FIRSTNAME': 'firstname'
}

def run_inference_sender_remote(config, image):
    timeout = 60

    if config.get('sender_remote_timeout'):
        timeout = int(config.get('sender_remote_timeout'))

    with open(image.filename, 'rb') as img_file:
        img_data = img_file.read()

    if config.get('sender_remote_url') and config.get('sender_remote_token'):
        response = requests.post(
            config.get('sender_remote_url'),
            headers={
                'Authorization': 'Bearer ' + config.get('sender_remote_token'),
                'Content-Type': 'image/jpeg'
            },
            data=img_data,
            timeout=timeout
        )

        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, response.text
    return False, 'Remote sender inference not configured'


def parse_output(output: str):
    final_dict = {}
    key_dict = ""
    sep_bool = True
    i = 0
    L = len(output)
    while i < L:
        if output[i] == "<":
            if output.startswith("<SEP>", i):
                i += 5
                sep_bool = True
                continue
            else:
                sep_bool = False
                i += 1
                key_dict = ""
                while i < L and output[i] != ">":
                    key_dict += output[i]
                    i += 1
        elif output[i] == ">":
            i += 1
            value_dict = ""
            while i < L and output[i] != "<":
                c = output[i]
                if c not in "\n[]":
                    value_dict += c
                i += 1
            if not sep_bool:
                final_dict[key_dict[2:]] = value_dict
            elif key_dict == "K_PHONE":
                cur = final_dict.get(key_dict[2:], [])
                if not isinstance(cur, list):
                    cur = [cur]
                cur.append(value_dict)
                final_dict[key_dict[2:]] = cur
        else:
            i += 1
    return final_dict


def get_glibc_version():
    result = subprocess.run(
        ["ldd", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    out = (result.stdout + result.stderr).lower()
    m = re.search(r"glibc\s+(\d+)\.(\d+)", out) or \
        re.search(r"(\d+)\.(\d+)", out)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 0, 0

def has_CPU_flags():
    """
    Return True if the CPU has the flag AVX2 and FMA, otherwise False.
    """
    try:
        with open("/proc/cpuinfo", "r") as f:
            data = f.read().lower()
    except FileNotFoundError:
        return False
    if "avx2" in data and "fma" in data:
        return True
    else:
        return False

def run_inference_sender(model_path, img_path, log):
    # Select the binary based on the glibc version and CPU flags
    if has_CPU_flags() and get_glibc_version() >= (2, 39) and os.path.exists(os.path.join(model_path, "mtmd_239")):
        workdir = os.path.join(model_path, "mtmd_239")
        num_threads = os.cpu_count() - 1
        if num_threads <= 0:
            num_threads = 1
        cmd = [
            f"{workdir}/llama-mtmd-cli",
            "-m", f"{workdir}/Qwen3-VL-2B-Instruct-FT-Q4_K_M.gguf",
            "--mmproj", f"{workdir}/mmproj-Qwen3-VL-2B-Instruct-FT-f16.gguf",
            "--image", img_path,
            "--image-min-tokens", "256",
            "--image-max-tokens", "512",
            "--threads", str(num_threads),
            "--temp", "0.0",
            "-p", "Extract sender's data in a python dictionary"
        ]

        result = subprocess.run(
            cmd,
            cwd=model_path,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            log.info("Error during sender inference : " + str(result.stderr))

        out = result.stdout
        out = out.replace("\n", "").replace("\"", "")
    else: # Qwen2
        model = transformers.Qwen2VLForConditionalGeneration.from_pretrained(model_path, dtype=torch.float32, device_map=None)
        model.eval()
        processor = transformers.AutoProcessor.from_pretrained(model_path, min_pixels=512 * 28 * 28, max_pixels=512 * 28 * 28, use_fast=True)
        
        with torch.inference_mode():
            formatted_data = [{"role": "user", "content": [{"type": "image", "image": img_path}, {"type": "text", "text": "Extract sender's data in a python dictionary"}]}]

            chat_text = processor.apply_chat_template(
                formatted_data,
                tokenize=False,
                add_generation_prompt=True)
            model_inputs = processor(
                text=[chat_text],
                images=[qwen_vl_utils.process_vision_info(formatted_data)[0]],
                return_tensors="pt",
                padding=True)

            input_ids = model_inputs["input_ids"].to(model.device)
            generated_ids = model.generate(
                input_ids=input_ids,
                attention_mask=model_inputs["attention_mask"].to(model.device),
                pixel_values=model_inputs["pixel_values"].to(model.device),
                image_grid_thw=model_inputs["image_grid_thw"].to(model.device),
                max_new_tokens=256)

            generated_ids_trimmed = [
                out_ids[len(in_ids):]
                for in_ids, out_ids in zip(input_ids, generated_ids)
            ]
            generated_texts = processor.batch_decode(
                generated_ids_trimmed,
                skip_special_tokens=False,
                clean_up_tokenization_spaces=False
            )
            out = (generated_texts[0])[1:-11]
    data = parse_output(out)
    if data and isinstance(data, str):
        data = json.loads(data)
    return data

class FindContact(Thread):
    def __init__(self, text, log, config, web_service, locale):
        Thread.__init__(self, name='contactThread')
        self.log = log
        self.text = text
        self.contact = ''
        self.min_ratio = 80
        self.locale = locale
        self.config = config
        self.custom_mail = ''
        self.custom_phone = ''
        if 'sender_min_ratio' in config.cfg['IA']:
            self.min_ratio = int(config.cfg['IA']['sender_min_ratio'])
        self.web_service = web_service

    def run(self):
        """
        Override the default run function of threading package
        This will search for a contact into the text of original PDF
        It will use mail, phone or URL regex
        """

        found_contact = False

        for phone in re.finditer(r"" + self.locale.phoneRegex + "", self.text):
            self.log.info('Find PHONE : ' + phone.group())

            # Now sanitize email to delete potential OCR error
            sanitized_phone = re.sub(r"[^0-9]", "", phone.group())
            self.log.info('Sanitized PHONE : ' + sanitized_phone)

            contact = self.web_service.retrieve_contact_by_phone(sanitized_phone)
            if contact:
                found_contact = True
                self.contact = contact
                self.log.info('Find phone in MEM Courrier, get it : ' + sanitized_phone)
                break
            else:
                # Add the phone into a custom value (custom_t10 by default)
                self.custom_phone += sanitized_phone + ';'
                continue

        if not found_contact:
            for mail in re.finditer(r"" + self.locale.emailRegex + "", self.text):
                self.log.info('Find E-MAIL : ' + mail.group())
                # Now sanitize email to delete potential OCR error
                sanitized_mail = re.sub(r"[" + self.config.cfg['GLOBAL']['sanitize_str'] + "]", "", mail.group())
                self.log.info('Sanitized E-MAIL : ' + sanitized_mail)

                contact = self.web_service.retrieve_contact_by_mail(sanitized_mail)
                if contact:
                    self.contact = contact
                    self.log.info('Find E-MAIL in MEM Courrier, attach it to the document')
                    break
                else:
                    # Add the e-mail into a custom value (custom_t10 by default)
                    self.custom_mail += sanitized_mail + ';'
                    continue

    def compare_contact(self, contact, ai_contact):
        match_contact = {}
        global_ratio = 0
        cpt = 0

        for key in ai_contact:
            if ai_contact[key]:
                if key in contact:
                    if contact[key]:
                        match_contact[key] = fuzz.ratio(ai_contact[key].lower(), contact[key].lower())
                        global_ratio += match_contact[key]
                        cpt += 1
        global_ratio = global_ratio / cpt

        if global_ratio >= self.min_ratio:
            self.log.info('Global ratio above ' + str(self.min_ratio) + '%, keep the original contact')
        return global_ratio >= self.min_ratio

    def find_contact_by_ai(self, ai_contact, process):
        found_contact = {}
        for key in ai_contact:
            if ai_contact[key] and key in MAPPING.keys():
                found_contact[MAPPING[key]] = ai_contact[key][:254]
                if isinstance(found_contact[MAPPING[key]], list):
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]][0]

                if key in ('LASTNAME', 'COMPANY', 'CITY'):
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]].upper()
                elif key == 'FIRSTNAME':
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]].capitalize()
                elif key == 'EMAIL':
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]].lower()
                elif key == 'POSTAL_CODE' and len(found_contact[MAPPING[key]]) != 5:
                    found_contact[MAPPING[key]] = ''

        contact = {}
        contact_mail = {}
        if (('email' not in found_contact or not found_contact['email']) and
                ('phone' not in found_contact or not found_contact['phone'])):
            self.start()
            self.join()
            if self.contact:
                if 'email' in self.contact and self.contact['email']:
                    found_contact['email'] = self.contact['email']
                if 'phone' in self.contact and self.contact['phone']:
                    found_contact['phone'] = self.contact['phone']

        if 'email' in found_contact and found_contact['email']:
            if not self.contact:
                contact = self.web_service.retrieve_contact_by_mail(found_contact['email'])
            else:
                contact = self.contact

            if contact:
                self.log.info('Contact found using email : ' + found_contact['email'])
                contact = self.web_service.retrieve_contact_by_id(contact['id'])
                match_contact = self.compare_contact(contact, found_contact)
                if match_contact:
                    return contact
                self.log.info(f'Global ratio under {self.min_ratio}%, search using phone')

        if 'phone' in found_contact and found_contact['phone']:
            if not self.contact:
                contact = self.web_service.retrieve_contact_by_phone(found_contact['phone'])
            else:
                contact = self.contact

            tmp_contact = False
            if contact:
                tmp_contact = contact

            if isinstance(found_contact['phone'], list):
                found_contact['phone'] = found_contact['phone'][0]

            if contact:
                self.log.info('Contact found using phone : ' + found_contact['phone'])
                contact = self.web_service.retrieve_contact_by_id(contact['id'])
                match_contact = self.compare_contact(contact, found_contact)
                if match_contact:
                    return contact
                self.log.info(f'Global ratio under {self.min_ratio}%, insert temporary contact')
            else:
                if tmp_contact:
                    contact = tmp_contact

        found_contact['status'] = 'TMP'
        if not contact:
            if contact_mail:
                self.log.info('No contact found using phone, use contact found using email')
                contact = contact_mail
            else:
                self.log.info('No contact found, create a temporary contact')

        if 'sender_custom_fields' in process and process['sender_custom_fields']:
            found_contact['customFields'] = json.loads(process['sender_custom_fields'])

        res, temporary_contact = self.web_service.create_contact(found_contact)
        if res:
            self.log.info('Temporary contact created with success : ' + str(temporary_contact['id']))
            if contact:
                contact['externalId'] = {
                    'ia_tmp_contact_id': temporary_contact['id']
                }

                if 'civility' in contact and contact['civility'] and 'id' in contact['civility']:
                    contact['civility'] = contact['civility']['id']

                self.web_service.update_contact_external_id(contact)
                return contact
        else:
            self.log.error('Error while creating temporary contact')
            return False
        return temporary_contact
