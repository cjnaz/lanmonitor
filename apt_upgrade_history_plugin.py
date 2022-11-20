#!/usr/bin/env python3
"""LAN Monitor plugin - apt_upgrade_history_plugin

apt history files at /var/log/apt/* are checked for the specific <apt_command> text and the date is extracted from
the most recent occurrence of this text.  May require root access in order to read apt history.

Typical config file lines:
    MonType_AptUpgrade  apt_upgrade_history_plugin
    AptUpgrade_<friendly_name>  <local or user@host>  [CRITICAL]  <age>  <apt_command>
    AptUpgrade_MyHost  local  CRITICAL  15d  apt full-upgrade
"""

__version__ = "V1.0 221120"

#==========================================================
#
#  Chris Nelson, 2021-2022
#
# V1.0  221120  Initial
#
# Changes pending
#  The apt history file content may be locale specific.  This plugin is currently hardcoded to US style.
#   
#==========================================================

import datetime
import re
import globvars
from lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check #, convert_time
from funcs3 import logging, timevalue, retime

# Configs / Constants
HISTORY_FILES = r"/var/log/apt/history.log*"
APTLINEFORMAT = r"Start-Date: ([\d-]+  [\d:]+)\sCommandline: "
# Start-Date: 2022-10-11  20:09:49
# Commandline: apt full-upgrade


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
            maxagevar = timevalue(xx[0])
            self.maxage_sec = maxagevar.seconds
            self.units = maxagevar.unit_str
            self.unitsC = maxagevar.unit_char
            self.apt_command = xx[1]
            self.apt_RE = re.compile(APTLINEFORMAT + self.apt_command + "\n")
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
        
        cmd = ["zcat", "-qf", "/var/log/apt/history.log*"]
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        # print (rslt)                  # Uncomment for debug

        if not rslt[0]:
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - COULD NOT GET APT HISTORY"}

        dates = self.apt_RE.findall(rslt[1].stdout)
        if len(dates) == 0:
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - NO <{self.apt_command}> COMMANDS IN THE APT HISTORY LOGS"}

        last_update = 0
        for date in dates:
            timestamp = datetime.datetime.strptime(date, "%Y-%m-%d  %H:%M:%S").timestamp()
            if timestamp > last_update:
                last_update = timestamp
        last_update_age = datetime.datetime.now().timestamp() - last_update
        if last_update_age < self.maxage_sec:
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {retime(last_update_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - APT UPGRADE TOO LONG AGO - {retime(last_update_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)"}


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

    dotest ({"key":"AptUpgrade_Pass", "tag":"Pass", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "rest_of_line":"500w apt full-upgrade"})

    dotest ({"key":"AptUpgrade_TooOld", "tag":"TooOld", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "rest_of_line":"10h apt full-upgrade"})

    dotest ({"key":"AptUpgrade_NoUpgrades", "tag":"NoUpgrades", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "rest_of_line":"10h apt full-upgradeS"})

    dotest ({"key":"AptUpgrade_CantAccess", "tag":"CantAccess", "host":"nosuchhost", "user_host_port":"pi@nosuchhost", "critical":True, "rest_of_line":"10h apt full-upgrade"})

    dotest ({"key":"AptUpgrade_baddef", "tag":"badline", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"10m"})

    dotest ({"key":"AptUpgrade_badtime", "tag":"badtime", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"10y apt full-upgrade"})

