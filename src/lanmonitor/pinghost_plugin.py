#!/usr/bin/env python3
"""
### pinghost_plugin

Ping the specified host. The `IPaddress_or_hostname` may be on the local LAN or external.

**Typical string and dictionary-style config file lines:**

    MonType_Host		        =  pinghost_plugin
    # Host_<friendly_name>      =  <local or user@host>  [CRITICAL]  <check_interval>  <IPaddress_or_hostname>
    Host_local_to_testhost2     =  local    CRITICAL   1h   testhost2
    Host_testhost2_to_yahoo.com =  {'u@h:p':'me@testhost2', 'recheck':'10m', 'rol':'yahoo.com'}
    Host_SmartPlug5             =  {'u@h:p':'local',        'recheck':'10m', 'rol':'2 smartplug5.lan'}

**Plugin-specific _rest-of-line_ params:**

`consecutive_timeout_count` (int, optional, default 1)
- If included (eg, '2' in the Host_SmartPlug5 example), this number of failing consecutive timeout calls results in a fail event.  
If fewer than this number of consecutive timeout calls then RTN_DISREGARD is returned, resulting in the timeout event(s) 
being logged but no notifications are sent.
- If not included then the `consecutive_timeout_count` defaults to 1, meaning that the first ping timeout results in a fail event.

`IPaddress_or_hostname` (str)

**Plugin-specific fail response:**

- If the ping of the `IPaddress_or_hostname` times out then `PING OF <host> FAILED - CommandTimedOut: Command did not complete 
within <n> seconds!` is the fail message if the ping was originated from local.  If originated from a remote host (via aysncssh)
the timeout message is `PING OF <host> FAILED`.  Both cases return RTN_FAIL and notifications are sent.

**Note:** Many hosts handle ICMP requests at a low priority, resulting in intermittent ping timeouts.  If the 
`consecutive_timeout_count` feature is problematic (i.e., due to increased real problem notification latency or too many false alarms), then 
consider a different method to confirm that a host is available, perhaps if the host offers a web interface, 
or allows an ssh connection (then use service_plugin, process_plugin, or ...).
"""

__version__ = '4.0'

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0.  Added consecutive_timeout_count support.
# 3.3 240805 - Updated to lanmonitor V3.3.  Removed pinghost_plugin_timeout.
# 3.1 230320 - Added config param pinghost_plugin_timeout, Warning for ssh fail to remote
# 3.0 230301 - Packaged
#   
#==========================================================

import datetime
import re
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, RTN_DISREGARD, RTNCODE_CONNECT_ATTEMPT_FAILED, cmd_check
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
            cmd_timeout     Max time in seconds allowed for the command execution in cmd_check()
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

        try:
            xx = item['rest_of_line'].split(maxsplit=1)
            if len(xx) == 2:
                self.max_consec_timeout = int(xx[0])
                self.timeout_count = 0
                self.ip_or_hostname = xx[1].strip()
            else:
                self.max_consec_timeout = 1
                self.timeout_count = 0
                self.ip_or_hostname = item['rest_of_line'].strip()
        except Exception as e:
            logging.error (f"  ERROR: <{self.key}> CAN'T PARSE SETTINGS <{item['rest_of_line']}>")
            return RTN_FAIL

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

        cmd = 'ping -c 1 ' + self.ip_or_hostname
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type='cmdrun', cmd_timeout=self.cmd_timeout)
        # logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")
        logging.debug (f"cmd_check returned:  ({rslt[0]}, (args: '{rslt[1].args}', returncode: {rslt[1].returncode}, stdout: '{rslt[1].stdout[0:50]}...', stderr: '{rslt[1].stderr}')")


        if rslt[0] == RTN_WARNING:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        elif rslt[0] == RTN_FAIL:
            if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
                error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            else:
                error_msg = f'PING OF <{self.ip_or_hostname}> FAILED'
                self.timeout_count += 1
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            
            if self.timeout_count == self.max_consec_timeout:
                self.timeout_count = 0
                return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}
            else:
                return {'rslt':RTN_DISREGARD, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}

        
        else:       # cmd_check RTN_PASS case
            ping_rslt = PING_RESPONSE_RE.search(rslt[1].stdout)
            self.timeout_count = 0
            if ping_rslt:
                return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - <{self.ip_or_hostname}> ({ping_rslt.group(1)} / {ping_rslt.group(2)} ms)"}
            else:
                return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - HOST <{self.ip_or_hostname}>  UNKNOWN ERROR"}  # This should not happen
