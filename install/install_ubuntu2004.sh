#!/usr/bin/env bash

BASEDIR=$(dirname "$0")

function checkModule {
    /usr/bin/python3 -c "import ""$1"
    if [ "$?" != "0" ]; then
        pip3 install $1
    fi
}

if systemctl list-units --all --no-legend ofsservice.service | grep -q 'ofsservice.service' ; then
   systemctl stop ofsservice
fi

command -v pip3 > /dev/null
if [ "$?" != "0" ]; then
    sudo apt-get -y install python3-pip
fi

checkModule "shutil"
checkModule "hashlib"
checkModule "gi.repository.GLib"
checkModule "dbus"
checkModule "syslog"

sudo cp -r "$BASEDIR"/../updater /
sudo chmod 744 /updater/ofsclient.py
sudo cp "$BASEDIR"/com.ofsservice.conf /usr/share/dbus-1/system.d/com.ofsservice.conf
sudo cp "$BASEDIR"/ofsservice.service /etc/systemd/system/ofsservice.service
sudo systemctl enable ofsservice
sudo systemctl start ofsservice

