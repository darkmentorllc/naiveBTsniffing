#!/bin/bash
echo "$1"
echo "tsharking"
tshark -r "$1" -Y 'bthci_evt.code == 0x3e && btcommon.eir_ad.entry.type == 0x01' -T fields -e bthci_evt.bd_addr -e bthci_evt.le_peer_address_type -e bthci_evt.le_advts_event_type -e bthci_evt.le_ext_advts_event_type -e btcommon.eir_ad.entry.flags.le_limited_discoverable_mode -e btcommon.eir_ad.entry.flags.le_general_discoverable_mode -e btcommon.eir_ad.entry.flags.le_bredr_support_controller -e btcommon.eir_ad.entry.flags.le_bredr_support_host -E occurrence=f -E separator=, -E quote=d | awk -F, '{gsub(/,,/, ",")}1' > /tmp/LE_bdaddr_to_flags.csv
# Dedup
cat /tmp/LE_bdaddr_to_flags.csv | sort | uniq > /tmp/LE_bdaddr_to_flags_uniq.csv
# get rid of 0x prefix to make it so I don't need to alter all the mysql table import statements for the boolean values (which I didn't find a way to convert properly)
sed -i '' s/\"0x0/\"/g /tmp/EIR_bdaddr_to_flags_uniq.csv
echo "mysql import"
mysql -u user -pa --database='bt' --execute="LOAD DATA INFILE '/tmp/LE_bdaddr_to_flags_uniq.csv' REPLACE INTO TABLE LE_bdaddr_to_flags FIELDS TERMINATED BY ',' ENCLOSED BY '\"' LINES TERMINATED BY '\n' (device_bdaddr, @bdaddr_random, @le_evt_type, @le_limited_discoverable_mode, @le_general_discoverable_mode, @le_bredr_support_controller, @le_bredr_support_host) SET bdaddr_random = CAST(CONV(REPLACE(@bdaddr_random, '0x', ''), 16, 10) AS UNSIGNED), le_evt_type = CAST(CONV(REPLACE(@le_evt_type, '0x', ''), 16, 10) AS UNSIGNED);"
