#!/usr/bin/env python3
"""Demo/test for webpage_plugin_test

Run on system hosting weewx

Produce / compare to golden results:
    ./webpage_plugin_test.py | diff webpage_plugin_test.golden -
        Expected differences:
            None
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0
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
    from webpage_plugin import monitor                  # Use version in cwd
except:
    from lanmonitor.webpage_plugin import monitor       # Use version in the package

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

dotest (1, "Local, page found - OK",
        {'key':'Page_WeeWX', 'tag':'WeeWX', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'   http://localhost/weewx/ Current Conditions   '})

dotest (2, "Local, page found, no match - CRITICAL",
        {'key':'Page_WeeWX-X', 'tag':'WeeWX-X', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'http://localhost/weewx/ XCurrent Conditions'})

dotest (3, "Local, page not found - FAIL",
        {'key':'Page_Bogus', 'tag':'Bogus', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'http://localhost/bogus/ whatever'})

dotest (4, "Remote, page found - OK",
        {'key':'Page_xBrowserSync', 'tag':'xBrowserSync', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'   https://www.xbrowsersync.org/ Browser syncing as it should be: secure, anonymous and   '})

dotest (5, "No such host - CRITICAL",
        {'key':'Page_Unknown', 'tag':'Unknown', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'http://localhost/weewx/ Current Conditions'})

dotest (6, "Known host, unavailable - WARNING",
        {'key':'Page_Unavailable', 'tag':'Unavailable', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'http://localhost/weewx/ Current Conditions'})


host_connections.close('all')
