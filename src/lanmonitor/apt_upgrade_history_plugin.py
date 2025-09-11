#!/usr/bin/env python3
"""
### apt_upgrade_history_plugin

apt history files at /var/log/apt/* are checked for the specific `apt_command` text and the date is extracted from
the most recent occurrence of this text, then compared to the `age` limit.  May require root access in order to read apt history.

**Typical string and dictionary-style config file lines:**

    MonType_AptUpgrade           =  apt_upgrade_history_plugin
    # AptUpgrade_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>    <age>  <apt_command>
    AptUpgrade_testhost          =  local  1d  30d  apt full-upgrade
    AptUpgrade_testhost2         =  {'u@h:p':'me@testhost2', 'recheck':'1d', 'rol':'30d  apt full-upgrade'}

**Plugin-specific _rest-of-line_ params:**

`age` (timevalue, or int/float seconds)
- Max time allowed since last execution of the apt_command

`apt_command` (str)
- The apt history is scanned for this specific string

Note: The apt history file formatting may be locale specific.  This plugin is currently hardcoded to US locale.
"""

__version__ = '4.0'

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0.
# 3.3 240805 - Updated to lanmonitor V3.3.  Bug fix enable age check on local machine.
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
HISTORY_FILES = r'/var/log/apt/history.log*'
APTLINEFORMAT = r'Start-Date: ([\d-]+  [\d:]+)\sCommandline: '

# Expected log file format example:
    # Start-Date: 2022-10-11  20:09:49
    # Commandline: apt full-upgrade


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
            self.apt_command = xx[1].strip()
            self.apt_RE = re.compile(APTLINEFORMAT + self.apt_command + '\n')
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

        cmd = 'zcat -qf ' + HISTORY_FILES
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
                error_msg = f'COULD NOT GET APT HISTORY>'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_PASS case
        dates = self.apt_RE.findall(rslt[1].stdout)
        if len(dates) == 0:
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - NO <{self.apt_command}> COMMANDS IN THE APT HISTORY LOGS"}

        last_update = 0
        for date in dates:
            timestamp = datetime.datetime.strptime(date, '%Y-%m-%d  %H:%M:%S').timestamp()
            if timestamp > last_update:
                last_update = timestamp
        last_update_age = datetime.datetime.now().timestamp() - last_update
        if last_update_age < self.maxage_sec:
            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - {retime(last_update_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)"}
        else:
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - APT UPGRADE TOO LONG AGO - {retime(last_update_age, self.unitsC):6.1f} {self.units:5} ({int(retime(self.maxage_sec, self.unitsC)):>4} {self.units:5} max)"}
