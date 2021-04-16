#!/usr/bin/env python3
"""LAN Monitor plugin - pinghost_plugin
"""

__version__ = "V0.0 210415"

#==========================================================
#
#  Chris Nelson, 2021
#
# V0.0 210415  Initial
#
# Changes pending
#   
#==========================================================

import sys
import re
import lanmonfuncs
from funcs3 import logging  #, cfg, getcfg

# Configs / Constants
RTN_PASS     = 0
RTN_WARNING  = 1
RTN_FAIL     = 2
RTN_CRITICAL = 3
IP_RE = re.compile(r"[\d]+\.[\d]+\.[\d]+\.[\d]+")   # Validity checks are rudimentary
HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9.-]+$")


class monitor:

    def __init__ (self):
        pass

    def eval_status (self, item):
        """ Primary function for checking the status of this item type.
        Passed in item dictionary keys:
            key             Full 'itemtype_tag' key value from config file line
            keylen          string length of longest key of this item type
            tag             'tag' portion only from 'itemtype_tag' from config file line
            user_host       'local' or 'user@hostname' from config file line
            host            'local' or 'hostname' from config file line
            hostlen         string length of longest host of this item type
            critical        True if 'CRITICAL' is in the config file line
            rest_of_line    Remainder of line after the 'user_host' from the config file line

        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """
        
        # Construct item type specifics and check validity
        key = item["key"]
        key_padded = key.ljust(item["keylen"])
        host = item["host"]
        host_padded = host.ljust(item["hostlen"])
        ip_or_hostname = item["rest_of_line"]


        if (IP_RE.match(ip_or_hostname) is None)  and  (HOSTNAME_RE.match(ip_or_hostname) is None):
            logging.error (f"ERROR:  <{key}> Invalid IP or hostname provided <{ip_or_hostname}> - Aborting")
            sys.exit(1)

        # Check for remote access if non-local
        if host != "local":
            pingrslt = lanmonfuncs.cmd_check(["ping", host, "-c", "1"], user_host="local", return_type="cmdrun")
            if not pingrslt[0]:
                return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - HOST CANNOT BE REACHED"}

        # Process the item
        cmd = ["ping", ip_or_hostname, "-c", "1"]              # <ssh user@host> added by cmd_check if not local
        rslt = lanmonfuncs.cmd_check(cmd, user_host=item["user_host"], return_type="cmdrun")
        # print (rslt)

        if rslt[0] == True:             # Pass condition
            return {"rslt":RTN_PASS, "notif_key":key, "message":f"{key_padded}  OK - {host_padded} - {ip_or_hostname}"}
        else:
            if item["critical"]:
                return {"rslt":RTN_CRITICAL, "notif_key":key, "message":f"CRITICAL: {key} - {host} - HOST {ip_or_hostname} IS NOT RESPONDING"}
            else:
                return {"rslt":RTN_FAIL, "notif_key":key, "message":f"FAIL: {key} - {host} - HOST {ip_or_hostname} IS NOT RESPONDING"}



if __name__ == '__main__':
    import argparse
    from funcs3 import loadconfig

    CONFIG_FILE = "lanmonitor.cfg"

    parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--config-file', default=CONFIG_FILE,
                        help=f"Path to config file (default <{CONFIG_FILE}>).")
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__,
                        help="Return version number and exit.")

    lanmonfuncs.args = parser.parse_args()
    loadconfig(cfgfile=lanmonfuncs.args.config_file)

    inst = monitor()

    test = {"key":"Host_local_to_RPi2", "keylen":15, "tag":"local_to_RPi2", "host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"rpi2.lan"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Host_local_to_IP", "keylen":15, "tag":"local_to_IP", "host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"192.168.1.1"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Host_RPi2_to_Shop2", "keylen":15, "tag":"RPi2_to_Shop2", "host":"rpi2.lan", "user_host":"pi@rpi2.lan", "hostlen":10, "critical":False, "rest_of_line":"shop2.lan"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Host_local_to_XX", "keylen":15, "tag":"local_to_XX", "host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"XX.lan"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Host_local_to_INV", "keylen":15, "tag":"local_to_INV", "host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"invalid@hostname"}
    print(f"{test}\n  {inst.eval_status(test)}\n")

    sys.exit()
