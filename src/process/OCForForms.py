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
import shutil
import locale
from datetime import datetime
from bs4 import BeautifulSoup

def extract_address_from_format(line, address_format, log):
    line = re.sub(r'\s+', ' ', line).strip()
    line = line.replace(" ,", ",")

    field_regex_map = {
        "addressNumber": r"\d+",
        "addressStreet": r"[A-Za-zÀ-ÿ'\s\-]+",
        "addressPostcode": r"\d{5}",
        "addressTown": r"[A-Za-zÀ-ÿ'\s\-]+",
        "addressCountry": r"[A-Za-zÀ-ÿ'\s\-]+",
        "addressLatitude": r"[-+]?\d*\.\d+",
        "addressLongitude": r"[-+]?\d*\.\d+"
    }

    pattern = address_format
    for placeholder, regex in field_regex_map.items():
        pattern = pattern.replace(placeholder, f"(?P<{placeholder}>{regex})")

    match = re.search(pattern, line)
    if match:
        log.info("Address match found:" + str(match.groupdict()))
        return match.groupdict()

    log.warning("No address match found.")
    return {}

def process_form(args, config, config_mail, log, web_service, process_name, file):
    json_identifier = config.cfg['GLOBAL']['formpath'] + '/forms_identifier.json'
    if os.path.isfile(json_identifier):
        with open(json_identifier, 'r', encoding='UTF-8') as identifier:
            identifier = identifier.read()
            identifier = json.loads(identifier)

        process_found = False
        process = False
        for _process in identifier:
            subject = args['data']['subject']
            keyword_subject = identifier[_process]['keyword_subject']

            if keyword_subject in subject:
                if 'model_id' in identifier[_process] and identifier[_process]['model_id'] is not None:
                    args['data']['modelId'] = identifier[_process]['model_id']

                if 'destination' in identifier[_process] and identifier[_process]['destination'] is not None:
                    args['data']['destination'] = identifier[_process]['destination']

                if 'dest_user' in identifier[_process] and identifier[_process]['dest_user'] is not None:
                    args['data']['dest_user'] = identifier[_process]['dest_user']

                process_found = True
                process = _process

                if identifier[process].get('custom_fields') is not None:
                    args['data']['customFields'].update(identifier[_process].get('custom_fields'))

                if identifier[process].get('destination') is not None:
                    destination = identifier[_process].get('destination')
                    if not isinstance(destination, int):
                        destinations = web_service.retrieve_entities()
                        for dest in destinations['entities']:
                            if destination == dest['id']:
                                destination = dest['serialId']
                                if args.get('isMail') is not None and args.get('isMail') is True:
                                    args['data']['destination'] = destination
                    else:
                        args['data']['destination'] = destination

                if identifier[process].get('doctype') is not None:
                    args['data']['doctype'] = identifier[_process].get('doctype')

                if identifier[process].get('priority') is not None:
                    args['data']['priority'] = identifier[_process].get('priority')

                if identifier[process].get('status') is not None:
                    args['data']['status'] = identifier[_process].get('status')

                log.info('The e-mail will use the "' + process + '" form process')

        # If a process is found, use the specific JSON file to search data using REGEX
        if process_found:
            json_file = config.cfg['GLOBAL']['formpath'] + '/' + identifier[process]['json_file']
            if os.path.isfile(json_file):
                with open(json_file, 'r', encoding='UTF-8') as data:
                    data = json.loads(data.read())['FIELDS']
                    contact_fields = data['CONTACT']['data']
                    contact_table = data['CONTACT']['table']
                    letterbox_fields = data['LETTERBOX']['data']

                with open(args['file'], 'r', encoding='UTF-8') as file_content:
                    text_parsed = BeautifulSoup(file_content, 'html.parser')

                lines = []

                cpt = 0
                for row in text_parsed.find_all('tr'):
                    line = ''
                    for el in row.find_all('td'):
                        if el.text.strip() not in line:
                            line += el.text.strip() + ' '
                    lines.append(line.strip())
                    cpt += 1

                text = text_parsed.findAll(['p'])
                if lines:
                    text = text + lines

                results = {
                    contact_table: {}
                }
                if (not text and file_content) or len(text) <= 1:
                    with open(args['file'], 'r', encoding='UTF-8') as file_content:
                        text_parsed = file_content.read()
                        text_parsed = re.sub(r'\s+', ' ', text_parsed)
                        text_parsed = re.sub(r'\t', '', text_parsed)
                        text_parsed = re.sub(r'<br>', '\n', text_parsed)
                        text_parsed = text_parsed.split('\n')

                        text = []
                        for line in text_parsed:
                            if line:
                                text.append(line)

                for line in text:
                    if not isinstance(line, str):
                        line = line.get_text()
                    line = line.replace('<br>', '').replace('&nbsp;', '')
                    line = line.replace('<b>', '').replace('</b>', '')

                    for field in contact_fields:
                        regex = contact_fields[field]['regex']
                        column = contact_fields[field]['column']
                        res = re.findall(r'' + regex, line)
                        if res and res[0].strip():
                            if 'correspondance_table' in contact_fields[field] and contact_fields[field]['correspondance_table']:
                                for correspondance in contact_fields[field]['correspondance_table']:
                                    if res[0].lower() == correspondance.lower():
                                        results[contact_table][column] = contact_fields[field]['correspondance_table'][correspondance]
                            else:
                                results[contact_table][column] = res[0].strip()

                    for field in letterbox_fields:
                        regex = field['regex']
                        column = field['column']
                        regex_return = re.findall(r'' + regex, line.replace('\n', ' '))
                        if regex_return:
                            text_data = regex_return[0].strip()
                            if column != 'custom':
                                if field.get('correspondance_table') is not None and field['correspondance_table'] is not None and field.get('databaseAssociation') is not None and field['databaseAssociation'] is not None:
                                    for correspondance in field['correspondance_table']:
                                        if text_data.lower() == correspondance.lower():
                                            log.info('Found correspondance : ' + correspondance)
                                            field['databaseAssociation']['filterValue'] = field['correspondance_table'][correspondance]
                                            res = web_service.retrieve_data(field['databaseAssociation'])
                                            if res and res[0] and res[0][field['databaseAssociation']['column']] is not None:
                                                log.info('Found data ' + column + ' : ' + str(res[0][field['databaseAssociation']['column']]))
                                                args['data'][column] = str(res[0][field['databaseAssociation']['column']])
                                elif field.get('databaseAssociation') is not None and field['databaseAssociation'] is not None:
                                    field['databaseAssociation']['filterValue'] = text_data
                                    res = web_service.retrieve_data(field['databaseAssociation'])
                                    if res and res[0] and res[0][field['databaseAssociation']['column']] is not None:
                                        log.info('Found data ' + column + ' : ' + str(res[0][field['databaseAssociation']['column']]))
                                        args['data'][column] = str(res[0][field['databaseAssociation']['column']])
                                elif field.get('correspondance_table') is not None and field['correspondance_table'] is not None:
                                    for correspondance in field['correspondance_table']:
                                        if text_data.lower() == correspondance.lower():
                                            log.info('Found correspondance : ' + correspondance)
                                            args['data'][column] = field['correspondance_table'][correspondance]
                                else:
                                    args['data'][column] = re.sub(r'\s+', ' ', text_data)

                            if 'mapping' in field:
                                mapping = field['mapping']
                                if mapping[cpt]['isCustom'] == 'True':
                                    if mapping[cpt]['isAddress'] == 'True':
                                        extracted_address = extract_address_from_format(text_data, mapping[cpt]['addressFormat'], log)
                                        if not extracted_address or extracted_address == {}:
                                            args['data']['customFields'][mapping[cpt]['column']][0]['addressStreet'] = text_data
                                        else:
                                            if 'addressLatitude' in extracted_address:
                                                extracted_address['latitude'] = extracted_address.pop('addressLatitude')
                                            if 'addressLongitude' in extracted_address:
                                                extracted_address['longitude'] = extracted_address.pop('addressLongitude')
                                            args['data']['customFields'][mapping[cpt]['column']][0].update(extracted_address)

                                    elif 'isDate' in mapping[cpt] and mapping[cpt]['isDate'] == 'True':
                                        locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
                                        _date_format = mapping[cpt]['dateFormat']
                                        _date = datetime.strptime(text_data, _date_format)
                                        args['data']['customFields'].update({mapping[cpt]['column']: str(_date)})
                                    else:
                                        args['data']['customFields'].update({mapping[cpt]['column']: text_data})
                                else:
                                    args['data'][column] = text_data
                res_contact = web_service.retrieve_contact_by_mail(results[contact_table]['email'])
                if res_contact:
                    log.info('Contact found using email : ' + results[contact_table]['email'])
                    args['data']['senders'] = [{'id': res_contact['id'], 'type': 'contact'}]
                else:
                    res_contact = web_service.create_contact(results[contact_table])
                    if res_contact[0]:
                        args['data']['senders'] = [{'id': res_contact[1]['id'], 'type': 'contact'}]

                res = web_service.insert_letterbox_from_mail(args['data'], config_mail.cfg[process_name])
                if res:
                    log.info('Insert form from EMAIL OK : ' + str(res))
                    return res

                try:
                    shutil.move(file, config.cfg['GLOBAL']['errorpath'] + os.path.basename(file))
                except shutil.Error as e:
                    log.error('Moving file ' + file + ' error : ' + str(e))
                return False, res

        else:
            log.error('No process was found, the mail will be processed normally')
            return False, 'default'
    else:
        log.error("Could not find JSON config file : " + json_identifier)
