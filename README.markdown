# OpenCapture for Maarch

Hi! I'm your first Markdown file in **StackEdit**. If you want to learn about StackEdit, you can read me. If you want to play with Markdown, you can edit me. Once you have finished with me, you can create new files by opening the **file explorer** on the left corner of the navigation bar.


# Installation

## Necessary package

    sudo apt install python3
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



