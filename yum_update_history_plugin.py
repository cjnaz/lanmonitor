#!/usr/bin/env python3
"""LAN Monitor plugin - yum_update_history_plugin

yum history output is checked for the specific <yum_command> text and the date is extracted from
the first occurrence this line.  May require root access in order to read yum history.

Typical config file lines:
    MonType_YumUpdate  yum_update_history_plugin
    YumUpdate_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <yum_command>
    YumUpdate_MyHost  local  CRITICAL  1d  15d  update --skip-broken
"""

__version__ = "V2.0 221130"

#==========================================================
#
#  Chris Nelson, 2021-2022
#
# V2.0 221130  Update for V2.0 changes
# V1.2 220420  Incorporated funcs3 timevalue and retime
# V1.1 210523  Touched fail output formatting
# V1.0 210507  Initial
#
# Changes pending
#   
#==========================================================

import datetime
import re
import globvars
from lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from funcs3 import logging, timevalue, retime

# Configs / Constants
YUMLINEFORMAT=re.compile(r"[ \d]+ \| [\w -]+ \| ([\d :-]+) ")
#    154 | update --skip-broken     | 2021-03-18 22:31 | Update         |    5 ss


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
            rest_of_line    Remainder of line after the 'user_host' from the config file line
        Returns True if all good, else False
        """

        logging.debug (f"{__name__}.setup()  called for  {item['key']}:\n  {item}")

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
        self.next_run       = datetime.datetime.now()
        self.check_interval = item['check_interval']                # ^^^^ These items don't need to be modified

        try:
            xx = item["rest_of_line"].split(maxsplit=1)
            maxagevar = timevalue(xx[0])
            self.maxage_sec = maxagevar.seconds
            self.units = maxagevar.unit_str
            self.unitsC = maxagevar.unit_char
            self.yum_command = xx[1]
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

        logging.debug (f"{__name__}.eval_status()  called for  {self.key}")

        cmd = ["yum", "history"]        # ssh user@host added by cmd_check if not local
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        # print (rslt)                  # Uncomment for debug

        if "You don't have access to the history DB." in rslt[1].stderr:
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - NO ACCESS TO THE YUM HISTORY DB"}
        if not rslt[0]:
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - COULD NOT GET YUM HISTORY"}

        for line in rslt[1].stdout.split("\n"):
            if self.yum_command in line:
                out = YUMLINEFORMAT.match(line)
                if out:
                    try:
                        last_update = datetime.datetime.strptime(out.group(1), "%Y-%m-%d %H:%M").timestamp()
                        last_update_age = datetime.datetime.now().timestamp() - last_update
                        if last_update_age < self.maxage_sec:
                            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {retime(last_update_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)"}
                        else:
                            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - YUM UPDATE TOO LONG AGO - {retime(last_update_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)"}
                    except Exception as e:
                        return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - FAILED WHILE READING THE YUM RESPONSE\n  {e}"}

        return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - NO <{self.yum_command}> UPDATES IN THE YUM HISTORY DB"}


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
        print ()
        inst = monitor()
        setup_rslt = inst.setup(test)
        print (f"  setup():  {setup_rslt}")
        if setup_rslt == RTN_PASS:
            print(f"  eval_status():  {inst.eval_status()}")

    dotest ({"key":"YumUpdate_Pass", "tag":"Pass", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"90d update --skip-broken"})

    dotest ({"key":"YumUpdate_TooOld", "tag":"TooOld", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10m update --skip-broken"})

    dotest ({"key":"YumUpdate_baddef", "tag":"badline", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10m"})

    dotest ({"key":"YumUpdate_badtime", "tag":"badtime", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10y update --skip-broken"})

    dotest ({"key":"YumUpdate_remote", "tag":"remote", "host":"rpi1.lan", "user_host_port":"pi@rpi1.lan", "critical":True, "check_interval":1, "rest_of_line":"10m update"})

    dotest ({"key":"YumUpdate_noupdates", "tag":"noupdates", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10m update xx"})
