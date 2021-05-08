#!/usr/bin/env python3
"""LAN Monitor plugin - service_plugin

Each service name is checked with a `systemctl status <service name>` (for systemd)
or `service <service_name> status` (for init), checking for the active/running response.

      MonType_Service		service_plugin
      Service_<friendly_name>  <local or user@host>  [CRITICAL]  <service name>
      Service_firewalld       local			CRITICAL  firewalld
      Service_RPi1_HP1018     me@RPi1.mylan     cups
"""

__version__ = "V1.0 210507"

#==========================================================
#
#  Chris Nelson, 2021
#
# V1.0 210507  Initial
#
# Changes pending
#   
#==========================================================

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

        self.service_name   = item["rest_of_line"]

        # Identify the system manager type - expecting systemd or init
        psp1_rslt = cmd_check(["ps", "-p1"], user_host_port=self.user_host_port, return_type="cmdrun")
        if not psp1_rslt[0]:
            logging.error (f"WARNING:  <{self.key}> - {self.host} - COULD NOT READ SYSTEM MANAGER TYPE (ps -p1 run failed)")
            return RTN_WARNING

        if "systemd" in psp1_rslt[1].stdout:
            self.cmd = ["systemctl", "status", self.service_name]
            self.check_line_text="Active:"
            self.expected_text="active (running)"
            self.not_text=None
        elif "init" in psp1_rslt[1].stdout:
            self.cmd = ["service", self.service_name, "status"]
            self.check_line_text=None #"Active:"
            self.expected_text="running"
            self.not_text="not"
        else:
            logging.error (f"ERROR:  <{self.key}> - {self.host} - UNKNOWN SYSTEM MANAGER TYPE")
            return RTN_FAIL

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """
        
        rslt = cmd_check(self.cmd, user_host_port=self.user_host_port, return_type="check_string",
            check_line_text=self.check_line_text, expected_text=self.expected_text, not_text=self.not_text)
        # print (rslt)                  # Uncomment for debug

        if rslt[0] == True:
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {self.service_name}"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"{self.failtext}: {self.key} - {self.host} - SERVICE {self.service_name} IS NOT RUNNING"}


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

    dotest ({"key":"Service_local_sshd", "tag":"local_sshd", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"sshd"})

    dotest ({"key":"Service_RPi2_sshd", "tag":"RPi2_sshd", "host":"RPi2", "user_host_port":"pi@RPi2.lan", "critical":False, "rest_of_line":"sshd"})

    dotest ({"key":"Service_local_xx", "tag":"local_xx", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"xx"})
