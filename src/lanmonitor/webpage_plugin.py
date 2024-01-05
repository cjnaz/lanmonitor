#!/usr/bin/env python3
"""LAN Monitor plugin - webpage_plugin

The specified web page <url> is retrieved and checked that it contains the <expected text>. 
The url may be on a local or remote server.

      MonType_Page		webpage_plugin
      Page_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <url>  <expected text>
      Page_WeeWX              local             15m  http://localhost/weewx/             Current Conditions
      Page_xBrowserSync       me@RPi2.mylan     1h   https://www.xbrowsersync.org/       Browser syncing as it should be: secure, anonymous and free
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
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from cjnfuncs.core import logging

# Configs / Constants


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
        self.url = xx[0]
        self.match_text = xx[1]

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        cmd = ["curl", self.url, "--connect-timeout", "10", "--max-time", "10"]
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="check_string", expected_text=self.match_text)
        # logging.debug (f"cmd_check response:  {rslt}")

        if "404 Not Found" in rslt[1].stdout:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - WEBPAGE <{self.url}> NOT FOUND"}

        if rslt[0] == RTN_PASS:
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {self.url}"}
        elif rslt[0] == RTN_WARNING:
            errro_msg = rslt[1].stderr.replace('\n','')
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - {errro_msg}"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - WEBPAGE <{self.url}> NOT AS EXPECTED"}
