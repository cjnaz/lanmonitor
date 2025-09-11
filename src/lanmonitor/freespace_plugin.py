#!/usr/bin/env python3
"""
### freespace_plugin

The free space on the file system that holds the specified `path` on the specified `u@h:p` is checked. 
Expected free space may be an absolute value or a percentage. If the path does not exist, setup() will
pass but eval_status() will fail.

**Typical string and dictionary-style config file lines:**

    MonType_Free		   =  freespace_plugin
    # Free_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <free_amount>  <path>
    Free_testhost2         =  me@testhost2    CRITICAL   5m   20%         /home/me
    Free_root              =  {'u@h:p':'local',  'recheck':'1d', 'rol':'10000000  /'}

**Plugin-specific _rest-of-line_ params:**

`free_amount` (integer or percentage)
- Minimum free number of 1K-blocks or percentage

`path` (str)
- Directory path on the specified `u@h:p` host
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
import re
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, RTNCODE_CONNECT_ATTEMPT_FAILED, cmd_check
from cjnfuncs.core import logging

# Configs / Constants
SPACE_RE = re.compile(r"\d+ +\d+ +(\d+ +) +(\d+)%")
# df output example:
#   Filesystem     1K-blocks    Used Available Use% Mounted on
#   /dev/root       15022928 2556068  11824848  18% /
# SPACE_RE picks up group(1)='11824848', group(2)='18'


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

        percent_form = re.search('^([\d]+)%\s+(.+)', item['rest_of_line'])
        if percent_form:
            self.minfree   = int(percent_form.group(1))
            self.free_type = 'percent'
            self.path = '"' + percent_form.group(2).strip() + '"'
            return RTN_PASS

        else:
            absolute_form = re.search('^([\d]+)\s+(.+)', item['rest_of_line'])
            if absolute_form:
                self.minfree   = int(absolute_form.group(1))
                self.free_type = 'absolute'
                self.path = '"' + absolute_form.group(2).strip() +'"'
                return RTN_PASS

        logging.error (f"  ERROR:  <{self.key}> COULD NOT PARSE SETTINGS <{item['rest_of_line']}>")
        return RTN_FAIL


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        cmd = 'df ' + self.path
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type='cmdrun', cmd_timeout=self.cmd_timeout)
        # logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")
        logging.debug (f"cmd_check returned ({rslt[0]}, (args: '{rslt[1].args}', returncode: '{rslt[1].returncode}', stdout: '{rslt[1].stdout[0:30]}...,' stderr: '{rslt[1].stderr}')")


        if rslt[0] == RTN_WARNING:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        elif rslt[0] == RTN_FAIL:
            if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
                error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            else:
                error_msg = f'COULD NOT GET df OF PATH <{self.path}>'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_PASS case
        out = SPACE_RE.search(rslt[1].stdout)
        if out:
            if self.free_type == 'absolute':
                abs_free = int(out.group(1))
                if abs_free > self.minfree:
                    return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - free {abs_free}  (minfree {self.minfree})  {self.path}"}
                else:
                    return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - free {abs_free}  (minfree {self.minfree})  {self.path}"}
            else:   # percent case
                percent_free = 100 - int(out.group(2))
                if percent_free > self.minfree:
                    return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - free {percent_free}%  (minfree {self.minfree}%)  {self.path}"}
                else:
                    return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - free {percent_free}%  (minfree {self.minfree}%)  {self.path}"}
        else:
            logging.debug (f"df of <{self.path}> not parsable - returned\n  {rslt[1].stdout}")
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - df OF PATH <{self.path}> not parsable"}
