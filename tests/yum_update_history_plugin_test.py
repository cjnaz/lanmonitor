#!/usr/bin/env python3
"""LAN Monitor plugin - yum_update_history_plugin_test
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.3 240805 - Updated to lanmonitor V3.3
# 3.1 230320 - Added ssh access warning cases
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS
try:
    from yum_update_history_plugin import monitor
except:
    from lanmonitor.yum_update_history_plugin import monitor

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

dotest (1, "YumUpdate pass - OK",
        {'key':'YumUpdate_Pass', 'tag':'Pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'   90d update  '})

dotest (2, "YumUpdate too old - CRITICAL",
        {'key':'YumUpdate_TooOld', 'tag':'TooOld', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10m update'})

dotest (3, "Bad definition - setup ERROR",
        {'key':'YumUpdate_baddef', 'tag':'badline', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10m'})

dotest (4, "Bad time - setup ERROR",
        {'key':'YumUpdate_badtime', 'tag':'badtime', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10y update'})

dotest (5, "Remote not running yum - Can't get history - WARNING",
        {'key':'YumUpdate_remote', 'tag':'remote', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10m update'})

dotest (6, "No matching command history - WARNING",
        {'key':'YumUpdate_noupdates', 'tag':'noupdates', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10m update xx'})

dotest (7, "No such host - WARNING",
        {'key':'YumUpdate_Unknown', 'tag':'Unknown', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'90d update'})

dotest (8, "Known host, unavailable - WARNING",
        {'key':'YumUpdate_Unavailable', 'tag':'Unavailable', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'90d update'})
