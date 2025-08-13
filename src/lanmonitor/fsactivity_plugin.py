#!/usr/bin/env python3
"""
### fsactivity_plugin

The age of files in a directory is checked for the newest file being more recent than `age` ago.
Sub-directories may be optionally recursed, but not in conjunction with specific files (or with wildcards).
Alternately, the age of a specific file (or with wildcards) in the specified directory may be checked.

**Typical string and dictionary-style config file lines:**

    MonType_Activity	       =  fsactivity_plugin
    # Activity_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <age> [Recursive] <path>
    Activity_RAMDRIVE          =  local                    1h   15m recursive /mnt/RAMDRIVE/
    Activity_testhost2_*.csv   =  {'u@h:p':'me@testhost2', 'critical':True, 'recheck':'30m', 'rol':'5m  /mnt/RAMDRIVE/*.csv'}

**Plugin-specific _rest-of-line_ params:**

`age` (timevalue, or int/float seconds)
- Max age of the path (newest file in the path directory or specific file)

`recursive` (str, case insensitive, optional)
- May only be applied if the `path` is to a directory.  Ignored if `path` is to a file or with wildcards.
- If included, all directories beneath `path` are searched for the newest file

`path` (str)
- If to a directory then the `recursive` param may also be specified
- If to a file(s) then wildcards ('*' and '?') are supported
"""

__version__ = "3.5"

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 3.5 250811 - Updated to lanmonitor V3.5.  Rewrote check logic using find
# 3.3 240805 - Updated to lanmonitor V3.3.
# 3.2 230602 - Changed individual file method so as to detect file missing
# 3.1 230320 - Warning for ssh fail to remote
# 3.0 230301 - Packaged
#   
#==========================================================

import datetime
import lanmonitor.globvars as globvars
import pathlib
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from cjnfuncs.core import logging
from cjnfuncs.timevalue import timevalue, retime


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
            cmd_timeout     Max time in seconds allowed for the SSH call in cmd_check()
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
        try:
            maxagevar = timevalue(xx[0])
            self.maxage_sec = maxagevar.seconds
            self.units = maxagevar.unit_str
            self.unitsC = maxagevar.unit_char

            self.path = xx[1].strip().replace(' ', '\\ ').replace("'", "\\'")
            self.depth = ' -maxdepth 1 '
            _rol = self.path.lower()
            if _rol.startswith('recursive'):
                self.depth = ' '
                self.path = self.path.split(maxsplit=1)[1].replace(' ', '\\ ').replace("'", "\\'")

        except Exception as e:
            logging.error (f"  ERROR:  <{self.key}> INVALID LINE SYNTAX <{item['rest_of_line']}>\n  {e}")
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

        cmd = 'find ' + self.path + self.depth + "-type f -printf '%T@ %p\\n' | sort -nr | head -n 1"
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type='cmdrun', cmd_timeout=self.cmd_timeout)
        logging.debug (f"cmd_check response:  {rslt}")

        if rslt[0] == RTN_WARNING:           # ssh: Could not resolve hostname xxx: Name or service not known
            error_msg = rslt[1].stderr.replace('\n','')
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        if rslt[0] != RTN_PASS:
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - COULD NOT ACCESS PATH <{self.path}>"}

        cmd_response = rslt[1].stdout

        if cmd_response == '':
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - FILE(S) NOT FOUND AT <{self.path}>"}

        newest_timestamp, newest_file = cmd_response.split(maxsplit=1)
        newest_age = datetime.datetime.now().timestamp() - float(newest_timestamp)

        if newest_age < self.maxage_sec:
            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - {retime(newest_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)  {newest_file}"}
        else:
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key}  STALE FILES - {self.host} - {retime(newest_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)  {newest_file}"}
