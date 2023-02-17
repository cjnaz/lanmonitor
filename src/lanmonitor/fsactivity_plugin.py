#!/usr/bin/env python3
"""LAN Monitor plugin - fsactivity_plugin

The age of files at the `<path to directory or file>` is checked for at least one file being more recent than `<age>` ago.
Note that sub-directories are not recursed - only the listed top-level directory is checked for the newest file.

      MonType_Activity	fsactivity_plugin
      Activity_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <path to directory or file>
      Activity_MyServer_backups     local       1d  8d    /mnt/share/MyServerBackups
      Activity_RPi2_log.csv         rpi2.mylan  CRITICAL  30s  5m    /mnt/RAMDRIVE/log.csv
"""
__version__ = "3.0"

#==========================================================
#
#  Chris Nelson, Copyright 2021-2023
#
# 3.0 230301 - Packaged
#   
#==========================================================

import datetime
import re
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from cjnfuncs.cjnfuncs import logging, timevalue, retime

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
            check_interval  Time in seconds between rechecks
            rest_of_line    Remainder of line (plugin specific formatting)
        Returns True if all good, else False
        """

        logging.debug (f"{item['key']} - {__name__}.setup() called:\n  {item}")

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
            self.failtext = "FAIL"
        self.next_run       = datetime.datetime.now().replace(microsecond=0)
        self.check_interval = item['check_interval']                # ^^^^ These items don't need to be modified

        xx = item["rest_of_line"].split(maxsplit=1)
        try:
            maxagevar = timevalue(xx[0])
            self.maxage_sec = maxagevar.seconds
            self.units = maxagevar.unit_str
            self.unitsC = maxagevar.unit_char
            self.path = xx[1]
        except Exception as e:
            logging.error (f"  ERROR:  <{self.key}> INVALID LINE SYNTAX <{item['rest_of_line']}>\n  {e}")
            return RTN_FAIL

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        cmd = ["ls", "-ltA", "--full-time", self.path]
        ls_rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        # logging.debug (f"cmd_check response:  {ls_rslt}")

        if not ls_rslt[0]:
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - COULD NOT GET ls OF PATH <{self.path}>"}
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
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - COULD NOT GET TIMESTAMP OF NEWEST FILE <{self.path}>"}

        if newest_age < self.maxage_sec:
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {retime(newest_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)  {self.path}"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key}  STALE FILES - {self.host} - {retime(newest_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)  {self.path}"}
