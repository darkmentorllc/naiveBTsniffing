#!/usr/bin/python3
'''
This is a tool which coordinates the launching of various 2thprinting apps.
The goal is to try and generally minimize contention for the scanning interface
(which is the built-in hci0 used by the python BTC/BLE libraries).
'''

import datetime
import subprocess
import threading
import time
import os
from subprocess import TimeoutExpired
import traceback

# Library to get updates upon modification of bluetoothctl log file
from inotify_simple import INotify, flags

##################################################
# BEGIN TESTING TOGGLES
##################################################

BLE_thread_enabled = True
BTC_thread_enabled = True

btc_2thprint_enabled = False
ble_2thprint_enabled = False
gattprint_enabled = True
sdpprint_enabled = True

# This can be used to pre-populate any specific devices you want to test
# TODO
#manual_test = True

print_skipped = True
print_verbose = True
print_finished_bdaddrs = True

# END TESTING TOGGLES

# Place BDADDRs that you know will be traveling with you into this array,
# so that you don't waste time trying to get data about your own devices
# e.g. skip_these_addresses = ["AA:BB:CC:DD:EE:FF".lower()]
skip_these_addresses = []

device_connect_attempts = {}
max_connect_attempts = 3 # How many times to attempt connections before skipping the device thereafter
                         # Note: can be reset by a device appearing in a [DEL] statement and then a [NEW] statement
                         # in the bluetoothctl log (which would happen if the signal went low and then high again)

##################################################
# PATHS YOU MAY NEED TO FIX
##################################################

username = "pi"

default_cwd = f"/home/{username}/"

gatttool_exec_path = f"/home/{username}/Downloads/bluez-5.66/attrib/gatttool"

sdptool_exec_path = f"/home/{username}/Downloads/bluez-5.66/tools/sdptool"
sdptool_log_path = f"/home/{username}/Scripts/logs/sdptool"

braktooth = f"/home/{username}/Downloads/braktooth_esp32_bluetooth_classic_attacks/wdissector/bin/bt_exploiter"
brak_cwd = f"/home/{username}/Downloads/braktooth_esp32_bluetooth_classic_attacks/wdissector/"

python2 = "/usr/bin/python2.7"
ble2thprint = f"/home/{username}/Downloads/sweyntooth_bluetooth_low_energy_attacks/LL2thprint.py"
sweyn_cwd = f"/home/{username}/Downloads/sweyntooth_bluetooth_low_energy_attacks/"
dongle1 = "/dev/ttyACM0"

btc2thprint_log_path = f"/home/{username}/BTC_2THPRINT.log"
gattprint_log_path = f"/home/{username}/GATTprint.log"
sdpprint_log_path = f"/home/{username}/SDPprint.log"

# END STUFF YOU MAY NEED TO FIX UP

# Define a dictionary to store BDADDRs and their RSSI values
ble_bdaddrs = {}
ble_bdaddrs_lock = threading.Lock()
btc_bdaddrs = {}
btc_bdaddrs_lock = threading.Lock()
ble_deprioritized_bdaddrs = {}
ble_deprioritized_bdaddrs_lock = threading.Lock()
btc_deprioritized_bdaddrs = {}
btc_deprioritized_bdaddrs_lock = threading.Lock()

gatt_success_bdaddrs = {}
gatt_success_bdaddrs_lock = threading.Lock()
sdp_success_bdaddrs = {}
sdp_success_bdaddrs_lock = threading.Lock()
ll2thprint_success_bdaddrs = {}
ll2thprint_success_bdaddrs_lock = threading.Lock()
lmp2thprint_success_bdaddrs = {}
lmp2thprint_success_bdaddrs_lock = threading.Lock()



##################################################
# Log print helpers
##################################################

def external_log_write(log_path, fmt_str):
    with open(log_path, 'a') as file:
        try:
            current_time = datetime.datetime.now()
            print(f"\n{fmt_str}") # add a newline before, just preference, to make it easier to spot in the stdout log
            file.write(f"{fmt_str}\n") # add a newline after (required to not run lines together)
            file.flush()
        except Exception as e:
            print("Exception occurred:", str(e))
            print(f"You need to determine why the {log_path} file couldn't be written, because the logs are useless without this write")
            quit()

##################################################
# Threading for launching background processes
##################################################

def locked_delete_from_dict(dict, lock, key):
    with lock:
        if(key in dict.keys()):
            del dict[key]

def all_2thprints_done(type, bdaddr):
   if(type == "BLE"):
       if(bdaddr in gatt_success_bdaddrs.keys() and bdaddr in ll2thprint_success_bdaddrs.keys()):
           return True
       else:
           return False
   if(type == "BTC"):
       if(bdaddr in sdp_success_bdaddrs.keys() and bdaddr in lmp2thprint_success_bdaddrs.keys()):
           return True
       else:
           return False


class ApplicationThread(threading.Thread):
    def __init__(self, process, bdaddr, info_type, timeout):
        threading.Thread.__init__(self)
        self.process = process
        self.timeout = timeout
        self.is_terminated = False
        self.bdaddr = bdaddr
        self.info_type = info_type

    def run(self):
        try:
            retCode = self.process.wait(self.timeout)
            if self.process.poll() is None:
                print(f"PID: {self.process.pid}: ApplicationThread: Shouldn't be able to get here. pid still running. Killing it")
                self.process.kill()
            else:
                print(f"PID: {self.process.pid}: ApplicationThread: {self.info_type} collection for {self.bdaddr} terminated on its own with return code {retCode}")
                if(retCode == 0): #Success!
                    if(self.info_type == "GATT"):
                       external_log_write(gattprint_log_path, f"GATTPRINTING SUCCESS FOR: {self.bdaddr} {datetime.datetime.now()}")
                       with gatt_success_bdaddrs_lock:
                           gatt_success_bdaddrs[self.bdaddr] = 1
                           # Should only remove from ble_bdaddrs if all BLE-type prints are done
                           if(print_finished_bdaddrs): print(f"Successful GATTPrinting of {self.bdaddr}!")
                           if(all_2thprints_done("BLE", self.bdaddr)):
                               locked_delete_from_dict(ble_bdaddrs, ble_bdaddrs_lock, self.bdaddr)
                               if(print_finished_bdaddrs): print(f"All 2thprints collected! Deleting {self.bdaddr} from ble_bdaddrs!")
                    elif(self.info_type == "LL2thprint"):
                       with ll2thprint_success_bdaddrs_lock:
                           ll2thprint_success_bdaddrs[self.bdaddr] = 1
                           if(print_finished_bdaddrs): print(f"Successful LL2thprinting of {self.bdaddr}!")
                           if(all_2thprints_done("BLE", self.bdaddr)):
                               locked_delete_from_dict(ble_bdaddrs, ble_bdaddrs_lock, self.bdaddr)
                               if(print_verbose): print(f"All 2thprints collected! Deleting {self.bdaddr} from ble_bdaddrs!")
                    elif(self.info_type == "LMP2thprint"):
                       external_log_write(btc2thprint_log_path, f"BTC_2THPRINT: SUCCESS FOR: {self.bdaddr} {datetime.datetime.now()}")
                       with lmp2thprint_success_bdaddrs_lock:
                           lmp2thprint_success_bdaddrs[self.bdaddr] = 1
                           if(print_finished_bdaddrs): print(f"Successful LMP2thprinting of {self.bdaddr}!")
                           if(all_2thprints_done("BTC", self.bdaddr)):
                               locked_delete_from_dict(btc_bdaddrs, btc_bdaddrs_lock, self.bdaddr)
                               if(print_finished_bdaddrs): print(f"All 2thprints collected! Deleting {self.bdaddr} from btc_bdaddrs!")
                    elif(self.info_type == "SDP"):
                       external_log_write(sdpprint_log_path, f"SDPPRINTING SUCCESS FOR: {self.bdaddr} {datetime.datetime.now()}")
                       with sdp_success_bdaddrs_lock:
                           sdp_success_bdaddrs[self.bdaddr] = 1
                           if(print_finished_bdaddrs): print(f"Successful SDPPrinting of {self.bdaddr}!")
                           if(all_2thprints_done("BTC", self.bdaddr)):
                               locked_delete_from_dict(btc_bdaddrs, btc_bdaddrs_lock, self.bdaddr)
                               if(print_finished_bdaddrs): print(f"All 2thprints collected! Deleting {self.bdaddr} from btc_bdaddrs!")
                else:
                    if(self.info_type == "GATT"):
                       external_log_write(gattprint_log_path, f"GATTPRINTING FAILURE 0x{retCode:02x} FOR: {self.bdaddr} {datetime.datetime.now()}")
                    elif(self.info_type == "LMP2thprint"):
                       external_log_write(btc2thprint_log_path, f"BTC_2THPRINT: FAILURE 0x{retCode:02x} FOR: {self.bdaddr} {datetime.datetime.now()}")
                    elif(self.info_type == "SDP"):
                       external_log_write(sdpprint_log_path, f"SDPPRINTING FAILURE 0x{retCode:02x} FOR: {self.bdaddr} {datetime.datetime.now()}")

            self.is_terminated = True
        except TimeoutExpired:
            if(print_verbose): print(f"PID: {self.process.pid}: ApplicationThread: TimeoutExpired")
            print(f"PID: {self.process.pid}: ApplicationThread: Killing pid")
            self.process.kill()
            self.is_terminated = True
            if(self.info_type == "GATT"):
               external_log_write(gattprint_log_path, f"GATTPRINTING FAILURE TIMEOUT FOR: {self.bdaddr} {datetime.datetime.now()}")
            elif(self.info_type == "LMP2thprint"):
               external_log_write(btc2thprint_log_path, f"BTC_2THPRINT: FAILURE TIMEOUT FOR: {self.bdaddr} {datetime.datetime.now()}")
            elif(self.info_type == "SDP"):
               external_log_write(sdpprint_log_path, f"SDPPRINTING FAILURE TIMEOUT FOR: {self.bdaddr} {datetime.datetime.now()}")


def launch_application(cmd, target_cwd, stdout=None):
    try:
        process = subprocess.Popen(cmd, cwd=target_cwd, stdout=stdout)
        print(f"PID: {process.pid}: central_app_launcher2.py: launched {cmd}")
#        raise BlockingIOError("FAKE I/O operation is blocked")
    except BlockingIOError as e:
        # Handle the exception gracefully, e.g., log the error and take appropriate action.
        print(f"launch_application: Caught BlockingIOError while launching application: {e}")
        # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
        print(f"launch_application: UNRECOVERABLE ERROR. REBOOTING at {datetime.datetime.now()}")
        force_reboot()
        return None
    except Exception as e:
        # Handle other exceptions that might occur.
        print(f"launch_application: Caught an exception while launching application: {e}")
        force_reboot()
        return None

    return process

def force_reboot():
    print(f"UNRECOVERABLE ERROR. REBOOTING at {datetime.datetime.now()}")
    os.system("sudo reboot")
    print("SLEEPING FOR SUPERSTITION!")
    time.sleep(30)
    os.system("sudo reboot")
    print("REBOOT STILL DIDN'T WORK?!")


##################################################
# For processing the bluetoothctl log
##################################################

bluetoothctl_log_link = '/tmp/BT_link.txt'

# Function to process a line and update the bdaddrs dictionary
# Line output looks like:
# {[NEW],[DEL} Device <bdaddr> {BLE,BTC} {random,public} <name>
# [CHG} Device <bdaddr> RSSI {various}
# [CHG] Device <bdaddr> ManufacturerData Key: 0x004c
# 0x004c is for Apple, which we want to deprioritize since we already have adequate data about them
def process_line(line):
    global device_connect_attempts
    tok = line.split()
    #print(tok)
    # We can have raw byte value lines from manufacturer data printouts
    if (len(tok) < 5 or tok[1] != "Device"):
        return

    bdaddr = tok[2].lower()
    type = tok[3] # This is technically only true for NEW and DEL but it's fine, since it's not used in CHG

    # Didn't want to deal with formatting. Just copied how tok[0] looked when I printed the tok
    if (tok[0] == '[\x01\x1b[0;92m\x02NEW\x01\x1b[0m\x02]'):
        device_connect_attempts[bdaddr] = 0 # This actually allows us to retry things which went away via a DEL and then came back
        if (type == "BLE"):
            with ble_bdaddrs_lock:
                ble_bdaddrs[bdaddr] = (tok[4], -80)
                if(BLE_thread_enabled and print_verbose): print(f"[NEW] {type} {bdaddr}")
        else:
            with btc_bdaddrs_lock:
                btc_bdaddrs[bdaddr] = (tok[4], -80)
                if(BTC_thread_enabled and print_verbose): print(f"[NEW] {type} {bdaddr}")

    # TODO: the CHG case could be made more efficient (not checking both lists) if bluetoothctl printed the type with the line...
    elif (tok[0] == '[\x01\x1b[0;93m\x02CHG\x01\x1b[0m\x02]' and tok[3] == "RSSI:"):
        with ble_bdaddrs_lock:
            if (bdaddr in ble_bdaddrs):
                (type, rssi) = ble_bdaddrs[bdaddr]
                # If we are seeing a device with a stronger signal than it previously had
                # Allow one more try to connect to it (this could happen multiple times, so it could ultimately get multiple tries)
                # This may allow us to connect to devices we weren't able to when further away
                if(rssi < int(tok[4]) and device_connect_attempts[bdaddr] > 1):
                    print(f"Higher RSSI observed. Decrementing device_connect_attempts {bdaddr} to {device_connect_attempts[bdaddr]-1}")
                    device_connect_attempts[bdaddr] -= 1
                ble_bdaddrs[bdaddr] = (type, int(tok[4]))
                type = "BLE"
                if(BLE_thread_enabled and print_verbose): print(f"Updated {type} RSSI ({tok[4]}) for {bdaddr}")

        with btc_bdaddrs_lock:
            if (bdaddr in btc_bdaddrs):
                (type, rssi) = btc_bdaddrs[bdaddr]
                # If we are seeing a device with a stronger signal than it previously had
                # Allow one more try to connect to it (this could happen multiple times, so it could ultimately get multiple tries)
                # This may allow us to connect to devices we weren't able to when further away
                if(rssi < int(tok[4]) and device_connect_attempts[bdaddr] > 1):
                    print(f"Higher RSSI observed. Decrementing device_connect_attempts {bdaddr} to {device_connect_attempts[bdaddr]-1}")
                    device_connect_attempts[bdaddr] -= 1
                btc_bdaddrs[bdaddr] = (type, int(tok[4]))
                type = "BTC"
                if(BTC_thread_enabled and print_verbose): print(f"Updated {type} RSSI ({tok[4]}) for {bdaddr}")

    elif (tok[0] == '[\x01\x1b[0;93m\x02CHG\x01\x1b[0m\x02]' and tok[3] == "ManufacturerData" and tok[4] == "Key:"):
        #print(tok)
        # Deprioritize Apple devices
        if(tok[5] == "0x004c"): # Can add more vendors here as desired
            with ble_bdaddrs_lock:
                if (bdaddr in ble_bdaddrs):
                    (type, rssi) = ble_bdaddrs[bdaddr]
                    with ble_deprioritized_bdaddrs_lock:
                        ble_deprioritized_bdaddrs[bdaddr] = (type, rssi, tok[5])
                    del ble_bdaddrs[bdaddr]
                    if(BLE_thread_enabled and print_verbose): print(f"Deprioritized BLE {type} {bdaddr} due to ManufacturerData {tok[5]}")

            with btc_bdaddrs_lock:
                if (bdaddr in btc_bdaddrs):
                    (type, rssi) = btc_bdaddrs[bdaddr]
                    with btc_deprioritized_bdaddrs_lock:
                        btc_deprioritized_bdaddrs[bdaddr] = (type, rssi, tok[5])
                    del btc_bdaddrs[bdaddr]
                    type = "BTC"
                    if(BTC_thread_enabled and print_verbose): print(f"Deprioritized BTC {type} {bdaddr} due to ManufacturerData {tok[5]}")

    elif (tok[0] == '[\x01\x1b[0;91m\x02DEL\x01\x1b[0m\x02]'):
        if (type == "BLE"):
            locked_delete_from_dict(ble_bdaddrs, ble_bdaddrs_lock, bdaddr)
            # Decided NOT to delete from the deprioritized bdaddrs for now, because it will prevent things that are on
            # the edge of signal range from popping in and out of existance, wasting resources on re-scans
            # due to not immediately knowing their deprioritized devices
            # The downside is that the list will continue to grow indefinitely, but for the time being I think that's an acceptable tradeoff
            # If it becomes a problem we can store a last-seen time and periodically drop things that haven't been seen for an hour or so
            #locked_delete_from_dict(ble_deprioritized_bdaddrs, ble_deprioritized_bdaddrs_lock, bdaddr)
            if(BLE_thread_enabled and print_verbose): print(f"[DEL] {type} {bdaddr}")
        elif (type == "BTC"):
            locked_delete_from_dict(btc_bdaddrs, btc_bdaddrs_lock, bdaddr)
            # Decided NOT to delete from the deprioritized bdaddrs for now, because it will prevent things that are on
            # the edge of signal range from popping in and out of existance, wasting resources on re-scans
            # due to not immediately knowing their deprioritized devices
            # The downside is that the list will continue to grow indefinitely, but for the time being I think that's an acceptable tradeoff
            # If it becomes a problem we can store a last-seen time and periodically drop things that haven't been seen for an hour or so
            #locked_delete_from_dict(btc_deprioritized_bdaddrs, btc_deprioritized_bdaddrs_lock, bdaddr)
            if(BTC_thread_enabled and print_verbose): print(f"[DEL] {type} {bdaddr}")
        else:
            print("Shouldn't get here. Debug script.")
            print(tok)
            quit()


##################################################
# BLE-handling thread
##################################################

def reprioritize_ble_bdaddr(bdaddr):
    with ble_bdaddrs_lock:
        type = ""
        rssi = -80
        with ble_deprioritized_bdaddrs_lock:
            if(bdaddr in ble_deprioritized_bdaddrs):
                (type, rssi, vendor) = ble_deprioritized_bdaddrs[bdaddr]
                del ble_deprioritized_bdaddrs[bdaddr]
                ble_bdaddrs[bdaddr] = (type, rssi)
                print(f"Reprioritized {type} {bdaddr} ({rssi})")

def reprioritize_btc_bdaddr(bdaddr):
    with ble_bdaddrs_lock:
        type = ""
        rssi = -80
        with btc_deprioritized_bdaddrs_lock:
            if(bdaddr in btc_deprioritized_bdaddrs):
                (type, rssi, vendor) = btc_deprioritized_bdaddrs[bdaddr]
                del btc_deprioritized_bdaddrs[bdaddr]
                btc_bdaddrs[bdaddr] = (type, rssi)
                print(f"Reprioritized {type} {bdaddr} ({rssi})")

# Function for the first thread
def ble_thread_function():
    global device_connect_attempts
    ble_external_tool_threads = []
    while True:
        # Get the BDADDRs sorted in descending order of their RSSI, so we process higher RSSI first
        sorted_ble_bdaddrs = sorted(ble_bdaddrs.keys(), key=lambda x: ble_bdaddrs[x][1], reverse=True)

        if(print_verbose):
            print(f"Begin loop through sorted_ble_bdaddrs {datetime.datetime.now()}")
            print(f"sorted_ble_bdaddrs = {sorted_ble_bdaddrs}")
            print(f"ble_deprioritized_bdaddrs = {ble_deprioritized_bdaddrs}")

        skip_count = int(0)
        for bdaddr in sorted_ble_bdaddrs:
            # Skip devices that may be traveling with us, to not waste time on them
            # Only try collecting data from a given bd_addr max_connect_attempts times before skipping forever thereafter
            # This is so that we don't waste time trying to get info from something that will never give it to us,
            # when we could be spending that time trying new devices
            if((str(bdaddr).lower() in skip_these_addresses) or (device_connect_attempts[bdaddr] >= max_connect_attempts)):
                if(print_skipped):
                    print(f"BLE: Max connect attempts exceeded for {bdaddr}, skipping")
                skip_count += 1
                if(print_skipped):
                    print(f"BLE: skip_count = {skip_count} of {len(sorted_ble_bdaddrs)}")

                # Delete it otherwise it will just keep coming up over and over again in the while True loop
                locked_delete_from_dict(ble_bdaddrs, ble_bdaddrs_lock, bdaddr)

                if(skip_count == len(sorted_ble_bdaddrs) and len(ble_deprioritized_bdaddrs) > 0):
                    print("BLE: Everything's being skipped. We could go ahead and do some deprioritized bdaddrs now...")
                    print(ble_deprioritized_bdaddrs)
                    bdaddr = list(ble_deprioritized_bdaddrs.keys())[0] # Grab a single bdaddr
                    reprioritize_ble_bdaddr(bdaddr)
                    print(ble_deprioritized_bdaddrs)

                continue
            else:
                device_connect_attempts[bdaddr] += 1

            if(print_verbose): print(f"BLE Address: {bdaddr}")

            if(gattprint_enabled):
                skip_sub_process = False
                with gatt_success_bdaddrs_lock:
                    if(bdaddr in gatt_success_bdaddrs.keys()):
                        if(print_finished_bdaddrs): print(f"We've already successfully GATTprinted {bdaddr}! Skipping!")
                        # Remove it from further consideration (it could have just been added in by a [DEL] -> [NEW] sequence)
                        if(all_2thprints_done("BLE", bdaddr)):
                            locked_delete_from_dict(ble_bdaddrs, ble_bdaddrs_lock, bdaddr)
                            if(print_finished_bdaddrs): print(f"All 2thprints collected! Deleting {bdaddr} from ble_bdaddrs!")
                        skip_sub_process = True # We can't just 'continue' here or we'd skip attempting the ll2thprint below

                # We have to check whether bdaddr is still in ble_bdaddrs because it could have been deleted via finding a [DEL] in the bluetoothctl log
                # This is a race condition...
                if(not skip_sub_process and bdaddr in ble_bdaddrs):
                    with ble_bdaddrs_lock:
                        if(bdaddr in ble_bdaddrs):
                            external_log_write(gattprint_log_path, f"GATTPRINTING ATTEMPT FOR: {bdaddr} {datetime.datetime.now()}")
                            (type, rssi) = ble_bdaddrs[bdaddr]
                            gatt_cmd = [gatttool_exec_path, "-t", type, "-b", bdaddr]
                            try:
                                gatt_process = launch_application(gatt_cmd, default_cwd)
                            except BlockingIOError as e:
                                print(f"Caught BlockingIOError while launching GATT application: {e}") # This seems to be due to a rare error while attempting a fork() within Popen()
                                # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                                force_reboot()
                            except Exception as e:
                                print(f"Caught an exception while launching GATT application: {e}")
                                # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                                force_reboot()
                            if(gatt_process != None):
                                gatt_thread = ApplicationThread(gatt_process, bdaddr, info_type="GATT", timeout=20) # Unfortunately I found some device that can take ~21 sec(!) even when tested manually
                                try:
                                    gatt_thread.start()
                                    ble_external_tool_threads.append(gatt_thread)
                                except Exception as e:
                                    print(f"Caught an exception while starting GATT thread: {e}")
                                    # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                                    force_reboot()


            if(ble_2thprint_enabled):
                skip_sub_process = False
                with ll2thprint_success_bdaddrs_lock:
                    if(bdaddr in ll2thprint_success_bdaddrs.keys()):
                        if(print_finished_bdaddrs): print(f"We've already successfully LL2thprinted {bdaddr}! Skipping!")
                        # Remove it from further consideration (it could have just been added in by a [DEL] -> [NEW] sequence)
                        if(all_2thprints_done("BLE", bdaddr)):
                            locked_delete_from_dict(ble_bdaddrs, ble_bdaddrs_lock, bdaddr)
                            if(print_finished_bdaddrs): print(f"All 2thprints collected! Deleting {bdaddr} from ble_bdaddrs!")
                        skip_sub_process = True # We can't just 'continue' here for generalism, for if we add more stuff beyond this

                if(not skip_sub_process and bdaddr in ble_bdaddrs): # Double check that bdaddr hasn't been deleted out of ble_bdaddrs by a [DEL]
                    ble_2thprint_cmd = [python2, ble2thprint, dongle1, bdaddr]
                    try:
                        ble_2thprint_process = launch_application(ble_2thprint_cmd, sweyn_cwd)
                    except BlockingIOError as e:
                        print(f"Caught BlockingIOError while launching LL2thprint application: {e}") # This seems to be due to a rare error while attempting a fork() within Popen()
                        # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                        force_reboot()
                    except Exception as e:
                        print(f"Caught an exception while launching LL2thprint application: {e}")
                        # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                        force_reboot()

                    if(ble_2thprint_process != None):
                        ble_2thprint_thread = ApplicationThread(ble_2thprint_process, bdaddr, info_type="LL2thprint", timeout=10)
                        try:
                            ble_2thprint_thread.start()
                            ble_external_tool_threads.append(ble_2thprint_thread)
                        except Exception as e:
                            print(f"Caught an exception while starting LL2thprint thread: {e}")
                            # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                            force_reboot()


            # Wait for all threads to finish, before moving to the next bd_addr
            for thread in ble_external_tool_threads:
                thread.join()
            print(f"BLE: Finished all threads for {bdaddr}")

        print(f"Finished one complete loop through sorted_ble_bdaddrs {datetime.datetime.now()}")

        # Busy wait until the diciontary has entries to process before proceeding again
        while(len(ble_bdaddrs) == 0):
            pass
       # time.sleep(5)


##################################################
# BTC-handling thread
##################################################

# Function for the second thread
def btc_thread_function():
    global device_connect_attempts
    btc_external_tool_threads = []
    while True:
        # Get the BDADDRs sorted in descending order of their RSSI, so we process higher RSSI first
        sorted_btc_bdaddrs = sorted(btc_bdaddrs.keys(), key=lambda x: btc_bdaddrs[x][1], reverse=True)

        if(print_verbose):
            print(f"Begin loop through sorted_btc_bdaddrs {datetime.datetime.now()}")
            print(f"sorted_btc_bdaddrs = {sorted_btc_bdaddrs}")
            print(f"btc_deprioritized_bdaddrs = {btc_deprioritized_bdaddrs}")

        skip_count = 0
        for bdaddr in sorted_btc_bdaddrs:
            # Skip devices that may be traveling with us, to not waste time on them
            # Only try collecting data from a given bd_addr max_connect_attempts times before skipping forever thereafter
            # This is so that we don't waste time trying to get info from something that will never give it to us,
            # when we could be spending that time trying new devices
            if((str(bdaddr).lower() in skip_these_addresses) or (device_connect_attempts[bdaddr] >= max_connect_attempts)):
                if(print_skipped):
                    print(f"BTC: Max connect attempts exceeded for {bdaddr}, skipping")
                skip_count += 1
                if(print_skipped):
                    print(f"BTC: skip_count = {skip_count} of {len(sorted_btc_bdaddrs)}")
                # Delete it otherwise it will just keep coming up over and over again in the while True loop
                locked_delete_from_dict(btc_bdaddrs, btc_bdaddrs_lock, bdaddr)

                if(skip_count == len(sorted_btc_bdaddrs) and len(btc_deprioritized_bdaddrs) > 0):
                    print("BTC: Everything's being skipped. We could go ahead and do some deprioritized bdaddrs now...")
                    print(btc_deprioritized_bdaddrs)
                    bdaddr = list(btc_deprioritized_bdaddrs.keys())[0] # Grab a single bdaddr
                    reprioritize_btc_bdaddr(bdaddr)
                    print(btc_deprioritized_bdaddrs)

                continue
            else:
                device_connect_attempts[bdaddr] += 1

            if(btc_2thprint_enabled):
                skip_sub_process = False
                with lmp2thprint_success_bdaddrs_lock:
                    if(bdaddr in lmp2thprint_success_bdaddrs.keys()):
                        if(print_finished_bdaddrs): print(f"We've already successfully LMP2thprinted {bdaddr}! Skipping!")
                        # Remove it from further consideration (it could have just been added in by a [DEL] -> [NEW] sequence)
                        if(all_2thprints_done("BTC", bdaddr)):
                            locked_delete_from_dict(btc_bdaddrs, btc_bdaddrs_lock, bdaddr)
                            if(print_finished_bdaddrs): print(f"All 2thprints collected! Deleting {bdaddr} from btc_bdaddrs!")
                        skip_sub_process = True # We can't just 'continue' here for generalism, for if we add more stuff beyond this

                if(not skip_sub_process and bdaddr in btc_bdaddrs): # Double check that bdaddr hasn't been deleted out of btc_bdaddrs by a [DEL]
                    external_log_write(btc2thprint_log_path, f"BTC_2THPRINT: LOG ENTRY FOR BDADDR: {bdaddr} {datetime.datetime.now()}")
                    btc_2thprint_cmd = [braktooth, "--exploit=LMP2thprint", "--target={}".format(bdaddr)]
                    try:
                        btc_2thprint_process = launch_application(btc_2thprint_cmd, brak_cwd) # Braktooth must be launched from its target dir, otherwise it errors out
                    except BlockingIOError as e:
                        print(f"Caught BlockingIOError while launching LMP2thprint application: {e}") # This seems to be due to a rare error while attempting a fork() within Popen()
                        # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                        force_reboot()
                    except Exception as e:
                        print(f"Caught an exception while launching LMP2thprint application: {e}")
                        # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                        force_reboot()
                    if(btc_2thprint_process != None):
                        btc_2thprint_thread = ApplicationThread(btc_2thprint_process, bdaddr, info_type="LMP2thprint", timeout=15)
                        try:
                            btc_2thprint_thread.start()
                            btc_external_tool_threads.append(btc_2thprint_thread)
                        except Exception as e:
                            print(f"Caught an exception while starting LMP2thprint thread: {e}")
                            # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                            force_reboot()

            if(sdpprint_enabled):
                skip_sub_process = False
                with sdp_success_bdaddrs_lock:
                    if(bdaddr in sdp_success_bdaddrs.keys()):
                        if(print_finished_bdaddrs): print(f"We've already successfully SDPPrinted {bdaddr}! Skipping!")
                        # Remove it from further consideration (it could have just been added in by a [DEL] -> [NEW] sequence)
                        if(all_2thprints_done("BTC", bdaddr)):
                            locked_delete_from_dict(btc_bdaddrs, btc_bdaddrs_lock, bdaddr)
                            if(print_finished_bdaddrs): print(f"All 2thprints collected! Deleting {bdaddr} from btc_bdaddrs!")
                        skip_sub_process = True # We can't just 'continue' here for generalism, for if we add more stuff beyond this

                if(not skip_sub_process and bdaddr in btc_bdaddrs): # Double check that bdaddr hasn't been deleted out of btc_bdaddrs by a [DEL]
                    external_log_write(sdpprint_log_path, f"SDPPRINTING ATTEMPT FOR: {bdaddr} {datetime.datetime.now()}")
                    output_file = open(f"{sdptool_log_path}/{bdaddr}_sdp.xml", "a") # redirect stdout to an output XML file
                    sdpprint_cmd = [sdptool_exec_path, "browse", "--xml", bdaddr]
                    try:
                        sdpprint_process = launch_application(sdpprint_cmd, default_cwd, stdout=output_file) # There should be no special CWD requirements
                    except BlockingIOError as e:
                        print(f"Caught BlockingIOError while launching application: {e}") # This seems to be due to a rare error while attempting a fork() within Popen()
                        # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                        force_reboot()
                    except Exception as e:
                        print(f"Caught an exception while launching SDP application: {e}")
                        # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                        force_reboot()

                    if(sdpprint_process != None):
                        sdpprint_thread = ApplicationThread(sdpprint_process, bdaddr, info_type="SDP", timeout=15)
                        try:
                            sdpprint_thread.start()
                            btc_external_tool_threads.append(sdpprint_thread)
                        except Exception as e:
                            print(f"Caught an exception while starting SDPprint thread: {e}")
                            # This doesn't seem to ever resolve itself for hours after it eventually occurs (which takes about 5 hours). So I need to just reboot to resolve it
                            force_reboot()

            # Wait for all threads to finish, before moving to the next bd_addr
            for thread in btc_external_tool_threads:
                thread.join()

            #if(print_verbose): print(f"BTC Address: {bdaddr}")

        print(f"Finished one complete loop through sorted_btc_bdaddrs {datetime.datetime.now()}")
        # Busy wait until the diciontary has entries to process before proceeding again
        while(len(btc_bdaddrs) == 0):
            pass
        #time.sleep(5)

##################################################
# main()
##################################################

# Monitor the file continuously using inotify
inotify = INotify()
watch_descriptor = inotify.add_watch(bluetoothctl_log_link, flags.MODIFY)

def main():

    ble_thread = threading.Thread(target=ble_thread_function)
    btc_thread = threading.Thread(target=btc_thread_function)

    if(BLE_thread_enabled): ble_thread.start()
    if(BTC_thread_enabled):btc_thread.start()


    # Keep track of the bluetoothctl log file position so we don't re-process it on each open
    bt_file_position = 0

    print("\n\n=============================================================")
    print(f"central_app_launcher2 started at {datetime.datetime.now()}")
    print("=============================================================")

    # Keep processing the bluetoothctl log file forever
    while True:
        try:
            with open(bluetoothctl_log_link, 'r') as file:
                file.seek(bt_file_position)
                for line in file:
#                    print(line)
                    process_line(line.strip())
                bt_file_position = file.tell()  # Update the file position
                if(print_verbose): print(f"Updated bt_file_position to {bt_file_position}")

            # Block until there are further modifications
            for event in inotify.read():
                #print(event)
                if event.mask & flags.MODIFY:
                    break

        except Exception as e:
            print("Exception occurred:", str(e))
            traceback.print_exc()
            quit()
            print("Continuing.")

if __name__ == "__main__":
    main()
