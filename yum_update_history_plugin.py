#!/usr/bin/env python3
"""LAN Monitor plugin - yum_update_history_plugin

yum history output is checked for the specific <yum_command> text and the date is extracted from
the first occurrence this line.  May require root access in order to read yum history.

Typical config file lines:
    MonType_YumUpdate  yum_update_history_plugin
    YumUpdate_<friendly_name>  <local or user@host>  [CRITICAL]  <age>  <yum_command>
    YumUpdate_MyHost  local  CRITICAL  15d  update --skip-broken
"""

__version__ = "V0.0c 210419"

#==========================================================
#
#  Chris Nelson, 2021
#
# V0.0c 210419  bug fix in weeks to seconds calculation
# V0.0 210418  Initial
#
# Changes pending
#   
#==========================================================

import sys
import datetime
import re
import lanmonfuncs
from funcs3 import logging  #, cfg, getcfg

# Configs / Constants
RTN_PASS     = 0
RTN_WARNING  = 1
RTN_FAIL     = 2
RTN_CRITICAL = 3
YUMLINEFORMAT=re.compile(r"[ \d]+ \| [\w -]+ \| ([\d :-]+) ")
#    154 | update --skip-broken     | 2021-03-18 22:31 | Update         |    5 ss



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
            rslt            Integer status:  0=Pass/Good, 1=Warning, 2=Fail Std priority, 3=Fail Critical priority
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """
        
        # Construct item type specifics and check validity
        key = item["key"]
        key_padded = key.ljust(item["keylen"])
        host = item["host"]
        host_padded = host.ljust(item["hostlen"])
        xx = item["rest_of_line"].split(maxsplit=1)
        maxage, units = lanmonfuncs.convert_time(xx[0])     # aborts on conversion error
        yum_command = xx[1]

        # Check for remote access if non-local
        if host != "local":
            pingrslt = lanmonfuncs.cmd_check(["ping", host, "-c", "1"], user_host="local", return_type="cmdrun")
            if not pingrslt[0]:
                return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - HOST CANNOT BE REACHED"}

        # Process the item
        cmd = ["yum", "history"]
        rslt = lanmonfuncs.cmd_check(cmd, user_host=item["user_host"], return_type="cmdrun")
        # print (rslt)

        if "You don't have access to the history DB." in rslt[1].stderr:
            return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - NO ACCESS TO THE YUM HISTORY DB"}
        if not rslt[0]:
            return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - COULD NOT GET YUM HISTORY"}


        def retime(time_sec):
            """ Convert time value back to original units """
            if units == "secs ":  return time_sec
            if units == "mins ":  return time_sec /60
            if units == "hours":  return time_sec /60/60
            if units == "days ":  return time_sec /60/60/24
            if units == "weeks":  return time_sec /60/60/24/7

        for line in rslt[1].stdout.split("\n"):
            if yum_command in line:
                out = YUMLINEFORMAT.match(line)
                if out:
                    try:
                        last_update = datetime.datetime.strptime(out.group(1), "%Y-%m-%d %H:%M").timestamp()
                        last_update_age = datetime.datetime.now().timestamp() - last_update
                        if last_update_age < maxage:        # Pass condition
                            return {"rslt":RTN_PASS, "notif_key":key, "message":f"{key_padded}  OK - {host_padded} - {retime(last_update_age):6.1f} {units} ({int(retime(maxage)):>4} {units} max)"}
                        else:
                            if item["critical"]:
                                return {"rslt":RTN_CRITICAL, "notif_key":key, "message":f"CRITICAL: {key} - {host} - YUM UPDATE TOO LONG AGO - {retime(last_update_age):6.1f} {units} ({int(retime(maxage)):>4} {units} max)"}
                            else:
                                return {"rslt":RTN_FAIL, "notif_key":key, "message":f"FAIL: {key} - {host} - YUM UPDATE TOO LONG AGO - {retime(last_update_age):6.1f} {units} ({int(retime(maxage)):>4} {units} max)"}
                    except Exception as e:
                        return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - FAILED WHILE READING THE YUM RESPONSE\n  {e}"}

        return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - NO UPDATES IN THE YUM HISTORY DB"}


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
 
    test = {"key":"YumUpdate_Pass", "keylen":20, "tag":"MyHost","host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"90d update --skip-broken"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"YumUpdate_TooOld", "keylen":20, "tag":"TooOld","host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"10m update --skip-broken"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"YumUpdate_remote", "keylen":20, "tag":"remote","host":"rpi1.lan", "user_host":"pi@rpi1.lan", "hostlen":10, "critical":False, "rest_of_line":"10m update"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"YumUpdate_noupdates", "keylen":20, "tag":"noupdates","host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"10m update xx"}
    print(f"{test}\n  {inst.eval_status(test)}\n")

    sys.exit()