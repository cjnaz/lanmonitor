#!/usr/bin/env python3
"""
### pinghost_plugin

Ping the specified host. The `IPaddress_or_hostname` may be on the local LAN or external.

**Typical string and dictionary-style config file lines:**

    MonType_Host		        =  pinghost_plugin
    # Host_<friendly_name>      =  <local or user@host>  [CRITICAL]  <check_interval>  <IPaddress_or_hostname>
    Host_local_to_testhost2     =  local    CRITICAL   1h   testhost2
    Host_testhost2_to_yahoo.com =  {'u@h:p':'me@testhost2', 'recheck':'10m', 'rol':'yahoo.com'}

**Plugin-specific _rest-of-line_ params:**

`IPaddress_or_hostname` (str)

**Plugin-specific fail response:**

- If the ping of the `IPaddress_or_hostname` times out (subprocess.run() timeout) then 'Cannot contact target host' is the fail message.
"""

__version__ = "3.3"

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.3 240805 - Updated to lanmonitor V3.3.  Removed pinghost_plugin_timeout.
# 3.1 230320 - Added config param pinghost_plugin_timeout, Warning for ssh fail to remote
# 3.0 230301 - Packaged
#   
#==========================================================

import datetime
import re
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from cjnfuncs.core import logging
from cjnfuncs.timevalue import timevalue
import lanmonitor.globvars as globvars

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
            cmd_timeout     Max time in seconds allowed for the subprocess.run call in cmd_check()
            rest_of_line    Remainder of line (plugin specific formatting)
        Returns True if all good, else False
        """

        logging.debug (f"{item['key']} - {__name__}.setup() called:\n  {item}")

        self.key            = item['key']                           # vvvv These items don't need to be modified
        self.key_padded     = self.key.ljust(globvars.keylen)
        self.tag            = item['tag']
        self.user_host_port = item['user_host_port']
        self.host           = item['host']
        self.host_padded    = self.host.ljust(globvars.hostlen)
        if item['critical']:
            self.failtype = RTN_CRITICAL
            self.failtext = 'CRITICAL'
        else:
            self.failtype = RTN_FAIL
            self.failtext = 'FAIL'
        self.next_run       = datetime.datetime.now().replace(microsecond=0)
        self.check_interval = item['check_interval']
        self.cmd_timeout    = item['cmd_timeout']                   # ^^^^ These items don't need to be modified

        self.ip_or_hostname = item['rest_of_line'].strip()
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

        cmd = ['ping', '-c', '1', self.ip_or_hostname]
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type='cmdrun', cmd_timeout=self.cmd_timeout)
        # logging.debug (f"cmd_check response:  {rslt}")

        if rslt[0] == RTN_PASS:
            ping_rslt = PING_RESPONSE_RE.search(rslt[1].stdout)
            if ping_rslt:
                return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - {self.ip_or_hostname} ({ping_rslt.group(1)} / {ping_rslt.group(2)} ms)"}
            else:
                return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - HOST <{self.ip_or_hostname}>  UNKNOWN ERROR"}  # This should not happen

        elif rslt[0] == RTN_WARNING:
            error_msg = rslt[1].stderr.replace('\n','')
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - HOST <{self.ip_or_hostname}>  {error_msg}"}

        else: # RTN_FAIL
            if rslt[1].stderr == ""  or  "cmd_check subprocess.run timeout" in rslt[1].stderr:
                error_msg = "Cannot contact target host"
            else:
                error_msg = rslt[1].stderr.replace('\n','')
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - HOST <{self.ip_or_hostname}>  {error_msg}"}
