#!/bin/bash

if [ "$EUID" -ne 0 ]; then
    echo "install.sh needed to be launch by user with root privileges"
    exit 1
fi

if [ "$(uname -m)" != 'x86_64' ]; then
    echo "This script is only compatible with x86_64 architecture"
    exit 1
fi

bold=$(tput bold)
normal=$(tput sgr0)
defaultPath=/opt/edissyum/opencaptureformem/
imageMagickPolicyFile=/etc/ImageMagick-6/policy.xml
user=$(who am i | awk '{print $1}')
group=www-data

####################
# Handle parameters
parameters="user supervisor_process path supervisor_systemd secure_rabbit rabbit_user rabbit_password rabbit_host rabbit_port rabbit_vhost"
opts=$(getopt --longoptions "$(printf "%s:," "$parameters")" --name "$(basename "$0")" --options "" -- "$@")

while [ $# -gt 0 ]; do
    case "$1" in
        --user)
            user=$2
            group=$2
            shift 2;;
        --supervisor_process)
            nbProcess=$2
            shift 2;;
        --path)
            defaultPath=$2
            shift 2;;
        --supervisor_systemd)
            supervisorOrSystemd=$2
            shift 2;;
        --secure_rabbit)
            finalRabbitMQSecure=$2
            shift 2;;
        --rabbit_user)
            rabbitMqUser=$2
            shift 2;;
        --rabbit_password)
            rabbitMqPassword=$2
            shift 2;;
        --rabbit_host)
            rabbitMqHost=$2
            shift 2;;
        --rabbit_port)
            rabbitMqPort=$2
            shift 2;;
        --rabbit_vhost)
            rabbitMqVhost=$2
            shift 2;;
    *) break;;
    esac
done

if [ -z "$user" ]; then
    printf "The user variable is empty. Please fill it with your desired user : "
    read -r user
    if [ -z "$user" ]; then
        echo 'User remain empty, exiting...'
        exit
    fi
fi

####################
# User choice
if [ -z "$supervisorOrSystemd" ]; then
    echo "Do you want to use supervisor (1) or systemd (2) ? (default : 2) "
    echo "If you plan to handle a lot of files and need a reduced time of process, use supervisor"
    echo "WARNING : A lot of Tesseract processes will run in parallel and it can be very resource intensive"
    printf "Enter your choice [1/%s] : " "${bold}2${normal}"
    read -r choice

    if [[ "$choice" == "" || ("$choice" != 1 && "$choice" != 2) ]]; then
        finalChoice=2
    else
        finalChoice="$choice"
    fi

    if [ "$finalChoice" == 1 ]; then
        echo 'You choose supervisor, how many processes you want to be run simultaneously ? (default : 5)'
        printf "Enter your choice [%s] : " "${bold}5${normal}"
        read -r choice
        if [ "$choice" == "" ]; then
            nbProcess=5
        elif ! [[ "$choice" =~ ^[0-9]+$ ]]; then
            echo 'The input is not an integer, select default value (5)'
            nbProcess=5
        else
            nbProcess="$choice"
        fi
    fi
fi

if [ -z $finalRabbitMQSecure ]; then
    echo "Do you want to secure RabbitMQ ? (default : no) "
    printf "Enter your choice [yes/%s] : " "${bold}no${normal}"
    read -r rabbitMqSecure

    if [[ "$rabbitMqSecure" == "" ||  "$rabbitMqSecure" == "no" || ("$rabbitMqSecure" != 'yes' && "$rabbitMqSecure" != 'no') ]]; then
        finalRabbitMQSecure='no'
    else
        finalRabbitMQSecure="$rabbitMqSecure"

        printf "Choose a RabbitMQ user : "
        read -r rabbitMqUser
        printf "Set a password for %s : " "${bold}$rabbitMqUser${normal}"
        read -r rabbitMqPassword
        printf "Set a host (empty for default one) : "
        read -r rabbitMqHost
        printf "Set a port (empty for default one) : "
        read -r rabbitMqPort
        printf "Choose a RabbitMQ vhost (Leave empty or type / to keep default one) : "
        read -r rabbitMqVhost
    fi
fi

####################
# Install package
apt update
apt install -y tesseract-ocr
apt install -y tesseract-ocr-fra
apt install -y tesseract-ocr-eng

xargs -a apt-requirements.txt apt install -y

python3 -m venv "/opt/edissyum/python-venv/opencaptureformem"
echo "source /opt/edissyum/python-venv/opencaptureformem/bin/activate" >> "/home/$user/.bashrc"
"/opt/edissyum/python-venv/opencaptureformem/bin/python3" -m pip install --upgrade pip
"/opt/edissyum/python-venv/opencaptureformem/bin/python3" -m pip install pillow
"/opt/edissyum/python-venv/opencaptureformem/bin/python3" -m pip install -r pip-requirements.txt

chown -R "$user":"$group" "/opt/edissyum/python-venv/opencaptureformem"
chmod -R 775 "/opt/edissyum/python-venv/opencaptureformem"

cd $defaultPath || exit 2
find . -name ".gitkeep" -delete

git config core.fileMode False

####################
# Copy default service script
cp scripts/service.sh.default scripts/service.sh
cp scripts/launch_IN.sh.default scripts/launch_IN.sh
cp scripts/launch_reconciliation.sh.default scripts/launch_reconciliation.sh
cp scripts/launch_MAIL.sh.default scripts/launch_MAIL.sh

sed -i "s#§§PYTHON_VENV§§#source /opt/edissyum/python-venv/opencaptureformem/bin/activate#g" scripts/service.sh
sed -i "s#§§PYTHON_VENV§§#source /opt/edissyum/python-venv/opencaptureformem/bin/activate#g" scripts/launch_IN.sh
sed -i "s#§§PYTHON_VENV§§#source /opt/edissyum/python-venv/opencaptureformem/bin/activate#g" scripts/launch_reconciliation.sh
sed -i "s#§§PYTHON_VENV§§#source /opt/edissyum/python-venv/opencaptureformem/bin/activate#g" scripts/launch_MAIL.sh

####################
# Makes scripts executable
chmod u+x scripts/*.sh
chmod u+x scripts/MailCollect/*.sh

####################
# Modify default config
cp $defaultPath/src/config/config.ini.default $defaultPath/src/config/config.ini
cp $defaultPath/src/config/mail.ini.default $defaultPath/src/config/mail.ini

####################
# Fix ImageMagick Policies
if test -f "$imageMagickPolicyFile"; then
    sudo sed -i 's#<policy domain="coder" rights="none" pattern="PDF" />#<policy domain="coder" rights="read|write" pattern="PDF" />#g' $imageMagickPolicyFile
else
    echo "We could not fix the ImageMagick policy files because it doesn't exists. Please f/ix it manually using the informations in the README"
fi

####################
# Secure RabbitMQ service
# First remove guest user permissions
# Create custom vhost is needed
# Then add a new user, using choosen password
# Give the new user the needed permissions
# Finally update the json file

if [[ "$finalRabbitMQSecure" != "no" ]]; then
    cp "$defaultPath"/src/config/rabbitMQ.json.default "$defaultPath"/src/config/rabbitMQ.json
    rabbitMqFile=$defaultPath/src/config/rabbitMQ.json
    vhost="/"

    if [[ "$rabbitMqVhost" != "/" && "$rabbitMqVhost" != "" ]]; then
        rabbitmqctl add_vhost "$rabbitMqVhost"
        vhost=$rabbitMqVhost
    fi

    rabbitmqctl set_permissions --vhost "/" "guest" "^$" "^$" "^$"
    rabbitmqctl add_user "$rabbitMqUser" "$rabbitMqPassword"
    rabbitmqctl set_permissions --vhost "$vhost" "$rabbitMqUser" ".*" ".*" ".*"

    jq '.username = "'$rabbitMqUser'"' "$rabbitMqFile" > tmp.$$.json && mv tmp.$$.json "$rabbitMqFile"
    jq '.password = "'$rabbitMqPassword'"' "$rabbitMqFile" > tmp.$$.json && mv tmp.$$.json "$rabbitMqFile"
    jq '.vhost = "'$vhost'"' "$rabbitMqFile" > tmp.$$.json && mv tmp.$$.json "$rabbitMqFile"

    if [[ "$rabbitMqHost" != "" ]]; then
        jq '.host = "'$rabbitMqHost'"' "$rabbitMqFile" > tmp.$$.json && mv tmp.$$.json "$rabbitMqFile"
    fi

    if [[ "$rabbitMqPort" != "" ]]; then
        jq '.port = "'$rabbitMqPort'"' "$rabbitMqFile" > tmp.$$.json && mv tmp.$$.json "$rabbitMqFile"
    fi
fi

####################
# Create input folder for fs-watcher
mkdir -p /var/share/{entrant,sortant}/
chmod -R 775 /var/share/
chown -R "$user":"$group" /var/share/

####################
# Setting up fs-watcher service
mkdir -p /var/log/watcher/
touch /var/log/watcher/daemon.log
chmod -R 775 /var/log/watcher/

sed -i "s#§§OC_PATH§§#$defaultPath#g" $defaultPath/src/config/watcher.ini.default
cp $defaultPath/src/config/watcher.ini.default /etc/watcher.ini

touch /etc/systemd/system/fs-watcher.service
su -c "cat > /etc/systemd/system/fs-watcher.service << EOF
[Unit]
Description=filesystem watcher
After=basic.target

[Service]
ExecStart=/opt/edissyum/python-venv/opencaptureformem/bin/watcher -c /etc/watcher.ini start
ExecStop=/opt/edissyum/python-venv/opencaptureformem/bin/watcher -c /etc/watcher.ini stop
Type=simple
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

systemctl daemon-reload
systemctl enable --now fs-watcher

####################
# Create the service systemd or supervisor
if [ "$finalChoice" == 2 ] || [ $supervisorOrSystemd == 'systemd' ]; then
    touch /etc/systemd/system/oc-worker.service
    su -c "cat > /etc/systemd/system/oc-worker.service << EOF
[Unit]
Description=Daemon for Open-Capture for MEM Courrier

[Service]
Type=simple

User=$user
Group=$group
UMask=0022

ExecStart=$defaultPath/scripts/service.sh
KillSignal=SIGQUIT

Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
"
    systemctl daemon-reload
    systemctl start oc-worker.service
    systemctl enable oc-worker.service
else
    mkdir "$defaultPath"/data/log/Supervisor/
    apt install -y supervisor
    touch /etc/supervisor/conf.d/opencapture.conf
    su -c "cat > /etc/supervisor/conf.d/opencapture.conf << EOF
[program:OCWorker]
command=$defaultPath/scripts/service.sh
process_name=%(program_name)s_%(process_num)02d
numprocs=$nbProcess
socket_owner=$user
stopsignal=QUIT
stopasgroup=true
killasgroup=true
stopwaitsecs=10
stderr_logfile=$defaultPath/data/log/Supervisor/OC_%(process_num)02d_error.log
EOF
  "
    chmod 755 /etc/supervisor/conf.d/opencapture.conf
    systemctl restart supervisor
    systemctl enable supervisor
fi

####################
# Create a custom temp directory to cron the delete of the ImageMagick temp content
mkdir -p /tmp/opencapture/
chown -R "$user":"$group" /tmp/opencapture

####################
# Generate a secret key for the API
secret=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
config_file="$defaultPath/src/config/config.ini"

if ! grep -q '^\[API\]' "$config_file"; then
    echo "Error: The [API] section is missing in your config.ini. Please add it."
    exit 1
fi

if ! grep -q '^secret_key' "$config_file"; then
    echo "Error: The secret_key key is missing in the [API] section. Please add it."
    exit 1
fi

sed -i "/^\[API\]/,/^\[/{s/^secret_key.*/secret_key = $secret/}" "$config_file"

chmod 755 "$config_file"

cp "$defaultPath"/src/config/custom.json.default "$defaultPath"/src/config/custom.json

####################
# Fill Addin Outlook manifest file with secret key
cp "$defaultPath/src/app/addin_outlook/manifest.xml.default" "$defaultPath/src/app/addin_outlook/manifest.xml"
sed -i "s#§§SECRET_KEY§§#$secret#g" "$defaultPath/src/app/addin_outlook/manifest.xml"

####################
# Create the Apache service for the API
touch /etc/apache2/sites-available/opencaptureformem.conf
touch /etc/apache2/sites-available/opencaptureformem-ssl.conf
sitePackageLocation=$(/opt/edissyum/python-venv/opencaptureformem/bin/python3 -c 'import site; print(site.getsitepackages()[0])')

cat << EOF > /etc/apache2/sites-available/opencaptureformem.conf
<VirtualHost *:80>
    ServerName localhost

    DocumentRoot $defaultPath
    WSGIDaemonProcess opencaptureformem home=$defaultPath python-path=$defaultPath python-home=/opt/edissyum/python-venv/opencaptureformem python-path=$sitePackageLocation
    WSGIScriptAlias /opencaptureformem $defaultPath/wsgi.py

    <Directory "$defaultPath">
        AllowOverride All
        Options -Indexes +FollowSymLinks
        WSGIProcessGroup opencaptureformem
        WSGIApplicationGroup %{GLOBAL}
        WSGIPassAuthorization On
        Require all granted
        <Files ~ "(.ini)">
            Require all denied
        </Files>
    </Directory>
</VirtualHost>
EOF

cat << EOF > /etc/apache2/sites-available/opencaptureformem-ssl.conf
<VirtualHost *:443>
    ServerName localhost

    DocumentRoot $defaultPath
    WSGIDaemonProcess opencaptureformem home=$defaultPath python-path=$defaultPath python-home=/opt/edissyum/python-venv/opencaptureformem python-path=$sitePackageLocation
    WSGIScriptAlias /opencaptureformem $defaultPath/wsgi.py

    SSLEngine on
    SSLCertificateFile      /path/to/signed_cert_and_intermediate_certs_and_dhparams
    SSLCertificateKeyFile   /path/to/private_key

    <Directory "$defaultPath">
        AllowOverride All
        Options +Indexes
        WSGIProcessGroup opencaptureformem
        WSGIApplicationGroup %{GLOBAL}
        WSGIPassAuthorization On
        Require all granted
        <Files ~ "(.ini)">
            Require all denied
        </Files>
    </Directory>
</VirtualHost>
EOF

a2dissite 000-default.conf
a2ensite opencaptureformem.conf
a2enmod ssl
a2enmod rewrite
systemctl restart apache2

usermod -aG www-data "$user"

####################
# Fix rights
chmod -R 775 $defaultPath
chown -R "$user":"$group" $defaultPath

echo ""
echo "#######################################################################################################################"

