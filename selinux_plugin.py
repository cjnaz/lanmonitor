#!/usr/bin/env python3
"""LAN Monitor plugin - selinux_plugin

Checks that the sestatus Current mode: value matches the config file value.

      MonType_SELinux		selinux_plugin
      SELinux_<friendly_name>  <local or user@host>  [CRITICAL]  <enforcing or permissive>
      SELinux_localhost     local             enforcing
"""

__version__ = "V1.1 210523"

#==========================================================
#
#  Chris Nelson, 2021
#
# V1.1 210523  Touched fail output formatting
# V1.0 210507  Initial
#
# Changes pending
#   
#==========================================================

import globvars
from lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from funcs3 import logging

# Configs / Constants
SEMODES = ["enforcing", "permissive"]


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

        self.expected_mode  = item["rest_of_line"]

        if self.expected_mode not in SEMODES:
            logging.error (f"  ERROR:  <{self.key}> INVALID EXPECTED sestatus MODE <{self.expected_mode}> PROVIDED - EXPECTING <{SEMODES}>")
            return RTN_FAIL
        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        cmd = ["sestatus"]              # ssh user@host added by cmd_check if not local
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="check_string", check_line_text="Current mode:", expected_text=self.expected_mode)
        # print (rslt)                  # Uncomment for debug

        if rslt[0] == True:
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {self.expected_mode}"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - NOT IN EXPECTED STATE (expecting <{self.expected_mode}>)"}


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

    dotest ({"key":"SELinux_local", "tag":"local", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"enforcing"})

    dotest ({"key":"SELinux_RPiX", "tag":"RPiX", "host":"RPiX", "user_host_port":"pi@rpiX", "critical":True, "rest_of_line":"enforcing"})

    dotest ({"key":"SELinux_RPi2", "tag":"RPi2", "host":"rpi2.lan", "user_host_port":"pi@rpi2.lan", "critical":False, "rest_of_line":"enforcing"})

    dotest ({"key":"SELinux_badmode", "tag":"Shop2", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"enforcingX"})

    dotest ({"key":"SELinux_RPi2_CRIT", "tag":"RPi2_CRIT", "host":"rpi2.lan", "user_host_port":"pi@rpi2.lan", "critical":True, "rest_of_line":"enforcing"})
