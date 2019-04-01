
# OpenCapture for Maarch  18.10

OpenCapture is a **free and Open Source** software under **GNU General Public License v3.0**.

The functionnalities of OC for Maarch are :

 - Process PDF or image file as input
 - Process files by batch (in a given folder) or single
 - Output searchable PDF, one or multi pages
 - Split PDF using QRCode and rename splitted PDF file using QRCode content
 - OCR and text recognition :
	 - Find a date and use it as metadata
	 - Find a mail or URL to reconciliate with an existing contact in Maarch
	 - Find an object and use it as metadata
 - Insert documents in Maarch with pre-qualified metadata :
	 - Destination with QRCode
	 - Date, contact, object with text recognition
 - Output PDF or PDF/A file
 - Works with **fr_FR** and **en_EN** locales
 - Fully logged, infos and errors
 - For now it deals only with **PDF** or **JPG** files

# Installation

## Pre-requisite

A server running the latest version of Debian. As Tesseract 4.0 is currently not available from strech package, it's needed to compile it. Don't worry and read the following.

## Install OpenCapture for Maarch

Nothing as simple as that :

    $ git clone https://gitlab.com/edissyum/opencapture/ /opt/maarch/OpenCapture/
    $ cd /opt/maarch/OpenCapture/install/
    $ sudo ./Makefile

    $ export LD_LIBRARY_PATH=/usr/local/lib
    $ export TESSDATA_PREFIX=/usr/share/tesseract-ocr/tessdata/


  It will install all the needed dependencies, compile and install Tesseract V4.0.0 with french and english locale. If you need more locales, just do :

    $ sudo apt install tesseract-ocr-langcode

  Here is a list of all available languages code : https://www.macports.org/ports.php?by=name&substr=tesseract-

## Create service

The ./Makefile command create the service, but you may want to change the User and Group so just open the ./MakfFile and change lines **22** and **23**

## Set up the incron

We want to automatise the capture of document. For that, we'll use incrontab.
First, add your user into the following file :

> /etc/incron.allow

Then use <code>incrontab -e</code> and put the following line :

    /path/to/capture/ IN_CLOSE,IN_MOVED_TO,IN_NO_LOOP /opt/maarch/OpenCapture/scripts/IN.sh $@/$#



## WebServices for Maarch 18.10

In order to reconciliate a contact it's needed to contact the Maarch database. For that 2 little PHP web services were developed.
First, go into your Maarch installation (e.g : **/var/www/maarch_courrier**).
Then add the new route to the end of **rest/index.php**, juste before the line <code>$app->run();</code>

> $app->get('/getContactByMail', \Contact\controllers\ContactController::class . ':getByMail');
> $app->get('/getContactByUrl', \Contact\controllers\ContactController::class . ':getByUrl');

Then, go to **src/app/contact/controllers/ContactController.php** and at the end of the file, juste before the last <code>}</code>, put :

    public function getByMail(Request $request, Response $response)
    {
      $data = $request->getParams();
      $contact = ContactModel::getByMail([
      'mail' => $data['mail'],
      ]);

     return $response->withJson($contact);
    }

    public function getByUrl(Request $request, Response $response)
    {
      $data = $request->getParams();
      $contact = ContactModel::getByUrl([
      'url' => $data['url'],
      ]);

     return $response->withJson($contact);
    }



## Various
If you want to generate PDF/A instead of PDF, you have to do the following :

> cp install/sRGB_IEC61966-2-1_black_scaled.icc /usr/share/ghostscript/X.XX/
> nano +8 /usr/share/ghostscript/X.XX/lib/PDFA_def.ps
> Replace : %/ICCProfile (srgb.icc) % Customise
> By : /ICCProfile (/usr/share/ghostscript/X.XX/sRGB_IEC61966-2-1_black_scaled.icc)   % Customize


# Informations
## QRCode separation

Maarch permit the creation of separator, with QRCODE containing the ID of an entity. "DGS" for example. If enabled is config.ini, the separation allow us to split a PDF file containing QR Code and create PDF with a filename prefixed with the entity ID. e.g : "DGS_XXXX.pdf"

## Configuration

The file <code>src/config/config.ini</code> is splitted in different categories

 - Global
	 - Set the default path of the project (default : **/opt/maarch/OpenCapture/**)
	 - tmpPath, no need to modify
	 - Resolution and compressionQuality when PDF are converted to JPG
	 - Path to the logFile, no need to modify
 - Locale
	 - Choose the locale for text recognition (about date format and regex), by default it's **fr_FR** or **en_EN** but you can add more (see further in the README)
	 - Choose the locale of OCR (see the langcodes of Tesseract)
	 - Path for the locale JSON file for date (related to the first option of Locale), no need to modify
 - OCForMaarch
	 - Link to **/rest** API of Maarch with User and Password
	 - Default metadata to insert documents (type_id, status, priority, format, category_id and destination)
 - Regex
	 - Add extensions to detect URL during text detection
 - Separator_QR
	 - Enable or disable
	 - Choose to export PDF or PDF/A
	 - Path to export PDF or PDF/A, no need to modify
	 - Tmp path, no need to modify
	 - Modify the default divider if needed (eg. DGS_XXX.pdf or DGS-XXX.pdf)

# Utilisations
We use worker and jobs to enqueue process.
Here is some examples of possible usages :

    $ python3 /opt/maarch/OpenCapture/worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -f file.pdf
    $ python3 /opt/maarch/OpenCapture/worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -p /path/to/folder/
    $ python3 /opt/maarch/OpenCapture/worker.py -c /opt/maarch/OpenCapture/src/config/config.ini -p /path/to/folder/ --read-destination-from-filename

--read-destination-from-filename is related to separation with QR CODE. It's reading the filename, based on the **divider** option in config.ini, to find the entity ID
-f stands for unique file
-p stands for path containing PDF/JPG files and process them as batch


## Apache modifications

In case some big files would be sent, you have to increase the **post_max_size** parameter on the following file
> /etc/php/7.X/apache2/php.ini

By default it is recommended to replace **8M** by **20M**

# LICENSE

OpenCapture for Maarch is released under the GPL v3.

