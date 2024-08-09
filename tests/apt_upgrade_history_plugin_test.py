#!/usr/bin/env python3
"""LAN Monitor plugin - apt_upgrade_history_plugin_test
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.3 240805 - Updated to lanmonitor V3.3.
# 3.1 230320 - Added ssh access warning cases
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS
try:
    from apt_upgrade_history_plugin import monitor
except:
    from lanmonitor.apt_upgrade_history_plugin import monitor

set_toolname('tool')
globvars.config = config_item()
globvars.config.cfg['nTries']           = 1
globvars.config.cfg['RetryInterval']    = '0s'
globvars.config.cfg['SSH_timeout']      = '4s'

setuplogging(ConsoleLogFormat="{module:>35}.{funcName:20} - {levelname:>8}:  {message}")
logging.getLogger().setLevel(logging.DEBUG)

def dotest (tnum, desc, test):
    print(f"\nTest {tnum} - {desc} {'-'*50}")
    inst = monitor()
    setup_rslt = inst.setup(test)
    logging.debug (f"{test['key']} - setup() returned:  {setup_rslt}")
    if setup_rslt == RTN_PASS:
        logging.debug (f"{test['key']} - eval_status() returned:  {inst.eval_status()}")

dotest (1, "Local pass - OK",
        {'key':'AptUpgrade_Pass', 'tag':'Pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'500w apt full-upgrade   '})

dotest (2, "Local too old - CRITICAL",
        {'key':'AptUpgrade_TooOld', 'tag':'TooOld', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m apt full-upgrade'})

dotest (3, "Local no Upgrades in history - WARNING",
        {'key':'AptUpgrade_NoUpgrades', 'tag':'NoUpgrades', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10h apt full-upgradeS'})

dotest (4, "Remote pass - OK",
        {'key':'AptUpgrade_RemotePass', 'tag':'RemotePass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'500w apt full-upgrade'})

dotest (5, "Remote too old - CRITICAL",
        {'key':'AptUpgrade_RemoteTooOld', 'tag':'RemoteTooOld', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m apt full-upgrade'})

dotest (6, "Remote no Upgrades in history - WARNING",
        {'key':'AptUpgrade_RemoteNoUpgrades', 'tag':'RemoteNoUpgrades', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10h apt full-upgradeS'})

dotest (7, "No such host - WARNING",
        {'key':'AptUpgrade_Unknown', 'tag':'Unknown', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10h apt full-upgrade'})

dotest (8, "Known host, unavailable - WARNING",
        {'key':'AptUpgrade_Unavailable', 'tag':'Unavailable', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'10h apt full-upgrade'})

dotest (9, "Bad (no) check command - setup ERROR",
        {'key':'AptUpgrade_baddef', 'tag':'badline', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10m'})

dotest (10, "Bad time limit - setup ERROR",
        {'key':'AptUpgrade_badtime', 'tag':'badtime', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10y apt full-upgrade'})
