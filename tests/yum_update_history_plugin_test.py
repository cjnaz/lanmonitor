#!/usr/bin/env python3
"""Demo/test for yum_update_history_plugin_test

Run on a host that uses yum

Produce / compare to golden results:
    ./yum_update_history_plugin_test.py | diff yum_update_history_plugin_test.golden -
        Expected differences:
            Ages in test 1 and 2
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 3.5 250811 - Updated to lanmonitor V3.5
# 3.3 240805 - Updated to lanmonitor V3.3
# 3.1 230320 - Added ssh access warning cases
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging, set_logging_level
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, host_connections
try:
    from yum_update_history_plugin import monitor               # Use version in cwd
except:
    from lanmonitor.yum_update_history_plugin import monitor    # Use version in the package

set_toolname('tool')

cfg = """
[DEFAULT]
Connection_timeout =            4s
Connection_nTries =             1
Connection_retry_interval =     0s

Command_nTries =                1
Command_retry_interval =        0s
Command_max_consecutive_timeouts =  2

[local]
hostname =                      localhost
username =                      me
port =                          22
"""
globvars.config = config_item()
globvars.config.read_string(cfg)

setuplogging(ConsoleLogFormat="{module:>35}.{funcName:20} - {levelname:>8}:  {message}")
set_logging_level(logging.DEBUG)


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

dotest (5, "Remote not running yum - Can't get history - CRITICAL",
        {'key':'YumUpdate_remote', 'tag':'remote', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10m update'})

dotest (6, "No matching command history - CRITICAL",
        {'key':'YumUpdate_noupdates', 'tag':'noupdates', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10m update xx'})

dotest (7, "No such host - CRITICAL",
        {'key':'YumUpdate_Unknown', 'tag':'Unknown', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'90d update'})

dotest (8, "Known host, unavailable - WARNING",
        {'key':'YumUpdate_Unavailable', 'tag':'Unavailable', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'90d update'})

dotest (9, "Invalid rest_of_line - setup Error",
        {'key':'YumUpdate_BadSetup', 'tag':'BadSetup', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'update 90d'})


host_connections.close('all')
