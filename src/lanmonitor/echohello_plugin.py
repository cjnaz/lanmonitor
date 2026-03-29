#!/usr/bin/env python3
"""
### echohello_plugin

Check that the target host (target_uhp) responds to an 'echo' command over ssh, as an alternative to the pinghost_plugin which can be
disregarded by the target host.  Note that this plugin only works with remote hosts that allow remote command execution
via ssh and support the command 'echo Hello', so it wont work with most IOT devices.  

TODO make work with Windows
TODO generic remote command execution?  Would allow for any remote operation

**Typical string and dictionary-style config file lines:**

    MonType_EchoHello =                 echohello_plugin
    # EchoHello_<friendly_name> =       <local or user@host>  [CRITICAL]  <check_interval>  <target_uhp>
    EchoHello_local_to_testhost =       local  CRITICAL  1m  me@testhost
    EchoHello_testhost2_to_testhost =   {'u@h:p':'me@testhost2', 'recheck':'1m', 'rol':'me@testhost'}

**Plugin-specific _rest-of-line_ params:**

`target_uhp` (str)
- Username, hostname and (optional) port to be accessed
- If the target_uhp does not contain an '@', it is taken as a config file section name, where the username, hostname (and optional port)
are obtained.
- If the hostname = 'localhost' (case insensitive) then the hostname is populated with the fqdn hostname of the host
running the check.  Note that the remote system must be allowed ssh access to the fqdn local hostname.
"""

__version__ = '4.1'

#==========================================================
#
#  Chris Nelson, Copyright 2026
#
# 4.1 260117 - New
#   
#==========================================================

import datetime
import socket
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, RTNCODE_CONNECT_ATTEMPT_FAILED, cmd_check, split_user_host_port
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

        self.target_uhp     = item['rest_of_line'].strip()

        if '@' in self.target_uhp:
            target_u, target_h, target_p = split_user_host_port(self.target_uhp)
        else:
            target_u = globvars.config.getcfg('username', section=self.target_uhp)
            target_h = globvars.config.getcfg('hostname', section=self.target_uhp)
            target_p = globvars.config.getcfg('port', 22, section=self.target_uhp)

        if target_h.lower() == 'localhost':
            target_h = socket.getfqdn()
        self.target_uhp = f"{target_u}@{target_h}:{target_p}"

        self.cmd            = f'ssh {target_u}@{target_h} -p {target_p} echo Hello'

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        rslt = cmd_check(self.cmd, user_host_port=self.user_host_port, cmd_timeout=self.cmd_timeout, return_type='cmdrun')
        logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")


        if rslt[0] == RTN_PASS:
            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} to {self.target_uhp}"}

        elif rslt[0] == RTN_WARNING:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_FAIL case
        if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
        else:
            error_msg = f"echo command failed"
        if '__*****__' in rslt[1].stderr:
            error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
        return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}
