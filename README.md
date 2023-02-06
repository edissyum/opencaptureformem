![Logo Open-Capture](https://edissyum.com/wp-content/uploads/2022/12/open_capture_for_mem_courrier.png)

# Open-Capture for MEM Courrier 21.03
Open-Capture for MEM Courrier is a **free and Open Source** software under **GNU General Public License v3.0**.

The functionnalities of Open-Capture for MEM Courrier are :

 - Process PDF or image file as input
 - Process files by batch (in a given folder) or single
 - Output searchable PDF, one or multi pages
 - Split PDF using QRCode and rename splitted PDF file using QRCode content
 - OCR and text recognition :
    - Find a date and use it as metadata
    - Find a mail or a phone to reconciliate with an existing contact in MEM Courrier
    - Find a subject and use it as metadata
 - Insert documents in MEM Courrier with pre-qualified metadata :
    - Destination with QRCode
    - Date, contact, object with text recognition
 - Output PDF or PDF/A file
 - Works with **fr_FR** and **en_EN** locales
 - Fully logged, infos and errors
 - For now it deals only with **PDF** or **JPG** files
 - Check integrity of a file to avoid processing incomplete files
 - Handle different process type (List of default process in config.ini : <code>processAvailable</code>) 
 - QR Code recognition from a file to reconcile it with the original document

# Installation
## Linux Distributions
Tested with :
- Debian 9.6 with Python 3.5.3 & Tesseract v3.04.01 or Tesseract V4.0.0 (stretch-backports)
- Debian 9.8 with Python 3.5.3 & Tesseract v3.04.01 or Tesseract V4.0.0 (stretch-backports)
- Debian 10 with Python 3.7.3 Tesseract V4.0.0
- Debian 11.X with Python 3.9.2 Tesseract V4.1.1


## Install Open-Capture for MEM Courrier
Nothing as simple as that :

    sudo mkdir /opt/mem/ && sudo chmod -R 775 /opt/mem/ && sudo chown -R $(whoami):$(whoami) /opt/mem/
    sudo apt install git
    latest_tag=$(git ls-remote --tags --sort="v:refname" https://github.com/edissyum/opencaptureformem.git *20.03 | tail -n1 |  sed 's/.*\///; s/\^{}//')
    git clone -b $latest_tag https://github.com/edissyum/opencaptureformem /opt/mem/opencapture/
    cd /opt/mem/opencapture/install/

The ./Makefile install all the necessary packages and create the service
You have the choice between using supervisor or basic systemd
Supervisor is useful if you need to run multiple instance of Open-Capture in parallel
Systemd is perfect for one instance

    chmod u+x Makefile
    sudo ./Makefile
      # Answer the few questions asked at launch
      # Go grab a coffee ;)

It will install all the needed dependencies, compile and install Tesseract V4.0.0 with french and english locale. If you need more locales, just do :

    sudo apt install tesseract-ocr-<langcode>

  Here is a list of all available languages code : https://www.macports.org/ports.php?by=name&substr=tesseract-

Don't forget to modify the two config file with your specifics need. If you need help, you have more informations about the <code>src/config/config.ini</code> settings into the **_Configuration_** section.
For the <code>src/config/mail.ini</code> just check the **_IMAP Connector (Open-Capture MailCollect Module)_** section.

In most cases you had to modify the <code>/etc/ImageMagick-6/policy.xml</code> file to comment the following line (~ line 94) and then restart the oc-worker:

    <policy domain="coder" rights="none" pattern="PDF" />


    sudo systemctl restart oc-worker.service

Fill the `typist` with the user_id who scan document (in the default MEM Courrier installation it's `bblier`)

## Set up the incron & the cron to start the service
We want to automatise the capture of document. For that, we'll use incrontab.
First, add your user into the following file :

> /etc/incron.allow

Then use <code>incrontab -e</code> and put the following line :

    /path/to/capture/ IN_CLOSE_WRITE,IN_MOVED_TO /opt/mem/opencapture/scripts/launch_IN.sh $@/$#
    
## Configuration
The file <code>src/config/config.ini</code> is splitted in different categories

 - Global
    - Choose the number of threads used to multi-threads (5 by defaults)
    - Resolution and compressionQuality when PDF are converted to JPG
    - List of char to be remove to sanitize detected email
    - Set the default path of the project (default : **/opt/mem/opencapture/**)
    - tmpPath, no need to modify
    - errorPath, no need to modify
    - Path to the logFile, no need to modify
 - Locale
    - Choose the locale for text recognition (about date format and regex), by default it's **fr_FR** or **en_EN** but you can add more (see further in the README)
    - Choose the locale of OCR (see the langcodes of Tesseract)
    - Path for the locale JSON file for date (related to the first option of Locale), no need to modify
 - Regex
    - Add extensions to detect URL during text detection
 - Separator_QR
    - Enable or disable
    - Choose to export PDF or PDF/A
    - Path to export PDF or PDF/A, no need to modify
    - Tmp path, no need to modify
    - Modify the default divider if needed (eg. DGS_XXX.pdf or DGS-XXX.pdf)
  - Open-Capture for MEM Courrier
    - Link to **/rest** API of MEM Courrier with User and Password
    - Do not process date when difference between date found and today date is older than timeDelta. -1 to disable it
    - Uppercase the subject automatically
  - OCForMEM_**process_name**
     - Default metadata to insert documents (doctype, status, typist, priority, format, model_id and destination)

To activate auto recontiliation for MEM Courrier outgoing document you must set this list of values in config.ini file (REATTACH_DOCUMENT part) :

    - Active : activate the process (True or False)
    - Action : reattach action id in MEM Courrier
    - group  : id of the scan group in MEM Courrier
    - basket : basket id linked to the group in MEM Courrier
    - status : the new status after reattach

### Utilisations
Here is some examples of possible usages in the launch_XX.sh script:

    python3 /opt/mem/opencapture/launch_worker.py -c /opt/mem/opencapture/src/config/config.ini -f file.pdf -process incoming
    python3 /opt/mem/opencapture/launch_worker.py -c /opt/mem/opencapture/src/config/config.ini -p /path/to/folder/
    python3 /opt/mem/opencapture/launch_worker.py -c /opt/mem/opencapture/src/config/config.ini -p /path/to/folder/ --read-destination-from-filename
    python3 /opt/mem/opencapture/launch_worker.py -c /opt/mem/opencapture/src/config/config.ini -p /path/to/folder/ --read-destination-from-filename -resid 100 -chrono MAARCH/2019D/1

--read-destination-from-filename is related to separation with QR CODE. It's reading the filename, based on the **divider** option in config.ini, to find the entity ID
-f stands for unique file
-p stands for path containing PDF/JPG files and process them as batch
-process stands for process mode (incoming or outgoing. If none, incoming will be choose)

## Various
If you want to generate PDF/A instead of PDF, you have to do the following :

    cp install/sRGB_IEC61966-2-1_black_scaled.icc /usr/share/ghostscript/X.XX/
    nano +8 /usr/share/ghostscript/X.XX/lib/PDFA_def.ps
    
    Replace : %/ICCProfile (srgb.icc) % Customise
    By : /ICCProfile (/usr/share/ghostscript/X.XX/sRGB_IEC61966-2-1_black_scaled.icc)   % Customize

# Open-Capture MailCollect Module
![Logo Open-Capture MailCollect](https://edissyum.com/wp-content/uploads/2020/04/0_Open-Capture_MailCollect_Module.png)

You have the possibility to capture e-mail directly from your inbox.
    
Just edit the <code>/opt/mem/opencapture/src/config/mail.ini</code> and add your process. Modify the default process <code>MAIL_1</code> with your informations (host, port, login, pwd etc..)
If you want to have the from, to, cc and replyTo metadatas you have to create the custom fields into MEM Courrier superadmin dashboard and modify the ID into the config file (8, 9, 10, 11 by default) 
Add other process if you want to capture more than one mailbox or multiple folder,
by copying <code>MAIL_1</code> and just change the name.

IMPORTANT : Do not put space into process name

I you have multiple processes, don't forget to copy <code>MAIL_1</code> section into <code>/opt/mem/opencapture/src/config/mail.ini</code> and that's all. 
The <code>launch_MAIL.sh</code> automatically loop into all the processes and launch them

Don't forget to fill the `typist` with the user_id who scan document (in the default MEM Courrier installation it's `bblier`)

Here is a short list of options you have for mail process into <code>/opt/mem/opencapture/src/config/mail.ini</code>

  - hostname, port, login, password : All the informations about the inbox 
  - securedConnection : Choose between SSL or STARTTLS or False. It will specify if we have to you IMAP4 or IMAP4_SSL. If <code>securedConnection</code> is SSL, port must be a secured port (e.g : 993)
  - folderToCrawl : Which folder needed to be crawl by connector to process email
  - generate_chrono : If true, MEM Courrier will generate a chrono number
  - forceUtf8 : If true, force mail encoding into UTF8 to avoid problems
  - isForm : If True, check if e-mail contains a forms using <code>forms_identifier.json</code> file
  - priorityToMailSubject : If true, use the subject from mail and do not search subject into the mail
  - priorityToMailDate : If true, use the date from mail and do not search subject into the mail
  - priorityToMailFrom : If true, use the FROM field from mail and do not search subject into the mail
  - folderDestination : if <code>actionAfterProcess</code> is <code>move</code> specify in which folder we had to move the e-mail after process
  - folderTrash : if <code>actionAfterProcess</code> is <code>delete</code>, specify the name of trash folder. If we use the IMAP delete function, the mail cannot be retrieve
  - actionAfterProcess : <code>move</code>, <code>delete</code> or <code>none</code>
  - importOnlyAttachments : If <code>True</code> skip the e-mail body content and process only attachments as a new document (same process as default Open-Capture process)
  - from_is_reply_to : In some case, the <code>from</code> field is a no-reply email and the real from e-mail is in reply-to. Put <code>True</code> if it's the case
    If this option is enabled but `reply_to` field is empty, the `from` field will be used
  - custom_fields : If you need to specify a static custom value, use this and fill it like this : "{"6": "VALUE"}"
  - custom_mail : The id of the custom where the email(s) adress(es) will be stored

You could also set-up notifications if an error is thrown while collect mail with IMAP.
For that, just fill the following informations : 
  - smtp_notif_on_error : enable the notifications service, or not
  - smtp_host, smtp_port, smtp_login, smtp_pwd : SMTP server informations
  - smtp_ssl, smtp_starttls : Enable SSL AND/OR STARTTLS
  - smtp_dest_admin_mail : e-mail which receive notifications
  - smtp_delay : To avoid spam. Prevent sending a new mail if the last one was sent less than X minutes ago. 0 to disable it

Hint : If you need to test the SMTP settings, just launch the script <code>/opt/mem/opencapture/scripts/MailCollect/smtp_test.py</code> with your hosts informations
Hint2 : To know the specific name of different folder, just launch the script <code>/opt/mem/opencapture/scripts/MailCollect/check_folders.py</code> with your hosts informations

To makes the capture of e-mail automatic, just cron the <code>launch_MAIL.sh</code> script :

     */5 8-18 * * 1-5   /opt/mem/opencapture/scripts/launch_MAIL.sh >/dev/null 2>&1

By default, run the script at every 5th minute past every hour from 8 through 18 on every day-of-week from Monday through Friday.

## Possible errors

If you have the following error when running your MailCollect scripts : <code>ssl.SSLError: [SSL: UNSUPPORTED_PROTOCOL] unsupported protocol (_ssl.c:1056)</code>
One of the possibility to solve is the following :

    sudo nano /etc/ssl/openssl.cnf

Find the <code>minProtocol</code> options and set it to TLSv1.0

## Clean MailCollect batches
When a batch is launch it will create a folder with a backup of the e-mail and the log file associated
To avoid lack of memory on the server, do not forget to cron the <code>clean.sh</code> script : 

    0 2 * * 1-5   /opt/mem/opencapture/scripts/MailCollect/clean.sh >/dev/null 2>&1

By default, run the script at 2 AM on every day-of-week from Monday through Friday and it will 
delete all the batch folder older than 7 days

# Update Open-Capture For MEM Courrier 20.03 and 21.03
The process of update is very simple. But before you need to modify the file and change lines **54** to put the user and group you want instead of default (edissyum) :

    cd /opt/mem/opencapture/install/
    chmod u+x update.sh
    sudo ./update.sh

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


# Informations
## QRCode separation
MEM Courrier permit the creation of separator, with QRCODE containing the ID of an entity. "DGS" for example. If enabled is config.ini, the separation allow us to split a PDF file
containing QR Code and create PDF with a filename prefixed with the entity ID. e.g : "DGS_XXXX.pdf"
On the new version 20.03 the separator now put entity ID instead of entity short label. But there is no issue.

    WARNING : In MEM Courrier parameters, set QRCodePrefix to 1 instead of 0

Now it's possible to send attachments with QR Code Separation. If you have a resume and a motivation letter, start with MEM Courrier entity Separation QR Code, then the resume. Add the PJ_SEPARATOR.pdf
and then the motivation letter. In MEM Courrier you'll have the resume as principal document and the motivation letter as attachment.

## Apache modifications
In case some big files would be sent, you have to increase the **post_max_size** parameter on the following file

>/etc/php/7.X/apache2/php.ini

By default it is recommended to replace **8M** by **20M** or more if needed

# LICENSE
Open-Capture for MEM Courrier is released under the GPL v3.
