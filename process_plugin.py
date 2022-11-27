#!/usr/bin/env python3
"""LAN Monitor plugin - process_plugin

Each process is checked by seeing if the `<executable path>` occurs in the output of a `ps -Af` call.  

      MonType_Process		process_plugin
      Process_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <executable path>
      Process_x11vnc		local       CRITICAL  5m  /usr/bin/x11vnc
"""

__version__ = "V2.0 221130"

#==========================================================
#
#  Chris Nelson, 2021 - 2022
#
# V2.0 221130  Update for V2.0 changes
# V1.1 210523  Touched fail output formatting
# V1.0 210507  Initial
#
# Changes pending
#   
#==========================================================

import datetime
import globvars
from lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from funcs3 import logging

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

        self.process_path   = item["rest_of_line"]

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """
        
        cmd = ["ps", "-Af"]
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="check_string", expected_text=self.process_path)
        # logging.debug (f"cmd_check response:  {rslt}")

        if rslt[0] == True:
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {self.process_path}"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - PROCESS <{self.process_path}> IS NOT RUNNING"}


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
    logging.getLogger().setLevel(logging.DEBUG)


    def dotest (test):
        print (f"\n{test}")
        inst = monitor()
        setup_rslt = inst.setup(test)
        print (f"  setup():  {setup_rslt}")
        if setup_rslt == RTN_PASS:
            print(f"  eval_status():  {inst.eval_status()}")

    dotest ({"key":"Process_x11vnc", "tag":"x11vnc", "host":"local", "user_host_port":"local", "critical":False, "check_interval":1, "rest_of_line":"/usr/bin/x11vnc"})

    dotest ({"key":"Process_RPi3_sshd", "tag":"Process_RPi3_sshd", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":False, "check_interval":1, "rest_of_line":"/usr/sbin/sshd"})

    dotest ({"key":"Process_XXX", "tag":"XXX", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"/usr/bin/XXX"})
