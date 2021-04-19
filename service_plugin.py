#!/usr/bin/env python3
"""LAN Monitor plugin - service_plugin

Each service name is checked with a `systemctl status <service name>` (for systemd)
or `service <service_name> status` (for init), checking for the active/running response.

      MonType_Service		service_plugin
      Service_<friendly_name>  <local or user@host>  [CRITICAL]  <service name>
      Service_firewalld       local			CRITICAL  firewalld
      Service_RPi1_HP1018     me@RPi1.mylan     cups
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
        service_name = item["rest_of_line"]

        # Check for remote access if non-local
        if host != "local":
            pingrslt = lanmonfuncs.cmd_check(["ping", host, "-c", "1"], user_host="local", return_type="cmdrun")
            if not pingrslt[0]:
                return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - HOST CANNOT BE REACHED"}

        # Identify the system manager type - expecting systemd or init
        psp1_rslt = lanmonfuncs.cmd_check(["ps", "-p1"], user_host=item['user_host'], return_type="cmdrun")
        if not psp1_rslt[0]:
            return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - COULD NOT OBTAIN SYSTEM MANAGER TYPE"}

        if "systemd" in psp1_rslt[1].stdout:
            cmd = ["systemctl", "status", service_name]
            check_line_text="Active:"
            expected_text="active (running)"
            not_text=None
        elif "init" in psp1_rslt[1].stdout:
            cmd = ["service", service_name, "status"]
            check_line_text=None #"Active:"
            expected_text="running"
            not_text="not"
        else:
            return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - UNKNOWN SYSTEM MANAGER TYPE"}

        # Process the item
        rslt = lanmonfuncs.cmd_check(cmd, user_host=item["user_host"], return_type="check_string",
            check_line_text=check_line_text, expected_text=expected_text, not_text=not_text)
        # print (rslt)

        if rslt[0] == True:             # Pass condition
            return {"rslt":RTN_PASS, "notif_key":key, "message":f"{key_padded}  OK - {host_padded} - {service_name}"}
        else:
            if item["critical"]:
                return {"rslt":RTN_CRITICAL, "notif_key":key, "message":f"CRITICAL: {key} - {host} - SERVICE {service_name} IS NOT RUNNING"}
            else:
                return {"rslt":RTN_FAIL, "notif_key":key, "message":f"FAIL: {key} - {host} - SERVICE {service_name} IS NOT RUNNING"}


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

    test = {"key":"Service_local_sshd", "keylen":20, "tag":"local_sshd", "host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"sshd"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Service_RPi2_sshd", "keylen":20, "tag":"RPi2_sshd", "host":"RPi2.lan", "user_host":"pi@RPi2.lan", "hostlen":10, "critical":False, "rest_of_line":"sshd"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Service_local_xx", "keylen":20, "tag":"local_xx", "host":"local", "user_host":"local", "hostlen":10, "critical":True, "rest_of_line":"xx"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Service_RPiX_sshd", "keylen":20, "tag":"RPiX_sshd", "host":"RPiX", "user_host":"pi@RPix.lan", "hostlen":10, "critical":False, "rest_of_line":"sshd"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Service_RPi2X_sshd", "keylen":20, "tag":"RPi2X_sshd", "host":"RPi2", "user_host":"piX@RPi2.lan", "hostlen":10, "critical":False, "rest_of_line":"sshd"}
    print(f"{test}\n  {inst.eval_status(test)}\n")

    sys.exit()