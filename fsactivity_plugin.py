#!/usr/bin/env python3
"""LAN Monitor plugin - fsactivity_plugin

The age of files at the `<path to directory or file>` is checked for at least one file being more recent than `<age>` ago.
Note that sub-directories are not recursed - only the listed top-level directory is checked for the newest file.

      MonType_Activity	fsactivity_plugin
      Activity_<friendly_name>  <local or user@host>  [CRITICAL]  <age>  <path to directory or file>
      Activity_MyServer_backups     local       8d    /mnt/share/MyServerBackups
      Activity_RPi2_log.csv         rpi2.mylan  CRITICAL  5m    /mnt/RAMDRIVE/log.csv
"""

__version__ = "V1.0 210507"

#==========================================================
#
#  Chris Nelson, 2021
#
# V1.0 210507  Initial
#
# Changes pending
#   
#==========================================================

import re
import datetime
import globvars
from lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check, convert_time
from funcs3 import logging  #, cfg, getcfg

# Configs / Constants
LSMATCH = re.compile(r'[ldrwx\-.]+\s+[\d*]\s+[\w\d]+\s+[\w\d]+\s+[\d]+\s+([\d\-]+)+\s([\d:.]+)\s([\d\-]+)')
    # Given -rwxrw-r--. 1 cjn users     976269 2021-03-11 00:30:44.049364380 -0700 filexyz.txt
    # group(1) == 2021-03-11, group(2) == 21:24:27.269508428, group(3) == -0700


class monitor:

    def __init__ (self):
        pass

    def setup (self, item):
        """ Set up instance vars and check item values.
        Passed in item dictionary keys:
            key             Full 'itemtype_tag' key value from config file line
            tag             'tag' portion only from 'itemtype_tag' from config file line
            user_host_port  'local' or 'user@hostname[:port]' from config file line
            host            'local' or 'hostname' from config file line
            critical        True if 'CRITICAL' is in the config file line
            rest_of_line    Remainder of line after the 'user_host' from the config file line
        Returns True if all good, else False
        """

        # Construct item type specifics and check validity
        self.key            = item["key"]                           # vvvv These items don't need to be modified
        self.key_padded     = self.key.ljust(globvars.keylen)
        self.tag            = item["tag"]
        self.user_host_port = item["user_host_port"]
        self.host           = item["host"]
        self.host_padded    = self.host.ljust(globvars.hostlen)
        if item["critical"]:
            self.failtype = RTN_CRITICAL
            self.failtext = "CRITICAL"
        else:
            self.failtype = RTN_FAIL
            self.failtext = "FAIL"                                  # ^^^^ These items don't need to be modified

        xx = item["rest_of_line"].split(maxsplit=1)
        try:
            self.maxage_sec, self.units = convert_time(xx[0])
            self.path = xx[1]
        except Exception as e:
            logging.error (f"ERROR:  <{self.key}> INVALID LINE SYNTAX <{item['rest_of_line']}>\n  {e}")
            return RTN_FAIL

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        cmd = ["ls", "-ltA", "--full-time", self.path]   # ssh user@host added by cmd_check if not local
        ls_rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        if not ls_rslt[0]:
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"WARNING: {self.key} - {self.host} - COULD NOT GET ls OF PATH <{self.path}>"}
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
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"WARNING: {self.key} - {self.host} - COULD NOT GET TIMESTAMP OF NEWEST FILE <{self.path}>"}

        def retime(time_sec):
            """ Convert time value back to original units """
            if self.units == "secs ":  return time_sec
            if self.units == "mins ":  return time_sec /60
            if self.units == "hours":  return time_sec /60/60
            if self.units == "days ":  return time_sec /60/60/24
            if self.units == "weeks":  return time_sec /60/60/24/7

        if newest_age < self.maxage_sec:
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {retime(newest_age):6.1f} {self.units} ({int(retime(self.maxage_sec)):>4} {self.units} max)  {self.path}"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"{self.failtext}: {self.key}  STALE FILES - {self.host} - {retime(newest_age):6.1f} {self.units} ({int(retime(self.maxage_sec)):>4} {self.units} max)  {self.path}"}


if __name__ == '__main__':
    import argparse
    from funcs3 import loadconfig

    CONFIG_FILE = "lanmonitor.cfg"

    parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--config-file', default=CONFIG_FILE,
                        help=f"Path to config file (default <{CONFIG_FILE}>).")
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__,
                        help="Return version number and exit.")

    globvars.args = parser.parse_args()
    loadconfig(cfgfile=globvars.args.config_file)

    inst = monitor()

    def dotest (test):
        print (f"\n{test}")
        inst = monitor()
        setup_rslt = inst.setup(test)
        print (f"  {setup_rslt}")
        if setup_rslt == RTN_PASS:
            print(f"  {inst.eval_status()}")

    dotest ({"key":"Activity_Shop2_backups", "tag":"Shop2_backups", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"8d /mnt/share/backups/Shop2/"})

    dotest ({"key":"Activity_rpi2_ramdrive", "tag":"rpi2_ramdrive", "host":"rpi2.lan", "user_host_port":"pi@rpi2.lan", "critical":True, "rest_of_line":"5m		/mnt/RAMDRIVE"})

    dotest ({"key":"Activity_Shop2_backups_fail", "tag":"Shop2_backups_fail", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"1h /mnt/share/backups/Shop2/"})

    dotest ({"key":"Activity_empty_dir", "tag":"empty_dir", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"1h junk"}) # empty dir in cwd

    dotest ({"key":"Activity_badpath", "tag":"badpath", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"1h /mnt/share/xxx"})

    dotest ({"key":"Activity_badhost", "tag":"badhost", "host":"rpi3.lan", "user_host_port":"pi@rpi3.lan", "critical":True, "rest_of_line":"1h /mnt/share/xxx"})
