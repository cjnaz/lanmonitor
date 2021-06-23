#!/usr/bin/env python3
"""LAN Monitor plugin - dd-wrt_age_plugin

Check the age of the dd-wrt version on the specified router.  The routerIP may be a hostname.

Typical config file lines:
    MonType_DD-wrt_age  dd-wrt_age_plugin
    DD-wrt_age_<friendly_name>  <local or user@host>  [CRITICAL]  <age>  <routerIP>
    DD-wrt_age_Router  local  CRITICAL  30d  192.168.1.1
"""

__version__ = "V1.0 210622"

#==========================================================
#
#  Chris Nelson, 2021
#
# V1.0 210622  new
#
# Changes pending
#   
#==========================================================

import datetime
import re
import globvars
from lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check, convert_time
from funcs3 import logging

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

        try:
            xx = item["rest_of_line"].split(maxsplit=1)
            self.maxage_sec, self.units = convert_time(xx[0])       # Exception on conversion error
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
        
        cmd = ["curl", self.url, "--connect-timeout", "10", "--max-time", "10"]      # ssh user@host added by cmd_check if not local
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        # print (rslt)                  # Uncomment for debug

        def retime(time_sec):
            """ Convert time value back to original units """
            if self.units == "secs ":  return time_sec
            if self.units == "mins ":  return time_sec /60
            if self.units == "hours":  return time_sec /60/60
            if self.units == "days ":  return time_sec /60/60/24
            if self.units == "weeks":  return time_sec /60/60/24/7

        out = LINEFORMAT.match(rslt[1].stdout)
        if out:
            dd_wrt_version = out.group(1)
            dd_wrt_date = out.group(2)
            dd_wrt_timestamp = (datetime.datetime.strptime(dd_wrt_date, "%m/%d/%y")).timestamp()
            dd_wrt_age = datetime.datetime.now().timestamp() - dd_wrt_timestamp

            if dd_wrt_age < self.maxage_sec:
                return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - "
                    + f"{retime(dd_wrt_age):6.1f} {self.units} ({int(retime(self.maxage_sec)):>4} {self.units} max)  "
                    + f"{self.url} - r{dd_wrt_version} - {dd_wrt_date}"}
            else:
                return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key}  DD-WRT STALE - {self.host} - "
                    + f"{retime(dd_wrt_age):6.1f} {self.units} ({int(retime(self.maxage_sec)):>4} {self.units} max)  "
                    + f"{self.url} - r{dd_wrt_version} - {dd_wrt_date}"}

        return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - NO VALID RESPONSE FROM ROUTER <{self.url}>"}


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


    def dotest (test):
        print (f"\n{test}")
        inst = monitor()
        setup_rslt = inst.setup(test)
        print (f"  {setup_rslt}")
        if setup_rslt == RTN_PASS:
            print(f"  {inst.eval_status()}")

    dotest ({"key":"DD-wrt_age_Pass", "tag":"Pass", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"90d 192.168.1.1"})

    dotest ({"key":"DD-wrt_age_Fail", "tag":"Fail", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"0d 192.168.1.1"})

    dotest ({"key":"DD-wrt_age_noreply", "tag":"Fail", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"0d 192.168.1.99"})

    dotest ({"key":"DD-wrt_age_badline", "tag":"Fail", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"0y 192.168.1.99"})
