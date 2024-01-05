#!/usr/bin/env python3
"""LAN Monitor plugin - freespace_plugin

Free space at the specified path is checked.  The `friendly_name` is user defined (not the real path).
Expected free space may be an absolute value or a percentage.

      MonType_Free		freespace_plugin
      Free_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <free_amount>  <path>
      Free_RPi3    pi@RPi3    CRITICAL   5m   20%         /home/pi
      Free_share   local                 1d   1000000000  /mnt/share

If the path does not exist, setup() will pass but eval_status() will return RTN_WARNING and retry on each
check_interval.  This allows for intermittently missing paths.
"""
__version__ = "3.1"

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.1 230320 - Warning for ssh fail to remote
# 3.0 230301 - Packaged
#   
#==========================================================

import datetime
import re
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from cjnfuncs.core import logging

# Configs / Constants
SPACE_RE = re.compile(r"\d+ +\d+ +(\d+ +) +(\d+)%")
# df output example:
#   Filesystem     1K-blocks    Used Available Use% Mounted on
#   /dev/root       15022928 2556068  11824848  18% /
# SPACE_RE picks up group(1)='11824848', group(2)='18'


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

        percent_form = re.search("^([\d]+)%\s+(.+)", item["rest_of_line"])
        if percent_form:
            self.minfree   = int(percent_form.group(1))
            self.free_type = 'percent'
            self.path = percent_form.group(2)
            return RTN_PASS

        else:
            absolute_form = re.search("^([\d]+)\s+(.+)", item["rest_of_line"])
            if absolute_form:
                self.minfree   = int(absolute_form.group(1))
                self.free_type = 'absolute'
                self.path = absolute_form.group(2)
                return RTN_PASS

        logging.error (f"  ERROR:  <{self.key}> COULD NOT PARSE SETTINGS <{item['rest_of_line']}>")
        return RTN_FAIL


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        cmd = ["df", self.path]
        df_rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        # logging.debug (f"cmd_check response:  {df_rslt}")

        if df_rslt[0] == RTN_WARNING:
            errro_msg = df_rslt[1].stderr.replace('\n','')
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - {errro_msg}"}

        if df_rslt[0] != RTN_PASS:
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - COULD NOT GET df OF PATH <{self.path}>"}

        out = SPACE_RE.search(df_rslt[1].stdout)
        if out:
            if self.free_type == 'absolute':
                abs_free = int(out.group(1))
                if abs_free > self.minfree:
                    return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - free {abs_free}  (minfree {self.minfree})  {self.path}"}
                else:
                    return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - free {abs_free}  (minfree {self.minfree})  {self.path}"}
            else:   # percent case
                percent_free = 100 - int(out.group(2))
                if percent_free > self.minfree:
                    return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - free {percent_free}%  (minfree {self.minfree}%)  {self.path}"}
                else:
                    return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - free {percent_free}%  (minfree {self.minfree}%)  {self.path}"}
        else:
            logging.debug (f"df of <{self.path}> not parsable - returned\n  {df_rslt[1].stdout}")
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - df OF PATH <{self.path}> not parsable"}
