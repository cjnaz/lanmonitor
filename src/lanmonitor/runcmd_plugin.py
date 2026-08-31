#!/usr/bin/env python3
"""
### runcmd_plugin

Run an arbitrary command on the u@h:p (locally or remotely).  One application of this plugin is as an alternative to the pinghost_plugin if the
remote host intermittently responds to ping/ICMP traffic.  Note that this plugin only works with remote hosts that allow remote command execution
via ssh, so it probably wont work with most IOT devices.

**Typical string and dictionary-style config file lines:**

    MonType_RunCmd =            runcmd_plugin
    # RunCmd_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <command>
    # RunCmd_<friendly_name> =  {'u@h:p':<'local' or 'user@host'>, 'critical':<True or False>, 'recheck':<check_interval>, \
    #                           'timeout':<timevalue>, 'rol':<'command'>, \
    #                           'log_stdout':<True or False>, 'expected_text':<str>, 'check_line_text':<str>, 'not_text':<str>}
    RunCmd_local =              local  CRITICAL  1m  echo Hello
    RunCmd_testhost2 =          {'u@h:p':'me@testhost2', 'recheck':'1m', 'rol':'echo Hello', 'log_stdout':False, 'expected_text':'Hello'}

**Plugin-specific params:**

String-style `command` / Dictionary-style `rol` (str)
- Arbitrary command to be executed on target host/u@h:p

`log_stdout` (dictionary-style only, bool, default True)
- If True, the stdout response from the command execution is included in the log output
- Set to False if the response is uninteresting or too long

`expected_text`, `check_line_text`, `not_text` (dictionary-style only, str, default None)
- Set these keys if using cmd_check's response checking features
"""

__version__ = '4.1'

#==========================================================
#
#  Chris Nelson, Copyright 2026
#
# 4.1 260831 - New
#
# TODO make work with Windows
#
#==========================================================

import datetime
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, RTNCODE_CONNECT_ATTEMPT_FAILED, cmd_check #, split_user_host_port
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

        self.key =              item['key']                           # vvvv These items don't need to be modified
        self.key_padded =       self.key.ljust(globvars.keylen)
        self.tag =              item['tag']
        self.user_host_port =   item['user_host_port']
        self.host =             item['host']
        self.host_padded =      self.host.ljust(globvars.hostlen)
        if item['critical']:
            self.failtype =     RTN_CRITICAL
            self.failtext =     'CRITICAL'
        else:
            self.failtype =     RTN_FAIL
            self.failtext =     'FAIL'
        self.next_run =         datetime.datetime.now().replace(microsecond=0)
        self.check_interval =   item['check_interval']
        self.cmd_timeout =      item['cmd_timeout']                   # ^^^^ These items don't need to be modified

        self.runcmd =           item['rest_of_line'].strip()
        self.log_stdout =       item.get('log_stdout', True)

        self.expected_text =    item.get('expected_text', None)
        self.check_line_text =  item.get('check_line_text', None)
        self.not_text =         item.get('not_text', None)
        if self.expected_text  or  self.not_text:
            if self.expected_text  and  not isinstance(self.expected_text, str):
                logging.error(f"{item['key']} - expected_text must be type str (if provided)")
                return RTN_FAIL

            if self.check_line_text  and  not isinstance(self.check_line_text, str):
                logging.error(f"{item['key']} - check_line_text must be type str (if provided)")
                return RTN_FAIL

            if self.not_text  and  not isinstance(self.not_text, str):
                logging.error(f"{item['key']} - not_text must be type str (if provided)")
                return RTN_FAIL

            self.return_type =  'check_string'
        else:
            self.return_type =  'cmdrun'

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        rslt = cmd_check(self.runcmd, user_host_port=self.user_host_port, cmd_timeout=self.cmd_timeout, 
                         return_type=self.return_type, expected_text=self.expected_text, check_line_text=self.check_line_text, not_text=self.not_text)
        logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")


        if rslt[0] == RTN_PASS:
            msg =               f"{self.key_padded}  OK - {self.host_padded}"
            if self.log_stdout:
                msg +=          f" - {rslt[1].stdout}"
            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':msg}

        elif rslt[0] == RTN_WARNING:
            error_msg =         'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg +=    ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_FAIL case
        if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
            error_msg =         'COULD NOT CONNECT TO EXECUTION HOST'
        else:
            error_msg =         f"command <{self.runcmd}> failed"
        if '__*****__' in rslt[1].stderr:
            error_msg +=        ' - ' + rslt[1].stderr.split('__*****__')[1]
        return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}
