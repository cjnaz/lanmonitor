#!/usr/bin/env python3
"""
### fsactivity_plugin

The age of files in a directory is checked for the newest file being more recent than `age` ago.
Sub-directories may be optionally recursed. Specific files (with wildcard support) may be checked.

**Typical string and dictionary-style config file lines:**

    MonType_Activity	       =  fsactivity_plugin
    # Activity_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <age> [Recursive] <path>
    Activity_RAMDRIVE          =  local                    1h   15m recursive /mnt/RAMDRIVE/
    Activity_testhost2_*.csv   =  {'u@h:p':'me@testhost2', 'critical':True, 'recheck':'30m', 'rol':'5m  /mnt/RAMDRIVE/*.csv'}

**Plugin-specific _rest-of-line_ params:**

`age` (timevalue, or int/float seconds)
- Max age of the path (compare newest file in the directory path)

`recursive` (str, case insensitive, optional)
- If included, all directories beneath `path` are searched for the newest file

`path` (str)
- End `path` with '/' to specify that the `path` points to a directory. The newest file in that directory will be age tested.
- If `path` does not end with '/' then the leaf node of the `path` is taken as a file to be searched for and age tested. 
- Wildcards ('*' and '?') may be used in the file portion.
- If the leaf node is a file and `recursive` is also specified then the file portion will be searched for in the
specified parent folder _and all subdirectories_.

**Config file switches defined in [fsactivity] section**

`Show_filenames`  (bool, default False)
- If True, log output includes the full path to the newest found file.
- If False, the directory or file path from the config file is logged.
"""

__version__ = '4.0'

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0.  Rewrote check logic using find
# 3.3 240805 - Updated to lanmonitor V3.3.
# 3.2 230602 - Changed individual file method so as to detect file missing
# 3.1 230320 - Warning for ssh fail to remote
# 3.0 230301 - Packaged
#   
#==========================================================

import datetime
import lanmonitor.globvars as globvars
from pathlib import Path
import shlex

from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, RTNCODE_CONNECT_ATTEMPT_FAILED, cmd_check
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

        self.show_filenames = globvars.config.getcfg('Show_filenames', False, section='fsactivity')

        xx = item['rest_of_line'].split(maxsplit=1)
        try:
            maxagevar = timevalue(xx[0])
            self.maxage_sec = maxagevar.seconds
            self.units = maxagevar.unit_str
            self.unitsC = maxagevar.unit_char

            _rol = xx[1].strip()

            if _rol.lower().startswith('recursive'):
                _rol = _rol.split(maxsplit=1)[1]
                self.depth = ''
            else:
                self.depth = '-maxdepth 1'

            self.path_for_logging = _rol
            if _rol.endswith('/'):
                self.path = shlex.quote(_rol)
                self.namepart = ''
            else:
                self.path = shlex.quote(str(Path(_rol).parent))
                self.namepart = f'-name {shlex.quote(str(Path(_rol).name))}'

        except Exception as e:
            logging.exception (f"  ERROR:  <{self.key}> INVALID LINE SYNTAX <{item['rest_of_line']}>\n  {e}")
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

        cmd = f"find {self.path} {self.depth} {self.namepart} -type f -printf '%T@ %p\\n' | sort -nr | head -n 1"
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type='cmdrun', cmd_timeout=self.cmd_timeout)
        logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")
        # logging.debug (f"cmd_check returned:  ({rslt[0]}, (args: '{rslt[1].args}', returncode: {rslt[1].returncode}, stdout: '{rslt[1].stdout[0:50]}...', stderr: '{rslt[1].stderr}')")


        if rslt[0] == RTN_WARNING:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        elif rslt[0] == RTN_FAIL:
            if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
                error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            else:
                error_msg = f'COULD NOT ACCESS PATH <{self.path}/>'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_PASS case
        cmd_response = rslt[1].stdout

        if cmd_response == '':
            _path = self.path + (''  if self.path.endswith('/')  else '/')
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - FILE(S) NOT FOUND AT <{self.path_for_logging}> ({rslt[1].stderr})"}

        newest_timestamp, newest_file = cmd_response.split(maxsplit=1)
        _newest_timestamp = float(newest_timestamp)
        newest_age = datetime.datetime.now().timestamp() - _newest_timestamp

        logging.debug (f"Newest file: <{newest_file}>, datetime <{datetime.datetime.fromtimestamp(_newest_timestamp)}>")

        xx = newest_file  if self.show_filenames  else self.path_for_logging
        if newest_age < self.maxage_sec:
            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - {retime(newest_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)  {xx}"}
        else:
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key}  STALE FILES - {self.host} - {retime(newest_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)  {xx}"}
