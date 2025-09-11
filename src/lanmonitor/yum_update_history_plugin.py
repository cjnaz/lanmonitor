#!/usr/bin/env python3
"""
### yum_update_history_plugin

yum history output is searched for the specific `yum_command` text and the date is extracted from 
the first occurrence of this line, then compared to the `age` limit. May require root access in 
order to read yum history.

This plugin works equally well with newer Fedora-based systems (eg, RHEL 8+) that use the `dnf` command.  These
systems save the history in the yum database, and `dnf history` and `yum history` output the same content.                 

**Typical string and dictionary-style config file lines:**

    MonType_YumUpdate           =  yum_update_history_plugin
    # YumUpdate_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <yum_command>
    YumUpdate_MyHost            =  local  CRITICAL  1d  15d  update --skip-broken
    YumUpdate_MyHost2           =  {'recheck':'1d', 'rol':'30d  update'}

**Plugin-specific _rest-of-line_ params:**

`age` (timevalue, or int/float seconds)
- Max time allowed since last execution of the yum_command

`yum_command` (str)
- The yum history is scanned for this specific string
- Internal whitespace must match exactly.  Leading and trailing whitespace is trimmed off.
"""

__version__ = '4.0'

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0.
# 3.3.1 240823 - Added '--cacheonly' to yum history command to avoid temporary database updates
# 3.3 240805 - Updated to lanmonitor V3.3
# 3.2.1 240116 - Bug fix yum command match .strip()
# 3.2 240105 - Bug fix yum command must now completely match
# 3.1 230320 - Warning for ssh fail to remote
# 3.0 230301 - Packaged
#   
#==========================================================

import datetime
import re
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, RTNCODE_CONNECT_ATTEMPT_FAILED, cmd_check
from cjnfuncs.core import logging
from cjnfuncs.timevalue import timevalue, retime

# Configs / Constants
YUMLINEFORMAT=re.compile(r"[ \d]+ \| ([\w -=]+) \| ([\d :-]+) ")

# Expected yum history format example:
#    154 | update --skip-broken     | 2021-03-18 22:31 | Update         |    5 ss


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
            maxagevar = timevalue(xx[0])
            self.maxage_sec = maxagevar.seconds
            self.units = maxagevar.unit_str
            self.unitsC = maxagevar.unit_char
            self.yum_command = xx[1].strip()
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

        cmd = 'yum history --cacheonly'
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
            elif "You don't have access to the history DB." in rslt[1].stderr:
                error_msg = 'NO ACCESS TO THE YUM HISTORY DB'
            else:
                error_msg = 'COULD NOT GET YUM HISTORY'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_PASS case
        for line in rslt[1].stdout.split('\n'):
            out = YUMLINEFORMAT.match(line)
            if out:
                if out.group(1).strip() == self.yum_command:
                    try:
                        last_update = datetime.datetime.strptime(out.group(2), '%Y-%m-%d %H:%M').timestamp()
                        last_update_age = datetime.datetime.now().timestamp() - last_update
                        if last_update_age < self.maxage_sec:
                            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - {retime(last_update_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)"}
                        else:
                            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - YUM UPDATE TOO LONG AGO - {retime(last_update_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)"}
                    except Exception as e:
                        return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - FAILED WHILE READING THE YUM RESPONSE\n  {e}"}

        return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - NO <{self.yum_command}> UPDATES IN THE YUM HISTORY DB"}
