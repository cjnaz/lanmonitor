#!/usr/bin/env python3
"""
### service_plugin

Check that the specified service is active and running. Checking is done via `systemctl status 
<service name>` (for systemd) or `service <service_name> status` (for init).  Which init system
and service manager is in use is determined by querying the target system.

**Typical string and dictionary-style config file lines:**

    MonType_Service           =  service_plugin
    # Service_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <service_name>
    Service_firewalld         =  local  CRITICAL  1m  firewalld
    Service_sshd              =  {'u@h:p':'me@testhost2', 'recheck':'10m', 'rol':'sshd'}

**Plugin-specific _rest-of-line_ params:**

`service_name` (str)
- Service name to be checked
"""

__version__ = '4.0'

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0.
# 3.3 240805 - Updated to lanmonitor V3.3.
# 3.1 230320 - Warning for ssh fail to remote
# 3.0 230301 - Packaged
#   
#==========================================================

import datetime
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, RTNCODE_CONNECT_ATTEMPT_FAILED, cmd_check
from cjnfuncs.core import logging, periodic_log

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

        self.service_name   = item['rest_of_line'].strip()

        # Identify the system manager type - expecting 'systemd' or 'init'
        psp1_rslt = cmd_check('ps -p1', user_host_port=self.user_host_port, return_type='cmdrun', cmd_timeout=self.cmd_timeout)
        logging.debug (f"cmd_check returned:  {psp1_rslt}")

        if psp1_rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in psp1_rslt[1].stderr:
                error_msg += ' - ' + psp1_rslt[1].stderr.split('__*****__')[1]
            periodic_log (f"  <{self.key}> - {self.host} - {error_msg}", category=self.key, log_interval='1h', log_level=logging.WARNING)
            # logging.error (f"  FAIL:  <{self.key}> - {self.host} - {error_msg}")
            return RTN_WARNING

        if psp1_rslt[0] != RTN_PASS:
            error_msg = 'COULD NOT READ SYSTEM MANAGER TYPE (ps -p1 run failed)'
            if '__*****__' in psp1_rslt[1].stderr:
                error_msg += ' - ' + psp1_rslt[1].stderr.split('__*****__')[1]
            periodic_log (f"  <{self.key}> - {self.host} - {error_msg}", category=self.key, log_interval='1h', log_level=logging.WARNING)
            return RTN_FAIL

        if 'systemd' in psp1_rslt[1].stdout:
            logging.debug ("Found system manager type:  systemd")
            self.cmd = 'systemctl status ' + self.service_name
            self.check_line_text='Active:'
            self.expected_text='active (running)'
            self.not_text=None
        elif 'init' in psp1_rslt[1].stdout:
            logging.debug ("Found system manager type:  init")
            self.cmd = 'service ' + self.service_name + ' status'
            self.check_line_text=None
            self.expected_text='running'
            self.not_text='not'
        else:
            logging.error (f"  ERROR:  <{self.key}> - {self.host} - UNKNOWN SYSTEM MANAGER TYPE")
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

        rslt = cmd_check(self.cmd, user_host_port=self.user_host_port, cmd_timeout=self.cmd_timeout, return_type='check_string',
            check_line_text=self.check_line_text, expected_text=self.expected_text, not_text=self.not_text)
        # logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")
        logging.debug (f"cmd_check returned:  ({rslt[0]}, (args: '{rslt[1].args}', returncode: {rslt[1].returncode}, stdout: '{rslt[1].stdout[0:25]}...', stderr: '{rslt[1].stderr}')")


        if rslt[0] == RTN_PASS:
            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - {self.service_name}"}

        elif rslt[0] == RTN_WARNING:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_FAIL case
        if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
        else:
            error_msg = f"SERVICE <{self.service_name}> IS NOT RUNNING"
        if '__*****__' in rslt[1].stderr:
            error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
        return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}
