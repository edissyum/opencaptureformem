#!/bin/bash

if [ "$EUID" -ne 0 ]
  then echo "Makefile needed to be launch by user with root privileges"
  exit 1
fi

bold=$(tput bold)
normal=$(tput sgr0)
OS=$(lsb_release -si)
VER=$(lsb_release -r)
defaultPath=/opt/mem/opencapture/
imageMagickPolicyFile=/etc/ImageMagick-6/policy.xml
user=$(who am i | awk '{print $1}')
group=www-data

if [ -z "$user" ]
then
 printf "The user variable is empty. Please fill it with your desired user : "
 read -r user
 if [ -z "$user" ]
 then
   echo 'User remain empty, exiting...'
   exit
 fi
fi

####################
# User choice
echo "Do you want to use supervisor (1) or sytemd (2) ? (default : 2) "
echo "If you plan to handle a lot of files and need a reduced time of process, use supervisor"
echo "WARNING : A lot of Tesseract processes will run in parallel and it can be very resource intensive"
printf "Enter your choice [1/%s] : " "${bold}2${normal}"
read -r choice

if [[ "$choice" == "" || ("$choice" != 1 && "$choice" != 2) ]]; then
  finalChoice=2
else
  finalChoice="$choice"
fi

if [ "$finalChoice" == 1 ];then
  echo 'You choose supervisor, how many processes you want to be run simultaneously ? (default : 10)'
  printf "Enter your choice [%s] : " "${bold}10${normal}"
  read -r choice
  if [ "$choice" == "" ]; then
    nbProcess=10
  elif ! [[ "$choice" =~ ^[0-9]+$ ]]; then
    echo 'The input is not an integer, select default value (10)'
    nbProcess=10
  else
    nbProcess="$choice"
  fi
fi

if [ "$finalChoice" != 1 ];then
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

echo 'Would you use Python virtual environment ? (default : yes)'
printf "Enter your choice [%s] : " "${bold}yes${normal}/no"
read -r choice
if [ "$choice" != "no" ]; then
    pythonVenv='true'
else
    pythonVenv='false'
fi

####################
# Install package
if [[ "$OS" = 'Debian' && "$VER" == *'9'* ]]; then
  su -c 'cat > /etc/apt/sources.list.d/stretch-backports.list << EOF
deb http://http.debian.net/debian stretch-backports main contrib non-free
EOF'
  apt update
  apt install -y -t stretch-backports tesseract-ocr
  apt install -y -t stretch-backports tesseract-ocr-fra
  apt install -y -t stretch-backports tesseract-ocr-eng
elif [[ "$OS" = 'Ubuntu' || "$OS" == 'Debian' && ($VER == *'10'* || $VER == *'11'*) ]]; then
  apt update
  apt install -y tesseract-ocr
  apt install -y tesseract-ocr-fra
  apt install -y tesseract-ocr-eng
fi

xargs -a apt-requirements.txt apt install -y

if [ $pythonVenv = 'true' ]; then
    python3 -m venv "/home/$user/python-venv/opencaptureformem"
    echo "source /home/$user/python-venv/opencaptureformem/bin/activate" >> "/home/$user/.bashrc"
    "/home/$user/python-venv/opencaptureformem/bin/python3" -m pip install --upgrade pip
    "/home/$user/python-venv/opencaptureformem/bin/python3" -m pip install pillow
    "/home/$user/python-venv/opencaptureformem/bin/python3" -m pip install -r pip-requirements.txt
else
    python3 -m pip install --upgrade pip
    python3 -m pip install pillow
    python3 -m pip install -r pip-requirements.txt
fi

cd $defaultPath || exit 2
find . -name ".gitkeep" -delete

git config core.fileMode False

####################
# Copy default service script
cp scripts/service.sh.default scripts/service.sh
cp scripts/launch_IN.sh.default scripts/launch_IN.sh
cp scripts/launch_OUT.sh.default scripts/launch_OUT.sh
cp scripts/launch_reconciliation.sh.default scripts/launch_reconciliation.sh
cp scripts/launch_MAIL.sh.default scripts/launch_MAIL.sh
if [ $pythonVenv = 'true' ]; then
    sed -i "s#§§PYTHON_VENV§§#source /home/$user/python-venv/opencaptureformem/bin/activate#g" scripts/service.sh
    sed -i "s#§§PYTHON_VENV§§#source /home/$user/python-venv/opencaptureformem/bin/activate#g" scripts/launch_IN.sh
    sed -i "s#§§PYTHON_VENV§§#source /home/$user/python-venv/opencaptureformem/bin/activate#g" scripts/launch_OUT.sh
    sed -i "s#§§PYTHON_VENV§§#source /home/$user/python-venv/opencaptureformem/bin/activate#g" scripts/launch_reconciliation.sh
    sed -i "s#§§PYTHON_VENV§§#source /home/$user/python-venv/opencaptureformem/bin/activate#g" scripts/launch_MAIL.sh
else
    sed -i "s#§§PYTHON_VENV§§##g" scripts/service.sh
    sed -i "s#§§PYTHON_VENV§§##g" scripts/launch_IN.sh
    sed -i "s#§§PYTHON_VENV§§##g" scripts/launch_OUT.sh
    sed -i "s#§§PYTHON_VENV§§##g" scripts/launch_reconciliation.sh
    sed -i "s#§§PYTHON_VENV§§##g" scripts/launch_MAIL.sh
fi

####################
# Makes scripts executable
chmod u+x scripts/*.sh
chmod u+x scripts/MailCollect/*.sh

####################
# Modify default config
cp $defaultPath/src/config/config.ini.default $defaultPath/src/config/config.ini
cp $defaultPath/src/config/mail.ini.default $defaultPath/src/config/mail.ini

####################
# Fix rights
chmod -R 775 $defaultPath
chown -R "$user":"$group" $defaultPath

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
    cp $defaultPath/src/config/rabbitMQ.json.default $defaultPath/src/config/rabbitMQ.json
    rabbitMqFile=$defaultPath/src/config/rabbitMQ.json
    vhost="/"

    if [[ "rabbitMqVhost" != "/" && "rabbitMqVhost" != "" ]]; then
        rabbitmqctl add_vhost "$rabbitMqVhost"
        vhost=$rabbitMqVhost
    fi

    rabbitmqctl set_permissions --vhost "/" "guest" "^$" "^$" "^$"
    rabbitmqctl add_user "$rabbitMqUser" "$rabbitMqPassword"
    rabbitmqctl set_permissions --vhost "$vhost" "$rabbitMqUser" ".*" ".*" ".*"

    jq '.username = "$rabbitMqUser"' $rabbitMqFile > tmp.$$.json && mv tmp.$$.json $rabbitMqFile
    jq '.password = "$rabbitMqPassword"' $rabbitMqFile > tmp.$$.json && mv tmp.$$.json $rabbitMqFile
    jq '.vhost = "$vhost"' $rabbitMqFile > tmp.$$.json && mv tmp.$$.json $rabbitMqFile

    if [[ "rabbitMqHost" != "" ]]; then
        jq '.host = "$rabbitMqHost"' $rabbitMqFile > tmp.$$.json && mv tmp.$$.json $rabbitMqFile
    fi

    if [[ "rabbitMqPort" != "" ]]; then
        jq '.port = "$rabbitMqPort"' $rabbitMqFile > tmp.$$.json && mv tmp.$$.json $rabbitMqFile
    fi
fi

####################
# Create the service systemd or supervisor
if [ "$finalChoice" == 2 ]; then
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
mkdir /tmp/opencapture/
chown -R "$user":"$group" /tmp/opencapture