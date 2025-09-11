#!/usr/bin/env python3
"""
### webpage_plugin

The specified web page `url` is retrieved and checked that it contains the `expected_text`. 
The `url` may be served by a local or remote server.

**Typical string and dictionary-style config file lines:**

    MonType_Page           =  webpage_plugin
    # Page_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <url>  <expected_text>
    Page_WeeWX             =  local  15m  http://localhost/weewx/  Current Conditions
    Page_xBrowserSync      =  {'u@h:p':'me@testhost2', 'recheck':'1h', 'rol':'https://www.xbrowsersync.org/  Browser syncing as it should be: secure, anonymous and free'}

**Plugin-specific _rest-of-line_ params:**

`url` (str)
- The local or remote url to be fetched

`expected_text` (str)
- Pass if the fetched url contains/includes the expected_text
- All text after the url is taken as the expected_text
- Leading and trailing whitespace is trimmed before the compare

Note: If the `url` or `expected_text` contains a `#` character then use the dictionary-style definition syntax to avoid the config file parser taking the # as the start of a comment.
"""

__version__ = '4.0'

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0.
# 3.3 240805 - Updated to lanmonitor V3.3
# 3.1 230320 - Warning for ssh fail to remote
# 3.0 230301 - Packaged
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

        xx = item['rest_of_line'].split(maxsplit=1)
        self.url = xx[0]
        self.match_text = xx[1].strip()

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        cmd = 'curl ' + self.url
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type='check_string', expected_text=self.match_text, cmd_timeout=self.cmd_timeout)
        # logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")
        logging.debug (f"cmd_check returned:  ({rslt[0]}, (args: '{rslt[1].args}', returncode: {rslt[1].returncode}, stdout: '{rslt[1].stdout[0:15]}...', stderr: '{rslt[1].stderr[0:10]}')")


        if '404 Not Found' in rslt[1].stdout:
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - WEBPAGE <{self.url}> NOT FOUND"}

        if rslt[0] == RTN_PASS:
            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - {self.url}"}

        elif rslt[0] == RTN_WARNING:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_FAIL case
        if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
        else:
            error_msg = f"WEBPAGE <{self.url}> NOT AS EXPECTED"
        if '__*****__' in rslt[1].stderr:
            error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
        return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}
