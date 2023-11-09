#!/bin/bash

ERRORLOG="/tmp/runall.log"
echo "start_central_app_launcher.sh start" >> $ERRORLOG
HN=$(hostname)
echo $HN

# So this comes up after bluetoothctl scan on
sleep 45
#So that this comes up first
# -u for unbuffered stdout
RESULT=$(sudo -E python3 -u /home/pi/central_app_launcher2.py 2>&1 | tee -a /home/pi/CAL.log &)
echo "start_central_app_launcher.sh end" >> $ERRORLOG
