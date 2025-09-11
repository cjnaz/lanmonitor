#!/usr/bin/env python3
"""
### interface_plugin

The specified interface is queried with `ifconfig <interface_name>`, checking for 'UP' and 'RUNNING'.

**Typical string and dictionary-style config file lines:**

    MonType_Interface           =  interface_plugin
    # Interface_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <interface_name>
    Interface_testhost2_wlan0   =  me@testhost2  CRITICAL  1m  wlan0
    Interface_local_lo          =  {'recheck':'5m', 'rol':'lo'}

**Plugin-specific _rest-of-line_ params:**

`interface_name` (str)
- Name of the interface to be checked

Note: See README note regarding adding the ifconfig command path to the ssh server path environment.
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
# TODO
#   Check for blank interface in setup
#   
#==========================================================

import datetime
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, RTNCODE_CONNECT_ATTEMPT_FAILED, cmd_check
from cjnfuncs.core import logging

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

        self.interface_name = item['rest_of_line'].strip()
        if self.interface_name == '':
            logging.error (f"  ERROR:  <{self.key}> INTERFACE NAME REQUIRED, GIVEN <{self.interface_name}>")
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

        cmd = 'ifconfig ' + self.interface_name
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type='cmdrun', cmd_timeout=self.cmd_timeout)
        # logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")
        logging.debug (f"cmd_check returned:  ({rslt[0]}, (args: '{rslt[1].args}', returncode: {rslt[1].returncode}, stdout: '{rslt[1].stdout[0:40]}...', stderr: '{rslt[1].stderr}')")


        if rslt[0] == RTN_WARNING:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        elif rslt[0] == RTN_FAIL:
            if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
                error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            else:
                error_msg = f'COULD NOT GET INTERFACE <{self.interface_name}> INFO'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_PASS case
        if 'UP' not in rslt[1].stdout:
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - INTERFACE <{self.interface_name}> IS DOWN"}
        if 'RUNNING' not in rslt[1].stdout:
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - INTERFACE <{self.interface_name}> IS NOT RUNNING"}
        
        return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - Interface <{self.interface_name}> is Up and Running"}
