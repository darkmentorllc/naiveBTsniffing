#**Note: You probably *don't* want to use this repository, but instead want to use the more advanced successor (which is built on the same principles): [Blue2thprinting](https://github.com/darkmentorllc/Blue2thprinting).**

# Disclaimer!

The code in this repository is ***researchware***. That means **its purpose is primarily to prove that the results from past research are real, and to allow replication of results*** (in this case, the ["It Was Harder to Sniff Bluetooth Through My Mask During the Pandemic..."](https://darkmentor.com/publication/2023-08-hitb/) talk.) This code is not meant to be used as a production tool, nor is it optimized for performance, ease of use, or anything else. It is only meant to be used by researchers looking to replicate, or expand, on this work.

Note: the below hardware purchase links are Amazon affiliate links that support the [OpenSecurityTraining2](https://ost2.fyi) nonprofit.

# Assumed Hardware
(If you do not have any of the below, you will need to purchase.)

* Keyboard  
* Mouse  
* Monitor with HDMI input (or DVI input and an HDMI adapter. Note: Raspberry Pis have not worked with all monitors / adapter configurations for me.)  
* USB-micro male to USB-A male cable (to be used for power)  


# Recommended Hardware

The below recommends 2 of some things, just because it ends up being cheaper per-unit. Or because it's useful to have an extra if one dies. 

For devices where only 1 is recommended, it is assumed that you will only have one Raspberry Pi powered up at a time. If you intend to have both powered, you will need to increase to 2x.

* 2x - [Raspberry Pi Zero W](https://www.raspberrypi.com/products/raspberry-pi-zero/) - ~$10/unit
* * You can use a Raspberry Pi 4b if you already have one, but in my experiments they capture less data than the Pi Zero W.

* 2x - [64 GB micro SD card](https://amzn.to/3PahwSb) - ~$6/unit
* * If you don't have a way to mount microSD cards, will also require 1x [SD card to USB adapter](https://amzn.to/3KURtM1) - ~$7/unit

* 2x - [USB-micro male to USB-A female adapter](https://amzn.to/45Ip6bN) - ~$4/unit
* * The USB hub is plugged into this.

* 2x - [USB-A battery pack (38800mAh)](https://amzn.to/3YPa5mD) - ~$32/unit
* * You can use a smaller & cheaper battery if you don't need to leave the device unattended for days.

* 1x - [Non-separate-power USB-A hub](https://amzn.to/3qHCkXw) - ~$8/unit
* * *Note:* in my experience connecting an unpowered USB-A hub to the Pi Zero seems to cause too much of a power draw, and causes it to reboot. For this reason, while at home you may want to instead use a [powered USB hub](https://amzn.to/3YJU3u5) (even though it's more expensive.) However, the unpowered USB-A hub is necessary if you want to bring keyboard and mouse and GPS with you while driving around (e.g. if you think you may want to check on the status.)

* 1x - [HDMI-mini male to HDMI femle adapter](https://amzn.to/44javCF) - ~$3.50/unit

* 1x - [USB-A Ethernet Adapter](https://amzn.to/3qOezgr) - ~$10/unit
* * The Pi does not have a real time clock battery. Therefore if you power it off and power it on a week later, it will still think it's the previous time. I've been too lazy to wire up a battery, and instead I just use NTP to sync the time over the network whenever I power it on before a sniffing run. Also, I use Ethernet, because I disable the WiFi so that it doesn't waste power or compete with the Bluetooth for the antenna via "coexistence".

* 1x - [USB-A GPS receiver](https://amzn.to/44srqCJ) - ~$19/unit
* * Not necessary if you're only going to place sniffers at a single known location. Necessary if you're going to wander around and want to know where something was observed.

The following are only required if you'll be placing the devices into an outdoor environment for days at a time:

* 2x - [Lockable water-proof outdoor box](https://amzn.to/3OHsSeO) - ~$9/unit

* 2x - [Keyed Padlock](https://amzn.to/3P95PuM) - ~$10/unit

* 2x - [Flexible bike lock](https://amzn.to/3YOu7xf) - ~$9/unit
* * These [aren't particularly secure](https://www.youtube.com/shorts/dA9OsRal_L8), and indeed I forgot my combo at one point and had to pick my own. But they're just there to stop hobos and randos from walking off with your stuff ;).

Nice to have:

* 1x - [5" Mini screen](https://amzn.to/3QtlJj1) - ~$39/unit
* * If you are using the device for mobile sniffing, it's desirable to know if it's actually continuing to capture data, or whether it's crashed. You won't be able to tell that without a screen + the unpowered USB hub + keyboard + mouse.

* 1x - [Short & flexible HDMI cable](https://www.amazon.com/gp/product/B0B5TDFVVW/ref=ppx_yo_dt_b_search_asin_title?ie=UTF8&th=1) for above mini-screen - ~$14/unit

* You will need an additional USB micro male to USB A male cable (to be used for power for the mini-screen).

**If you bought everything correctly, your setup should look like this :P**

![MySetup](./img/MySetup_Small.png)

# New! Easy-mode quick-start setup!

The below instructions are the full setup guide. However, it's the kind of thing where any small mistake in setup will cost you hours of debugging. So to make it easier for people to get started, I have done the initial setup on a system (minus the GPS setup and minus the small screen setup), and then just used `dd` to image the resulting 64GB microSD card with a known-good working instance of the software running on it. If you want to just get started quickly, then you can do the following.

1. Download [this file](https://drive.google.com/file/d/1bmfZFPHIO7cvjxV1yBJVJAgNt_wJx566/view?usp=sharing).
2. Use the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to write the `rPi0_Buster_KnownGood_2024-04-22.img.gz` file to your microSD card.
3. After you boot your Raspberry Pi Zero do the following from the command line:
4. cd ~/Scripts
5. sudo killall.sh
6. sudo raspi-config
	1. Select "1 System Options"
	2. Select "S4 Hostname"
	3. Set the hostname to "pi0-N" where N is that this is your Nth Raspberry pi. E.g. I have pi0-1, pi0-2, pi0-3 for my 3 Pis. This hostname will be used on log files, so if you've got multiple sniffers in multiple locations you'll want to know which logs came from which one. Then select "OK".
	4. Select "6 Advanced Options"
	2. Select "A1 Expand Filesystem"
	3. After it says "Root partition has been resized..." select "OK"
	4. Select "Finish"
	5. After it asks if you'd like to reboot, select yes.

**Note**: SSH is on by default and the password for the `pi` user is `a` by default. Change it if you feel like it.

If you instead want to set everything up from scratch, the instructions are [here](FULLSETUP.md).

# Confirm imaging succeeded

If imaging succeeded, the Raspberry Pi will just be automatically collecting BT data every time it boots up. You should be able to do `tail -f ~/CAL.log` and see the output from `~/central_all_launcher2.py`, which is orchestrating the tools like gatttool and sdptool.

You can also do:

`cd ~/Scripts`  
`./check.sh`  
If you are too quick, you will see things like `start_btmon.sh`, `start_bluetoothctl.sh`, or `start_gpspipe.sh`.  
But after their sleep timers have expired, they will transition to things like:

```
root       769  0.1  0.5   5216  2212 ?        S    15:05   0:00 /usr/bin/gpspipe -p -w -T +%F %H:%M:%S -o /home/pi/Scripts/logs/gpspipe/2024-04-22-15-04-36_pi0-1.txt
pi        1160  0.0  0.4   7328  2008 pts/1    S+   15:05   0:00 grep gpspipe
root       825  0.5  0.4   2780  2024 ?        S    15:05   0:00 /usr/bin/btmon -T -w /home/pi/Scripts/logs/btmon/2024-04-22-15-04-36_pi0-1.bin
pi        1172  0.0  0.4   7328  2024 pts/1    S+   15:05   0:00 grep btmon
root       895  2.1  1.0  18220  4472 ?        Sl   15:05   0:00 tclsh8.6 /usr/bin/unbuffer /home/pi/Downloads/bluez-5.66/client/bluetoothctl scan on
root       897  1.4  0.7   6988  3376 pts/0    Ss+  15:05   0:00 /home/pi/Downloads/bluez-5.66/client/bluetoothctl scan on
pi        1184  0.0  0.4   7328  1960 pts/1    S+   15:05   0:00 grep bluetoothctl
root       339  0.0  0.5   7648  2516 ?        S    15:04   0:00 /bin/bash /home/pi/Scripts/start_central_app_launcher.sh
root      1127  3.0  0.7   9932  3324 ?        S    15:05   0:00 sudo -E python3 -u /home/pi/central_app_launcher2.py
root      1136 52.0  2.4  19036 11008 ?        R    15:05   0:01 python3 -u /home/pi/central_app_launcher2.py
pi        1193  0.0  0.4   7328  2024 pts/1    S+   15:05   0:00 grep central_app
```

You can cancel collection by running: `sudo ./killall.sh` from the `~/Scripts` folder.

If you want to manually restart the collection without a reboot, you can run: `sudo ./runall.sh` from the Scripts folder.

# On-Device Analysis Scripts Usage

If you want a quick way to assess what named devices were seen in a given capture, run the below dump\_names\_specific.sh command.

### dump\_names\_specific.sh

Assume we have the following files:

```
root@pi0-2:/home/pi/Scripts# ls logs/btmon/
2023-08-24-01-04-59_pi0-2.bin  2023-08-24-01-11-38_pi0-2.bin
```

The named bluetooth devices found in multiple files can be dumped to stdout as follows:

```
./dump_names_specific.sh 2023-08-24-01-04-59_pi0-2.bin 2023-08-24-01-11-38_pi0-2.bin
Processing  /home/pi/Scripts/logs/btmon/2023-08-24-01-04-59_pi0-2.bin
btmon -T -r /home/pi/Scripts/logs/btmon/2023-08-24-01-04-59_pi0-2.bin.bin | grep -e "Name (.*):" | sort | uniq
Processing  /home/pi/Scripts/logs/btmon/2023-08-24-01-11-38_pi0-2.bin
btmon -T -r /home/pi/Scripts/logs/btmon/2023-08-24-01-11-38_pi0-2.bin.bin | grep -e "Name (.*):" | sort | uniq
All found names:
        Name (complete): This_is-not_real
        Name (complete): Neither is this😎
        Name (complete): BecauseWiGLEWouldTellYouWhereILive:P
```
from within the Scripts folder.

*Note:* The accepted name format is just the filename, not the full path. 

# Off-Device Analysis Scripts Usage

## Import data into MySQL on a separate analysis system

**Note:** Because data parsing and database lookups can be CPU/IO intensive, it is generally recommended to *not* perform data import or analysis on the capture device (the Pi Zero in this case.) Rather, it is recommended to copy all data off to a separate, faster, analysis system, and perform the subsequent steps there.

### One time setup

**Linux Software Setup**: You should already have the necessary MySQL (MariaDB) database and tshark tools installed from the above apt-get commands.

**macOS Software Setup**: You can load the data into the database and perform analysis on macOS, but you must first [install HomeBrew](https://brew.sh/), and then run `brew install mysql` and `brew install wireshark` (for the `tshark` CLI version). (If for some reason neither tshark nor wireshark are found in your PATH, look in / add from /usr/local/Cellar/wireshark/). Then also edit `/usr/local/etc/my.cnf` and add `secure_file_priv = /tmp` at the end of the file, and then start the mysql server with `/usr/local/opt/mysql/bin/mysqld_safe --datadir=/usr/local/var/mysql`.

**Create initial database & tables**:

To create the "bt" database and all the necessary tables, run the following:  

```
cd ~/naiveBTsniffing/Analysis
sudo ./create_all_db_tables.sh
```

**Import the IEEE OUIs into the database**:

```
cd ~/naiveBTsniffing/Analysis
./process_OUI_lists.sh ./oui.txt
```

The oui.txt is from [https://standards-oui.ieee.org/oui/oui.txt](https://standards-oui.ieee.org/oui/oui.txt), and should be periodically updated. Also note that the `process_OUI_lists.sh` script does not currently handle OUI assignments that are less than 24 bits ([tracking issue](https://github.com/darkmentorllc/naiveBTsniffing/issues/1)).

**Import BT companies into the database**:

```
cd ~/naiveBTsniffing/Analysis
./translator_fill_UUID16_to_company.sh
```

This should be re-run if you ever do a "git pull" in the `Blue2thprinting/public` directory, which contains the Bluetooth Assigned Numbers information, to get updated assigned vendor UUID16s.

### Importing data from btmon .bin files

`cd ~/naiveBTsniffing/Analysis`

Run `./fill_ALL_from_HCI_log.sh {your_btmon_file.bin}`.

E.g. `./fill_ALL_from_HCI_log.sh ../ExampleData/2023-10-06-08-52-20_up-apl01.bin`

You should see a variety of outputs such as "tsharking", and "mysql import". You can safely ignore any tshark warnings about the file being "cut short in the middle of a packet".

Eventually once you have many files to process in bulk, you will want to pass each file to `fill_ALL_from_HCI_log.sh` sequentially. For that you can issue a command like:

`time find /path/to/btmon_logs/2023-10* -type f -name "*.bin" | xargs -n 1 -I {} bash -c " ./fill_ALL_from_HCI_log.sh {}"`

**To confirm that some data was successfully imported, you can issue:**

```
mysql -u user -pa -D bt -e "SELECT * FROM LE_bdaddr_to_name LIMIT 10;"
```

This should show some of the same sort of device name data that you could see by the above `./dump_names_specific.sh` command.

### Importing GATT data from GATTprint.log

Both `central_all_launcher2.py` and `gatttool` log information about attempted and successful GATTprinting to the file `/home/pi/GATTprint.log` (or alt user home directory if you reconfigured it). To import this data into the database, run the following:

```
cp ~/Blue2thprinting/Analysis/parse_GATTPRINT_2db.py ~/
cd ~
cat GATTprint*.log | sort | uniq > GATTprint_dedup.log
python3 ./parse_GATTPRINT_2db.py
```

The above `cat` step is useful both to speed up the parsing of a single host's data (if it queried the same host multiple times), but also to combine data from multiple hosts, and avoid unnecessary duplicative mysql imports.

**To confirm that some data was successfully imported, you can issue:**

```
mysql -u user -pa -D bt -e "SELECT * FROM GATT_characteristics LIMIT 10;"
```

## Inspecting data with TellMeEverything.py

`cd ~/naiveBTsniffing/Analysis`

You will need Python3 installed, and you may need to change the path to the python3 interpreter at the beginning of the file. You will also need to do `pip3 install mysql-connector-python`, `pip3 install pyyaml` if you have not already.

Issue `python3 ./TellMeEverything.py --help` for the latest usage.

**If you get an error like "public/path/something can't be found"**, make sure your `~/naiveBTsniffing/Analysis/public` folder is not empty. If it is empty, that implies you didn't check out the Bluetooth assigned numbers sub-module at git repository clone time. This can be corrected by issuing `git submodule update --init --recursive`.

**Printing information for a specific BDADDR**:

`python3 ./TellMeEverything.py --bdaddr 4c:e6:c0:21:39:a6`

**Printing information for BDADDRs that have a name that matches a given regex**:

`python3 ./TellMeEverything.py --nameregex "^Flipper"`

The regex is used as a MySQL "REGEXP" statement, and thus must be valid MySQL regex syntax.

**Printing information for BDADDRs that have some data element that is associated with a company name that matches a given regex**:

`python3 ./TellMeEverything.py --companyregex "^Qualcomm"`

The regex is checked against associations with the BDADDR IEEE OUI, UUID16s, and BT/BLE CompanyID fields from link layer version information.

**Printing information for BDADDRs that have a UUID128 that matches a given regex**:

`python3 ./TellMeEverything.py --UUID128regex "02030302"`

**Printing information for BDADDRs that have Manufacturer Specific Data that matches a given regex**:

`python3 ./TellMeEverything.py --MSDregex "008fc3d5"`
