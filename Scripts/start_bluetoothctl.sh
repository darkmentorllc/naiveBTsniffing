#!/bin/bash

#bluetoothctl is a better than hcitool lescan because it shows more info about beacons it sees

LOGPATH="/home/pi/Scripts/logs/bluetoothctl"
DATE=$(/bin/date +%F-%H-%M-%S)
HN=$(hostname)
LINKAGE_FILE="/tmp/BT_link.txt"
echo "Logging to ${LOGPATH}/${DATE}_${HN}.txt"

#So this will come up after btmon
sleep 40

#Do the actual scanning, so hcidump and btmon can see traffic
#/usr/bin/bluetoothctl scan on > $LOGPATH/$DATE.txt

# Delete the link if it exists
if [ -e "$LINKAGE_FILE" ]; then
    rm "$LINKAGE_FILE"
fi
# Had to move over to my custom bluetoothctl to find out which are BTC vs. BLE devices!
RESULT=$(unbuffer /home/pi/Downloads/bluez-5.66/client/bluetoothctl scan on > ${LOGPATH}/${DATE}_${HN}.txt &)
#Re-link to the file so it can be found by other scripts
ln -s ${LOGPATH}/${DATE}_${HN}.txt $LINKAGE_FILE
