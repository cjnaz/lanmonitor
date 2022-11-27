#!/usr/bin/env python3
"""LAN Monitor plugin - pinghost_plugin

Each host is pinged.  The `friendly_name` is user defined (not the real hostname).
<IP address or hostname> may be internal (local LAN) or external.

      MonType_Host		pinghost_plugin
      Host_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <IP address or hostname>
      Host_RPi1_HP1018    local    CRITICAL   1h   192.168.1.44
      Host_Yahoo          me@RPi2.mylan       15m  Yahoo.com
"""

__version__ = "V2.0 221130"

#==========================================================
#
#  Chris Nelson, 2021-2022
#
# V2.0 221130  Update for V2.0 changes
# V1.2 210605  Removed warning HOST IS NOT KNOWN, allowing item to be a FAIL/CRITICAL.
# V1.1 210523  Allow '_' in hosthame.  Added 1s timeout.  Touched fail output formatting.  Added print of IP address.
# V1.0 210507  Initial
#
# Changes pending
#   
#==========================================================

import datetime
import re
import globvars
from lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from funcs3 import logging

# Configs / Constants
IP_RE = re.compile(r"[\d]+\.[\d]+\.[\d]+\.[\d]+")   # Validity checks are rudimentary
HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


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

        self.ip_or_hostname = item["rest_of_line"]
        if (IP_RE.match(self.ip_or_hostname) is None)  and  (HOSTNAME_RE.match(self.ip_or_hostname) is None):
            logging.error (f"  ERROR:  <{self.key}> INVALID IP OR HOSTNAME <{self.ip_or_hostname}>")
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

        cmd = ["ping", "-c", "1", "-W", "1", self.ip_or_hostname]
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        # logging.debug (f"cmd_check response:  {rslt}")

        IP_address = "(NONE)"
        for line in rslt[1].stdout.split("\n"):
            if line.startswith("PING"):
                IP_address = line.split()[2].replace(":", "")   # dd-wrt ping response may include a ":" - "(192.168.1.56):"
                break

        if rslt[0] == True:
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - {self.ip_or_hostname} {IP_address}"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - HOST <{self.ip_or_hostname}>  {IP_address} IS NOT RESPONDING"}



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
        print ()
        inst = monitor()
        setup_rslt = inst.setup(test)
        print (f"  setup():  {setup_rslt}")
        if setup_rslt == RTN_PASS:
            print(f"  eval_status():  {inst.eval_status()}")

    dotest ({"key":"Host_local_to_RPi3", "tag":"local_to_RPi3", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"rpi3"})

    dotest ({"key":"Host_local_to_IP", "tag":"local_to_IP", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"192.168.1.1"})

    dotest ({"key":"Host_RPi3_to_Shop2", "tag":"RPi3_to_Shop2", "host":"rpi3", "user_host_port":"pi@rpi3:22", "critical":True, "check_interval":1, "rest_of_line":"shop2"})

    dotest ({"key":"Host_local_to_INV", "tag":"local_to_INV", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"invalid@hostname"})

    dotest ({"key":"Host_local_to_XX", "tag":"local_to_XX", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"XX.lan"})
