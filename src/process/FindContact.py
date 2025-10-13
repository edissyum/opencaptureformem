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
import re
import json
import torch
from thefuzz import fuzz
from threading import Thread

import transformers
from PIL import Image
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode

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
    'FIRSTNAME': 'firstname',
}

def build_transform(input_size):
    IMAGENET_MEAN = (0.485, 0.456, 0.406)
    IMAGENET_STD  = (0.229, 0.224, 0.225)
    MEAN, STD = IMAGENET_MEAN, IMAGENET_STD
    transform = T.Compose([
        T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
        T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
        T.ToTensor(),
        T.Normalize(mean=MEAN, std=STD)
    ])
    return transform

def find_closest_aspect_ratio(aspect_ratio, target_ratios, width, height, image_size):
    best_ratio_diff = float('inf')
    best_ratio = (1, 1)
    area = width * height
    for ratio in target_ratios:
        target_aspect_ratio = ratio[0] / ratio[1]
        ratio_diff = abs(aspect_ratio - target_aspect_ratio)
        if ratio_diff < best_ratio_diff:
            best_ratio_diff = ratio_diff
            best_ratio = ratio
        elif ratio_diff == best_ratio_diff:
            if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                best_ratio = ratio
    return best_ratio

def dynamic_preprocess(image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
    orig_width, orig_height = image.size
    aspect_ratio = orig_width / orig_height
    target_ratios = set((i, j) for n in range(min_num, max_num + 1)
                        for i in range(1, n + 1) for j in range(1, n + 1)
                        if i * j <= max_num and i * j >= min_num)
    target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])
    target_aspect_ratio = find_closest_aspect_ratio(aspect_ratio, target_ratios, orig_width, orig_height, image_size)

    target_width  = image_size * target_aspect_ratio[0]
    target_height = image_size * target_aspect_ratio[1]
    blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

    resized_img = image.resize((target_width, target_height), resample=Image.BILINEAR)
    processed_images = []
    stride = (target_width // image_size)
    for i in range(blocks):
        x0 = (i % stride) * image_size
        y0 = (i // stride) * image_size
        box = (x0, y0, x0 + image_size, y0 + image_size)
        processed_images.append(resized_img.crop(box))

    if use_thumbnail and len(processed_images) != 1:
        processed_images.append(image.resize((image_size, image_size), resample=Image.BILINEAR))
    return processed_images

def load_image(image_file, input_size=448, max_num=12):
    image = image_file.convert('RGB')
    transform = build_transform(input_size=input_size)
    images = dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
    pixel_values = torch.stack([transform(im) for im in images])
    return pixel_values

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
                    key_dict += output[i]; i += 1
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

def run_inference_sender(model_path, img):
    N = max(1, min(8, torch.get_num_threads()))  # pick a sensible default
    os.environ.setdefault("OMP_NUM_THREADS", str(N))
    os.environ.setdefault("MKL_NUM_THREADS", str(N))
    torch.set_num_threads(int(os.environ["OMP_NUM_THREADS"]))
    torch.set_num_interop_threads(1)
    
    model = transformers.AutoModel.from_pretrained(
        model_path,
        torch_dtype=torch.float32,
        load_in_8bit=False,
        local_files_only=True,
        use_flash_attn=False,
        trust_remote_code=True,
        device_map="cpu",
    )
    model.eval()

    tokenizer = transformers.AutoTokenizer.from_pretrained(model_path, trust_remote_code=True, use_fast=True, local_files_only=True)

    pixel_values = load_image(img, max_num=12).to(torch.float32)

    generation_config = dict(
        max_new_tokens=256,
        do_sample=False,
        eos_token_id=tokenizer.eos_token_id
    )

    question = "<image> Extract all data from the image in a dictionnary."

    data = {}
    with torch.inference_mode():
        response = model.chat(tokenizer, pixel_values, question, generation_config)
        data = parse_output(response)
    print(data)
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
            if key == 'addresses':
                if ai_contact[key]:
                    if 'address' in ai_contact[key][0] and ai_contact[key][0]['address']:
                        found_contact[MAPPING['address']] = ai_contact[key][0]['address']
                    if 'postal_code' in ai_contact[key][0] and ai_contact[key][0]['postal_code']:
                        found_contact[MAPPING['postal_code']] = ai_contact[key][0]['postal_code']
                    if 'city' in ai_contact[key][0] and ai_contact[key][0]['city']:
                        found_contact[MAPPING['city']] = ai_contact[key][0]['city']
                    if 'additional_address' in ai_contact[key][0] and ai_contact[key][0]['additional_address']:
                        found_contact[MAPPING['additional_address']] = ai_contact[key][0]['additional_address']
                continue
            if ai_contact[key] and key in MAPPING.keys():
                found_contact[MAPPING[key]] = ai_contact[key][:254]
                if isinstance(found_contact[MAPPING[key]], list):
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]][0]

                if key in ('lastname', 'company', 'city'):
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]].upper()
                elif key == 'firstname':
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]].capitalize()
                elif key == 'email':
                    found_contact[MAPPING[key]] = found_contact[MAPPING[key]].lower()
                elif key == 'postal_code' and len(found_contact[MAPPING[key]]) != 5:
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
