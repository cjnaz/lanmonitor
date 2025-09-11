#!/usr/bin/env python3
"""
### selinux_plugin

Checks that the `sestatus` _Current mode:_ value matches the `expected_mode`.

**Typical string and dictionary-style config file lines:**

    MonType_SELinux		      =  selinux_plugin
    # SELinux_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <expected_mode>
    SELinux_localhost         =  local      5m       enforcing
    SELinux_localhost2        =  {'critical':True, 'recheck':'5m', 'rol':'enforcing'}

**Plugin-specific _rest-of-line_ params:**

`expected_mode` (str)
- 'enforcing' or 'permissive'

Note: If selinux is not installed on the target host, then this plugin reports "NOT IN EXPECTED STATE...".
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
from cjnfuncs.core import logging


# Configs / Constants
SEMODES = ['enforcing', 'permissive']


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

        self.expected_mode  = item['rest_of_line'].strip()

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

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        cmd = 'sestatus'
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type='check_string', check_line_text='Current mode:', expected_text=self.expected_mode, cmd_timeout=self.cmd_timeout)
        # logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")
        logging.debug (f"cmd_check returned:  ({rslt[0]}, (args: '{rslt[1].args}', returncode: {rslt[1].returncode}, stdout: '{rslt[1].stdout[0:39]}...', stderr: '{rslt[1].stderr}')")



        if rslt[0] == RTN_PASS:
            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - {self.expected_mode}"}

        elif rslt[0] == RTN_WARNING:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_FAIL case
        if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
        else:
            current_mode = ''
            for line in rslt[1].stdout.split('\n'):
                if 'Current mode:' in line:
                    current_mode = line.split(maxsplit=2)[2]
            error_msg = f"NOT IN EXPECTED STATE - expecting <{self.expected_mode}>, found <{current_mode}>"
        if '__*****__' in rslt[1].stderr:
            error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
        return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}
