![Logo Open-Capture](https://edissyum.com/wp-content/uploads/2022/12/open_capture_for_mem_courrier.png)

    Link to the full documentation : https://kutt.it/documentOC4MEM

# Open-Capture for MEM Courrier ![](https://img.shields.io/github/v/release/edissyum/opencaptureformem?color=97BF3D&label=Latest%20version) [![Open-Capture For Mem deployment](https://github.com/edissyum/opencaptureformem/actions/workflows/main.yml/badge.svg)](https://github.com/edissyum/opencaptureformem/actions/workflows/main.yml)
Open-Capture for MEM Courrier is a **free and Open Source** software under **GNU General Public License v3.0**.

# Open-Capture MailCollect Forms Module

If you have a mailbox receiving only forms, there is this module. On the <code>src/config/forms/forms_identifier.json</code> you'll choose :

    - The name of the process "Formulaire_1" in the default JSON file
    - keyword_subject --> The keyword we can find in the mail subject to detect the right process
    - model_id --> MEM Courrier model identifier
    - status --> Override the status set in mail.ini (optional)
    - destination --> Override the destination set in mail.ini (optional)
    - doctype --> Override the doctype set in mail.ini (optional)
    - priority --> Override the priority set in mail.ini (optional)
    - json_file --> Name of the JSON file containing all the informations about the form

And in the json_file here is what you can do (ou can use the default one <code>src/config/forms/default_form.json</code>) :

    - In FIELDS -> CONTACTS you'll have the default field. You just have to modify the REGEX if it doesn't match your form
    - In FIELDS -> LETTERBOX you could add your specifics data
        - column --> use a column of the res_letterbox table. If you want to use <code>custom_fields</code> data, put <code>custom</code> in it
        - regex --> regex used to find the data you want
        - mapping --> If column is equal to custom or if you want to split one line into multiple column you have to fill this (you need as many block of mapping as columns you want) :
            - isCustom --> if the data need to be in custom_fields column
            - isAddress --> If true, the bracket value need to be "LATITUDE,LONGITUDE" and the rest, the complete adress
            - column --> put the id of custom_fields (eg: "3") or a column of res_letterbox table

If you want specific data you could use <code>[]</code> into your line. For example you could check the <code>example_form.json</code> and <code>example_form.txt</code> to see the settings

## Use AI
Open-Capture for MEM Courrier is using AI to detect some informations automatically. By now, you can retrieve MEM Courrier destination and type_id.

We can't provide an AI model because it's specific to each company. But we can help you to create yours, contact us.

## API
Open-Capture for MEM Courrier integrate an API that allows you to directly send documents to MEM Courrier.

### Configuration of the API
In order to the API to work, you need to set a robust secret_key in the config.ini file (automatically generated in the install process). This key will be used to authenticate the requests.
```ini
[API]
# Token expiration time in hours
token_expiration_time       = 1
secret_key                  = YOUR_ROBUST_SECRET_KEY

```
You can easily generate / regenerate a secret key, by running the following script :

```bash
cd /opt/edissyum/opencaptureformem/scripts/
chmod u+x regenerate_secret_key.sh
./scripts/regenerate_secret_key.sh
```

You also need to specify the `custom_id` and the `config_file_path` in the `custom.json` file.
```json
[
    {
        "custom_id": "opencaptureformem",
        "config_file_path": "/opt/edissyum/opencaptureformem/src/config/config.ini"
    }
]
```

### Usage of the API

#### Get a token

You first need to get a token by calling the API with your `secret_key` and `custom_id` :

<table>
<tr>
<td> Curl </td> <td> Python </td>
</tr>
<tr>
<td>

```bash
curl \
-X POST \
-H "Content-Type: application/json" \
-d '{"secret_key": "YOUR_SECRET_KEY", "custom_id":"YOUR_CUSTOM_ID"}' \
http://YOUR_SERVER_URL/opencaptureformem/get_token
```

</td>
<td>

```python
import requests

url = "http://YOUR_SERVER_URL/opencaptureformem/get_token"
data = {"secret_key": "YOUR_SECRET_KEY", "custom_id": "YOUR_CUSTOM_ID"}
headers = {"Content-Type": "application/json"}

response = requests.post(url, json=data, headers=headers)

print(response.json() if response.status_code == 200 else f"Erreur: {response.status_code} - {response.text}")
```
</td>
</tr>
</table>

Then you'll get a token that you'll have to use in the next request.

Here are some possible responses :

<table>
<tr>
<td> Status </td> <td> Response </td>
</tr>
<tr>
<td> 200 </td>
<td>

```json
{
    "token":"XXXXXXXX-XXXXXXXXX-XXXXXXXXX-XXXXXXXXX"
}
```

</td>
</tr>
<tr></tr>
<tr>
<td> 400 </td>
<td>

```json
{
    "message":"Invalid secret key"
}
```

</td>
</tr>

<tr></tr>

<tr>
<td> 500 </td>
<td>
Internal Server Error    
</td>
</tr>
</table>

#### Upload files

A request to the API to upload files will look like this :

<table>
<tr>
<td> Curl </td> <td> Python </td>
</tr>
<tr>
<td>

```bash

curl \
-X POST \
-H "Content-Type: application/json" \
-H "Authorization: Bearer GENERATED_TOKEN" \
-d '{
  "files": [{"file_content": "BASE_64_FILE_CONTENT", "file_name": "FILE_NAME"}],
  "custom_id": "YOUR_CUSTOM_ID",
  "process_name": "YOUR_PROCESS_NAME"
}' \
http://YOUR_SERVER_URL/opencaptureformem/upload
```

</td>
<td>

```python
import requests

url = "http://YOUR_SERVER_URL/opencaptureformem/upload"
data = {
    "files": [{"file_content": "BASE_64_FILE_CONTENT", "file_name": "FILE_NAME"}],
    "custom_id": "YOUR_CUSTOM_ID",
    "process_name": "YOUR_PROCESS_NAME"
}
headers = {
    "Authorization": "Bearer GENERATED_TOKEN",
    "Content-Type": "application/json"
}

response = requests.post(url, json=data, headers=headers)

print(response.json() if response.status_code == 200 else f"Erreur: {response.status_code} - {response.text}")
```
</td>
</tr>
</table>


Here are some possible responses :

<table>
<tr>
<td> Status </td> <td> Response </td>
</tr>
<tr>
<td> 200 </td>
<td>

```json
{
    "message":"All files processed successfully"
}
```

</td>
</tr>

<tr></tr>

<tr>
<td> 400 </td>
<td>

```json
{
    "message":"custom_id XXXX not found in custom.json"
}
```

</td>
</tr>

<tr></tr>

<tr>
<td> 400 </td>
<td>

```json
{
    "message":"Each file must have a 'file_name' and 'file_content' key"
}
```

</td>
</tr>

<tr></tr>

<tr>
<td> 500 </td>
<td>
Internal Server Error    
</td>
</tr>
</table>

#### Get process list

A request to the API to get the list of available processes will look like this :

<table>
<tr>
<td> Curl </td> <td> Python </td>
</tr>
<tr>
<td>

```bash

curl \
-X POST \
-H "Content-Type: application/json" \
-H "Authorization: Bearer GENERATED_TOKEN" \
-d '{
  "custom_id": "YOUR_CUSTOM_ID"
}' \
http://YOUR_SERVER_URL/opencaptureformem/get_process_list
```

</td>
<td>

```python
import requests

url = "http://YOUR_SERVER_URL/opencaptureformem/get_process_list"
data = {
    "custom_id": "YOUR_CUSTOM_ID"
}
headers = {
    "Authorization": "Bearer GENERATED_TOKEN",
    "Content-Type": "application/json"
}

response = requests.post(url, json=data, headers=headers)

print(response.json() if response.status_code == 200 else f"Erreur: {response.status_code} - {response.text}")
```
</td>
</tr>
</table>

Here are some possible responses :

<table>
<tr>
<td> Status </td> <td> Response </td>
</tr>
<tr>
<td> 200 </td>
<td>

```json
{
    "processes":["incoming","reconciliation_default","reconciliation_found"]
}
```

</td>
</tr>

<tr></tr>

<tr>
<td> 400 </td>
<td>

```json
{
    "message":"Invalid or expired token"
}
```

</td>
</tr>

<tr></tr>

<tr>
<td> 500 </td>
<td>
Internal Server Error
</td>
</tr>
</table>

# LICENSE
Open-Capture for MEM Courrier is released under the GPL v3.
