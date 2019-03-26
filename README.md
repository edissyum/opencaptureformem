
# OpenCapture for Maarch  
  
OpenCapture is a **free and Open Source** software under **GNU General Public License v3.0**.  

The functionnalities of OC for Maarch are : 

 - Process files by batch (in a given folder)
 - Process unique file 
 - Output searchable PDF, one or multiple pages
 - Split PDF using QRCode and rename splitted PDF file using QRCode ID
 - Process PDF or image file as input
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
 
  
  
# Installation  
  
## Necessary package  
  

    sudo apt install python3 
    sudo apt install python3-pip
    sudo apt install pdftk 

    sudo pip3 install requests 
    sudo pip3 install pyPdf2 
    sudo pip3 install pytesseract 
    sudo pip3 install pillow

  

If you want to generate PDF/A instead of PDF, you have to do the following :  
  
> cp install/sRGB_IEC61966-2-1_black_scaled.icc /usr/share/ghostscript/X.XX/  
> nano +8 /usr/share/ghostscript/X.XX/lib/PDFA_def.ps  
> Replace : %/ICCProfile (srgb.icc) % Customise  
> By : /ICCProfile (/usr/share/ghostscript/X.XX/sRGB_IEC61966-2-1_black_scaled.icc)   % Customize  
  
## Apache modifications  
  
In case some big files will be send, you have to increase the **post_max_size** parameter on the following file  
> /etc/php/7.X/apache2/php.ini  
  
By default I recommend to replace **8M** by **20M**
