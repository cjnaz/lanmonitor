#!/usr/bin/env python3
"""LAN Monitor plugin - pinghost_plugin

Each host is pinged.  The `friendly_name` is user defined (not the real hostname).
<IP address or hostname> may be internal (local LAN) or external.

      MonType_Host		pinghost_plugin
      Host_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <IP address or hostname>
      Host_RPi1_HP1018    local    CRITICAL   1h   192.168.1.44
      Host_Yahoo          me@RPi2.mylan       15m  Yahoo.com
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
from cjnfuncs.cjnfuncs import logging

# Configs / Constants
IP_RE = re.compile(r"[\d]+\.[\d]+\.[\d]+\.[\d]+")   # Validity checks are rudimentary
HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
PING_RESPONSE_RE = re.compile(r"([\d.]+)\)*:.+time=([\d.]+) ms")

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

        self.ip_or_hostname = item["rest_of_line"]
        if (IP_RE.match(self.ip_or_hostname) is None)  and  (HOSTNAME_RE.match(self.ip_or_hostname) is None):
            logging.error (f"  ERROR:  <{self.key}> CAN'T PARSE IP OR HOSTNAME <{self.ip_or_hostname}>")
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

        cmd = ["ping", "-c", "1", "-W", "1", self.ip_or_hostname]
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        logging.debug (f"cmd_check response:  {rslt}")

        if rslt[0] == True:
            ping_rslt = PING_RESPONSE_RE.search(rslt[1].stdout)
            if ping_rslt:
                return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {self.ip_or_hostname} ({ping_rslt.group(1)} / {ping_rslt.group(2)} ms)"}
            else:
                return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - HOST <{self.ip_or_hostname}>  UNKNOWN ERROR"}  # This should not happen
        else:
            error_msg = rslt[1].stderr.replace('\n','')
            if error_msg == ""  and  "100% packet loss" in rslt[1].stdout:
                error_msg = "Cannot contact target host."
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - HOST <{self.ip_or_hostname}>  {error_msg}"}
