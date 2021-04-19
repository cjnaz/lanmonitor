#!/usr/bin/env python3
"""LAN Monitor plugin - selinux_plugin

Checks that the sestatus Current mode: value matches the config file value.

      MonType_SELinux		selinux_plugin
      SELinux_<friendly_name>  <local or user@host>  [CRITICAL]  <enforcing or permissive>
      SELinux_localhost     local             enforcing
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
import lanmonfuncs
from funcs3 import logging  #, cfg, getcfg

# Configs / Constants
RTN_PASS     = 0
RTN_WARNING  = 1
RTN_FAIL     = 2
RTN_CRITICAL = 3
SEMODES = ["enforcing", "permissive"]


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
        expected_mode = item["rest_of_line"]

        if expected_mode not in SEMODES:
            logging.error (f"ERROR:  <{item['key']}> Invalid expected sestatus mode <{expected_mode}> provided - expecting {SEMODES} - Aborting")
            sys.exit(1)

        # Check for remote access if non-local
        if host != "local":
            pingrslt = lanmonfuncs.cmd_check(["ping", host, "-c", "1"], user_host="local", return_type="cmdrun")
            if not pingrslt[0]:
                return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - HOST CANNOT BE REACHED"}

        # Process the item
        cmd = ["sestatus"]              # ssh user@host added by cmd_check if not local
        rslt = lanmonfuncs.cmd_check(cmd, user_host=item["user_host"], return_type="check_string", check_line_text="Current mode:", expected_text=expected_mode)
        # print (rslt)

        if rslt[0] == True:             # Pass condition
            return {"rslt":RTN_PASS, "notif_key":key, "message":f"{key_padded}  OK - {host_padded} - {expected_mode}"}
        else:
            if item["critical"]:
                return {"rslt":RTN_CRITICAL, "notif_key":key, "message":f"CRITICAL: {key} - {host} - NOT IN EXPECTED STATE (expecting {expected_mode})"}
            else:
                return {"rslt":RTN_FAIL,     "notif_key":key, "message":f"FAIL: {key} - {host} - NOT IN EXPECTED STATE (expecting {expected_mode})"}


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

    test = {"key":"SELinux_local", "keylen":15, "tag":"Shop2", "host":"local", "user_host":"local", "hostlen":10, "critical":True, "rest_of_line":"enforcing"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"SELinux_RPiX", "keylen":15, "tag":"RPiX", "host":"RPiX", "user_host":"pi@rpiX", "hostlen":10, "critical":True, "rest_of_line":"enforcing"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"SELinux_RPi2", "keylen":15, "tag":"RPi2", "host":"rpi2.lan", "user_host":"pi@rpi2.lan", "hostlen":10, "critical":False, "rest_of_line":"enforcing"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"SELinux_RPi2_CRIT", "keylen":15, "tag":"RPi2_CRIT", "host":"rpi2.lan", "user_host":"pi@rpi2.lan", "hostlen":10, "critical":True, "rest_of_line":"enforcing"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"SELinux_localX", "keylen":15, "tag":"Shop2", "host":"local", "user_host":"local", "hostlen":10, "critical":True, "rest_of_line":"enforcingX"}
    print(f"{test}\n  {inst.eval_status(test)}\n")

    sys.exit()