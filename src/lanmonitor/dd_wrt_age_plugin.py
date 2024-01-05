#!/usr/bin/env python3
"""LAN Monitor plugin - dd-wrt_age_plugin

Check the age of the dd-wrt version on the specified router.  The routerIP may be a hostname.

Typical config file lines:
    MonType_DD-wrt_age  dd-wrt_age_plugin
    DD-wrt_age_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <routerIP>
    DD-wrt_age_Router  local  CRITICAL  1d  30d  192.168.1.1
"""
__version__ = "3.1"

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.1 230320 - Warning for ssh fail to remote
# 3.0 230301 - Packaged
#   
# NOTE:  I no longer have a dd-wrt router to test this on.  Consider adding --max-time to the curl command.
#
#==========================================================

import datetime
import re
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from cjnfuncs.core import logging
from cjnfuncs.timevalue import timevalue, retime


# Configs / Constants
LINEFORMAT=re.compile(r'.*DD-WRT v.*-r([\d]+).+\(([\d/]+)\).*', re.DOTALL)
#  DD-WRT v3.0-r46885 std (06/05/21)


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

        try:
            xx = item["rest_of_line"].split(maxsplit=1)
            maxagevar = timevalue(xx[0])
            self.maxage_sec = maxagevar.seconds
            self.units = maxagevar.unit_str
            self.unitsC = maxagevar.unit_char
            self.url = xx[1] + "/Info.htm"
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

        cmd = ["curl", self.url, "--connect-timeout", "10", "--max-time", "10"]
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        # logging.debug (f"cmd_check response:  {rslt}")

        if rslt[0] == RTN_WARNING:
            errro_msg = rslt[1].stderr.replace('\n','')
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - {errro_msg}"}

        out = LINEFORMAT.match(rslt[1].stdout)
        if out:
            dd_wrt_version = out.group(1)
            dd_wrt_date = out.group(2)
            dd_wrt_timestamp = (datetime.datetime.strptime(dd_wrt_date, "%m/%d/%y")).timestamp()
            dd_wrt_age = datetime.datetime.now().timestamp() - dd_wrt_timestamp

            if dd_wrt_age < self.maxage_sec:
                return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - "
                    + f"{retime(dd_wrt_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)  "
                    + f"{self.url} - r{dd_wrt_version} - {dd_wrt_date}"}
            else:
                return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key}  DD-WRT STALE - {self.host} - "
                    + f"{retime(dd_wrt_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)  "
                    + f"{self.url} - r{dd_wrt_version} - {dd_wrt_date}"}

        return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - NO VALID RESPONSE FROM ROUTER <{self.url}>"}
