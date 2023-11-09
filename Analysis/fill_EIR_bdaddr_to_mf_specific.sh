#!/bin/bash
echo "$1"
echo "tsharking"
tshark -r "$1" -Y 'bthci_evt.code == 0x2f && btcommon.eir_ad.entry.type == 0xff ' -T fields -e bthci_evt.bd_addr -e btcommon.eir_ad.entry.company_id -e btcommon.eir_ad.entry.data -E separator=, -E quote=d > /tmp/EIR_bdaddr_to_mf_specific.csv
# dedupe for faster mysql import
cat /tmp/EIR_bdaddr_to_mf_specific.csv | sort | uniq > /tmp/EIR_bdaddr_to_mf_specific_uniq.csv
# Note: This can and will have entries like device ID = 0x000f (broadcom), which then have some "3DS" info for the manufacturer-specific data. But the problem is that Wireshark knows how to 
# dissect that info, and consequently nothing will be printed out for btcommon.eir_ad.entry.data. So then it has the wrong number of columns
# So we're going to process the file to tack a ,"XXXXXX" on to the end, since we don't have real values for now
sed -i '' 's/"0x000f",$/&"XXXXXX"/' /tmp/EIR_bdaddr_to_mf_specific_uniq.csv
echo "mysql import"
mysql -u user -pa --database='bt' --execute="LOAD DATA INFILE '/tmp/EIR_bdaddr_to_mf_specific_uniq.csv' REPLACE INTO TABLE EIR_bdaddr_to_mf_specific FIELDS TERMINATED BY ',' ENCLOSED BY '\"' LINES TERMINATED BY '\n' (device_bdaddr, @device_BT_CID, mf_specific_data) SET device_BT_CID = CAST(CONV(REPLACE(@device_BT_CID, '0x', ''), 16, 10) AS UNSIGNED);"
