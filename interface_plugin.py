#!/usr/bin/env python3
"""LAN Monitor plugin - interface_plugin

Each interface is checked with a `ifconfig <interface name>`, checking for 'UP' and 'RUNNING'.

      MonType_Interface		interface_plugin
      Interface_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <interface name>
      Interface_router_vlan0       local			CRITICAL  1m  vlan0
"""

__version__ = "V2.0 221130"

#==========================================================
#
#  Chris Nelson, 2021
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

        self.interface_name = item["rest_of_line"]

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{__name__}.eval_status()  called for  {self.key}")

        cmd = ["ifconfig", self.interface_name]     # ssh user@host added by cmd_check if not local
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        # print (rslt)                              # Uncomment for debug

        if rslt[0] == True:
            if "UP" not in rslt[1].stdout:
                return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - INTERFACE <{self.interface_name}> IS DOWN"}
            if "RUNNING" not in rslt[1].stdout:
                return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - INTERFACE <{self.interface_name}> IS NOT RUNNING"}
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - Interface <{self.interface_name}> is Up and Running"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - UNABLE TO READ INTERFACE <{self.interface_name}> STATE"}


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

    dotest ({"key":"Interface_local_lo", "tag":"local_lo", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"lo"})

    dotest ({"key":"Interface_router_wl0.1", "tag":"router_wl0.1", "host":"192.168.1.1", "user_host_port":"root@192.168.1.1", "critical":True, "check_interval":1, "rest_of_line":"wl0.1"})

    dotest ({"key":"Interface_bad_intf", "tag":"bad_intf", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"bad"})

    dotest ({"key":"Interface_no_interface", "tag":"local", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":""})
