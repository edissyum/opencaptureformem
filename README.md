![Logo Open-Capture](https://edissyum.com/wp-content/uploads/2022/12/open_capture_for_mem_courrier.png)

    Link to the full documentation : https://kutt.it/documentationOC4MEM

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

# LICENSE
Open-Capture for MEM Courrier is released under the GPL v3.
