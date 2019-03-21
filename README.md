sudo apt install pdftk

Si génération de PDF/A :
    Copier le fichier install/sRGB_IEC61966-2-1_black_scaled.icc vers /usr/share/ghostscript/X.XX/
    Modifier le fichier /usr/share/ghostscript/X.XX/lib/PDFA_def.ps:
        Ligne 8 remplacer
            %/ICCProfile (srgb.icc) % Customise
            par
            /ICCProfile (/usr/share/ghostscript/X.XX/sRGB_IEC61966-2-1_black_scaled.icc)   % Customize

