#!/usr/bin/env python3
"""LAN Monitor plugin - fsactivity_plugin
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
import datetime
import re
import lanmonfuncs
from funcs3 import logging  #, cfg, getcfg

# Configs / Constants
RTN_PASS     = 0
RTN_WARNING  = 1
RTN_FAIL     = 2
RTN_CRITICAL = 3
LSMATCH = re.compile(r'[ldrwx\-.]+\s+[\d*]\s+[\w\d]+\s+[\w\d]+\s+[\d]+\s+([\d\-]+)+\s([\d:.]+)\s([\d\-]+)')
    # Given -rwxrw-r--. 1 cjn users     976269 2021-03-11 00:30:44.049364380 -0700 filexyz.txt
    # group(1) == 2021-03-11, group(2) == 21:24:27.269508428, group(3) == -0700


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
        xx = item["rest_of_line"].split(maxsplit=1)
        maxage = xx[0]
        maxage_sec, units = lanmonfuncs.convert_time(maxage)     # aborts on conversion error
        path = xx[1]

        # Check for remote access if non-local
        if host != "local":
            pingrslt = lanmonfuncs.cmd_check(["ping", host, "-c", "1"], user_host="local", return_type="cmdrun")
            if not pingrslt[0]:
                return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - HOST CANNOT BE REACHED"}

        # Process the item
        cmd = ["ls", "-ltA", "--full-time", path]
        ls_rslt = lanmonfuncs.cmd_check(cmd, user_host=item['user_host'], return_type="cmdrun")
        # print (rslt)

        if not ls_rslt[0]:
            return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - COULD NOT GET ls OF PATH <{path}>"}
        ls_list = ls_rslt[1].stdout.split("\n")
        newest_file = ls_list[0]                # When path is to a file
        if newest_file.startswith("total"):
            newest_file = ls_list[1]            # When path is to a directory
        out = LSMATCH.match(newest_file)
        if out:
            xx = f"{out.group(1)} {out.group(2)[0:8]} {out.group(3)}"   # 2021-03-11 00:30:44 -0700
            newest_timestamp = (datetime.datetime.strptime(xx, "%Y-%m-%d %H:%M:%S %z")).timestamp()
            newest_age = datetime.datetime.now().timestamp() - newest_timestamp
        else:
            return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - COULD NOT GET TIMESTAMP OF NEWEST FILE <{path}>"}

        def retime(time_sec):
            """ Convert time value back to original units """
            if units == "secs ":  return time_sec
            if units == "mins ":  return time_sec /60
            if units == "hours":  return time_sec /60/60
            if units == "days ":  return time_sec /60/60/24
            if units == "weeks":  return time_sec /60/6024/7

        if newest_age < maxage_sec:
            return {"rslt":RTN_PASS, "notif_key":key, "message":f"{key_padded}  OK - {host_padded} - {retime(newest_age):6.1f} {units} ({int(retime(maxage_sec)):>4} {units} max)  {path}"}
        else:
            if item["critical"]:
                return {"rslt":RTN_CRITICAL, "notif_key":key, "message":f"CRITICAL: {key}  STALE FILES - {host} - {retime(newest_age):6.1f} {units} ({int(retime(maxage_sec)):>4} {units} max)  {path}"}
            else:
                return {"rslt":RTN_FAIL, "notif_key":key, "message":f"FAIL: {key}  STALE FILES - {host} - {retime(newest_age):6.1f} {units} ({int(retime(maxage_sec)):>4} {units} max)  {path}"}


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
 
    test = {"key":"Activity_Shop2_backups", "keylen":20, "tag":"Shop2_backups","host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"8d /mnt/share/backups/Shop2/"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Activity_rpi2_ramdrive", "keylen":20, "tag":"rpi2_ramdrive","host":"rpi2.lan", "user_host":"pi@rpi2.lan", "hostlen":10, "critical":False, "rest_of_line":"5m		/mnt/RAMDRIVE"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Activity_Shop2_backups_fail", "keylen":20, "tag":"Shop2_backups_fail","host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"1h /mnt/share/backups/Shop2/"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Activity_badpath", "keylen":20, "tag":"badpath","host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"1h /mnt/share/xxx"}
    print(f"{test}\n  {inst.eval_status(test)}\n")
    test = {"key":"Activity_badhost", "keylen":20, "tag":"badhost","host":"rpi3.lan", "user_host":"pi@rpi3.lan", "hostlen":10, "critical":False, "rest_of_line":"1h /mnt/share/xxx"}
    print(f"{test}\n  {inst.eval_status(test)}\n")

    sys.exit()