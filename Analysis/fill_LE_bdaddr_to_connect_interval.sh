#!/bin/bash
echo "$1"
echo "tsharking"
tshark -r "$1" -Y 'bthci_evt.code == 0x3e && btcommon.eir_ad.entry.type == 0x12' -T fields -e bthci_evt.bd_addr -e bthci_evt.le_peer_address_type -e bthci_evt.le_advts_event_type -e bthci_evt.le_ext_advts_event_type -e btcommon.eir_ad.entry.connection_interval_min -e btcommon.eir_ad.entry.connection_interval_max -E separator=, -E quote=d | awk -F, '{gsub(/,,/, ",")}1' > /tmp/LE_bdaddr_to_connect_interval.csv
# Dedup
cat /tmp/LE_bdaddr_to_connect_interval.csv | sort | uniq > /tmp/LE_bdaddr_to_connect_interval_uniq.csv
echo "mysql import"
mysql -u user -pa --database='bt' --execute="LOAD DATA INFILE '/tmp/LE_bdaddr_to_connect_interval_uniq.csv' IGNORE INTO TABLE LE_bdaddr_to_connect_interval FIELDS TERMINATED BY ',' ENCLOSED BY '\"' LINES TERMINATED BY '\n' (device_bdaddr, @bdaddr_random, @le_evt_type, @interval_min, @interval_max) SET bdaddr_random = CAST(CONV(REPLACE(@bdaddr_random, '0x', ''), 16, 10) AS UNSIGNED), le_evt_type = CAST(CONV(REPLACE(@le_evt_type, '0x', ''), 16, 10) AS UNSIGNED), interval_min = CAST(CONV(REPLACE(@interval_min, '0x', ''), 16, 10) AS UNSIGNED), interval_max = CAST(CONV(REPLACE(@interval_max, '0x', ''), 16, 10) AS UNSIGNED);"
