#!/bin/bash

ERRORLOG="/tmp/runall.log"
echo "start_gpspipe.sh start" >> $ERRORLOG
LOGPATH="/home/pi/Scripts/logs/gpspipe"
DATE=$(/bin/date +%F-%H-%M-%S)
HN=$(hostname)

sleep 30
# -w is just a particular output format
# -p is a workaround for a bug in gpspipe 3.22 (wasn't necessary in 3.17, supposedly fixed in 3.24)
RESULT=$( /usr/bin/gpspipe -p -w -T "+%F %H:%M:%S" -o ${LOGPATH}/${DATE}_${HN}.txt &>/dev/null&)
#echo " /usr/bin/gpspipe -w -T \"+%F %H:%M:%S\" -o ${LOGPATH}/${DATE}_${HN}.txt &>/dev/null&"
echo "start_gpspipe.sh end" >> $ERRORLOG
