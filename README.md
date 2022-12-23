![Logo Open-Capture](https://edissyum.com/wp-content/uploads/2019/08/OpenCaptureForMaarch.png)

Version 3.1.5_19.04_oauth


# Open-Capture for Maarch  19.04
Open-Capture is a **free and Open Source** software under **GNU General Public License v3.0**.

The functionnalities of OC for Maarch are :

 - Process PDF or image file as input
 - Process files by batch (in a given folder) or single
 - Output searchable PDF, one or multi pages
 - Split PDF using QRCode and rename splitted PDF file using QRCode content
 - OCR and text recognition :
    - Find a date and use it as metadata
    - Find a mail, phone or URL to reconciliate with an existing contact in Maarch
    - Find a subject and use it as metadata
 - Insert documents in Maarch with pre-qualified metadata :
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
- Ubuntu 18.04 with Python 3.7.4 & Tesseract v4.0.0-beta.1 (Used for development)
- Ubuntu 18.10 with Python 3.7.1 & Tesseract v4.0.0-beta.1
- Ubuntu Server 18.10 with Python 3.7.1 or Python 3.6.7 & Tesseract v4.0.0-beta.1
- Ubuntu Server 18.04.3 with Python 3.6.9 & Tesseract v4.0.0-beta.1
- Ubuntu Server 19.10 with Python 3.7.5 & Tesseract v4.1.0
- Debian 9.8 with Python 3.5.3 & Tesseract v3.04.01 or Tesseract V4.0.0 (stretch-backports)
- Debian 9.6 with Python 3.5.3 & Tesseract v3.04.01 or Tesseract V4.0.0 (stretch-backports)
- Debian 10 with Python 3.7.3 Tesseract V4.0.0

## Install Open-Capture for Maarch
Nothing as simple as that :

    $ sudo mkdir /opt/maarch/ && sudo chmod -R 775 /opt/maarch/ && sudo chown -R your_user:your_group /opt/maarch/
    $ sudo apt install git
    $ git clone -b 3.1.5_19.04 https://github.com/edissyum/opencaptureformaarch /opt/maarch/OpenCapture/
    $ cd /opt/maarch/OpenCapture/install/

The ./Makefile install all the necessary packages and create the service, but you may want to change the User and Group (edissyum by default) so just open the ./Makefile and change lines **84**, **85** and **123**
You have the choice between using supervisor or basic systemd
Supervisor is useful if you need to run multiple instance of Open-Capture in parallel
Systemd is perfect for one instance

    $ chmod u+x Makefile
    $ sudo ./Makefile
        # Answer the few questions asked at launch
        # Go grab a coffee ;)
    $ cp /opt/maarch/OpenCapture/src/config/config.ini.default /opt/maarch/OpenCapture/src/config/config.ini
    $ cp /opt/maarch/OpenCapture/src/config/mail.ini.default /opt/maarch/OpenCapture/src/config/mail.ini

Don't forget to modify the two config file with your specifics need. If you need help, you have more informations about the <code>src/config/config.ini</code> settings into the **_Configuration_** section.
For the <code>src/config/mail.ini</code> just check the **_IMAP Connector (Open-Capture MailCollect Module)_** section.

Fill the `typist` with the user_id who scan document (in the default Maarch installation it's `bblier`)

  It will install all the needed dependencies, compile and install Tesseract V4.0.0 with french and english locale. If you need more locales, just do :

    $ sudo apt install tesseract-ocr-langcode

  Here is a list of all available languages code : https://www.macports.org/ports.php?by=name&substr=tesseract-

## Set up the incron & the cron to start the service
We want to automatise the capture of document. For that, we'll use incrontab.
First, add your user into the following file :

> /etc/incron.allow

Then use <code>incrontab -e</code> and put the following line :

    /path/to/capture/ IN_CLOSE_WRITE,IN_MOVED_TO /opt/maarch/OpenCapture/scripts/launch_IN.sh $@/$#

We use worker and jobs to enqueue process. The worker is encapsulated into a service who needs to be started in order to run the process. It's needed to cron the boot of the service at every restart, by the root user :

    $ sudo crontab -e

   And add

    @reboot systemctl start oc-worker.service

## Configuration
The file <code>src/config/config.ini</code> is splitted in different categories

 - Global
    - Choose the number of threads used to multi-threads (5 by defaults)
    - Resolution and compressionQuality when PDF are converted to JPG
    - List of char to be remove to sanitize detected email
    - Set the default path of the project (default : **/opt/maarch/OpenCapture/**)
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
  - OCForMaarch
    - Link to **/rest** API of Maarch with User and Password
    - Do not process date when difference between date found and today date is older than timeDelta. -1 to disable it
    - Uppercase the subject automatically
  - OCForMaarch_**process_name**
     - Default metadata to insert documents (doctype, status, typist, priority, format, model_id and destination)

### Utilisations
Here is some examples of possible usages in the launch_XX.sh script:

    $ python3 /opt/maarch/OpenCapture/launch_worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -f file.pdf -process incoming
    $ python3 /opt/maarch/OpenCapture/launch_worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -p /path/to/folder/
    $ python3 /opt/maarch/OpenCapture/launch_worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -p /path/to/folder/ --read-destination-from-filename
    $ python3 /opt/maarch/OpenCapture/launch_worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -p /path/to/folder/ --read-destination-from-filename -resid 100 -chrono MAARCH/2019D/1

--read-destination-from-filename is related to separation with QR CODE. It's reading the filename, based on the **divider** option in config.ini, to find the entity ID
-f stands for unique file
-p stands for path containing PDF/JPG files and process them as batch
-process stands for process mode (incoming or outgoing. If none, incoming will be choose)


## WebServices for Maarch 19.04
In order to reconciliate a contact it's needed to contact the Maarch database. For that 2 little PHP web services were developed.
First, go into your Maarch installation (e.g : **/var/www/maarch_courrier**).

The list of files needed to be modify is in install/Maarch with the correct structure. Each modifications on files are between the following tags :

    // NCH01
        some code...
    // END NCH01

Just report the modifications onto you Maarch installation

## Various
If you want to generate PDF/A instead of PDF, you have to do the following :

    $ cp install/sRGB_IEC61966-2-1_black_scaled.icc /usr/share/ghostscript/X.XX/
    $ nano +8 /usr/share/ghostscript/X.XX/lib/PDFA_def.ps
    Replace : %/ICCProfile (srgb.icc) % Customise
    By : /ICCProfile (/usr/share/ghostscript/X.XX/sRGB_IEC61966-2-1_black_scaled.icc)   % Customize

# IMAP Connector (Open-Capture MailCollect Module)
![Logo Open-Capture MailCollect](https://edissyum.com/wp-content/uploads/2020/04/0_Open-Capture_MailCollect_Module.png)

You have the possibility to capture e-mail directly from your inbox.  
    
Just edit the <code>/opt/maarch/OpenCapture/src/config/mail.ini</code> and add your process. Modify the default process <code>MAIL_1</code> with your informations (host, port, login, pwd etc..)
Add other process if you want to capture more than one mailbox or multiple folder,
by copying <code>MAIL_1</code> and just change the name.

IMPORTANT : Do not put space into process name

I you have multiple processes, don't forget to copy <code>MAIL_1</code> section into <code>/opt/maarch/OpenCapture/src/config/mail.ini</code> and that's all. 
The <code>launch_MAIL.sh</code> automatically loop into all the processes and launch them   

Don't forget to fill the `typist` with the user_id who scan document (in the default Maarch installation it's `bblier`)

Here is a short list of options you have for mail process into <code>/opt/maarch/OpenCapture/src/config/mail.ini</code>

  - hostname, port, login, password : All the informations about the inbox 
  - isSSL : Choose between True or False. It will specify if we have to you IMAP4 or IMAP4_SSL. If <code>isSSL</code> is True, port must be 993
  - folderToCrawl : Which folder needed to be crawl by connector to process email
  - folderDestination : if <code>actionAfterProcess</code> is <code>move</code> specify in which folder we had to move the e-mail after process
  - folderTrash : if <code>actionAfterProcess</code> is <code>delete</code>, specify the name of trash folder. If we use the IMAP delete function, the mail cannot be retrieve
  - actionAfterProcess : <code>move</code>, <code>delete</code> or <code>none</code>
  - importOnlyAttachments : If <code>True</code> skip the e-mail body content and process only attachments as a new document (same process as default Open-Capture process)
  - from_is_reply_to : In some case, the <code>from</code> field is a no-reply email and the real from e-mail is in reply-to. Put <code>True</code> if it's the case
    If this option is enabled but `reply_to` field is empty, the `from` field will be used

You could also set-up notifications if an error is thrown while collect mail with IMAP.
For that, just fill the following informations : 
  - smtp_notif_on_error : enable the notifications service, or not
  - smtp_host, smtp_port, smtp_login, smtp_pwd : SMTP server informations
  - smtp_ssl, smtp_starttls : Enable SSL AND/OR STARTTLS
  - smtp_dest_admin_mail : e-mail which receive notifications
  - smtp_delay : To avoid spam. Prevent sending a new mail if the last one was sent less than X minutes ago. 0 to disable it

Hint : To know the specific name of different folder, just launch the script <code>/opt/maarch/OpenCapture/scripts/MailCollect/check_folders.py</code> with your hosts informations

To makes the capture of e-mail automatic, just cron the <code>launch_MAIL.sh</code> script : 

     */5 8-18 * * 1-5   /opt/maarch/OpenCapture/scripts/launch_MAIL.sh >/dev/null 2>&1

By default, run the script at every 5th minute past every hour from 8 through 18 on every day-of-week from Monday through Friday.

## Clean MailCollect batches
When a batch is launch it will create a folder with a backup of the e-mail and the log file associated
To avoid lack of memory on the server, do not forget to cron the <code>clean.sh</code> script : 

    0 2 * * 1-5   /opt/maarch/OpenCapture/scripts/MailCollect/clean.sh >/dev/null 2>&1

By default, run the script at 2 AM on every day-of-week from Monday through Friday and it will 
delete all the batch folder older than 7 days

# Update Open-Capture For Maarch 19.04
The process of update is very simple. But before you need to modify the file and change lines **54** to put the user and group you want instead of default (edissyum) :

    $ cd /opt/maarch/OpenCapture/install/
    $ chmod u+x update.sh
    $ sudo ./update.sh

# Informations
## QRCode separation
Maarch permit the creation of separator, with QRCODE containing the ID of an entity. "DGS" for example. If enabled is config.ini, the separation allow us to split a PDF file containing QR Code and create PDF with a filename prefixed with the entity ID. e.g : "DGS_XXXX.pdf"

## Apache modifications
In case some big files would be sent, you have to increase the **post_max_size** parameter on the following file

>/etc/php/7.X/apache2/php.ini

By default it is recommended to replace **8M** by **20M** or more if needed

# LICENSE
Open-Capture for Maarch is released under the GPL v3.
