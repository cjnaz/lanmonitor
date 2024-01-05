#!/usr/bin/env python3
"""LAN Monitor plugin - webpage_plugin_test
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.1 230320 - Added ssh access warning cases
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS
try:
    from webpage_plugin import monitor
except:
    from lanmonitor.webpage_plugin import monitor

set_toolname("tool")
globvars.config = config_item()
globvars.config.cfg["nRetries"]         = 1
globvars.config.cfg["RetryInterval"]    = "0s"
setuplogging(ConsoleLogFormat="{module:>35}.{funcName:20} - {levelname:>8}:  {message}")
logging.getLogger().setLevel(logging.DEBUG)

def dotest (tnum, desc, test):
    print(f"\nTest {tnum} - {desc} {'-'*50}")
    inst = monitor()
    setup_rslt = inst.setup(test)
    logging.debug (f"{test['key']} - setup() returned:  {setup_rslt}")
    if setup_rslt == RTN_PASS:
        logging.debug (f"{test['key']} - eval_status() returned:  {inst.eval_status()}")

dotest (1, "Local, page found - OK",
        {"key":"Page_WeeWX", "tag":"WeeWX", "host":"local", "user_host_port":"local", "critical":False, "check_interval":1, "rest_of_line":"http://localhost/weewx/ Current Conditions"})

dotest (2, "Local, page found, no match - CRITICAL",
        {"key":"Page_WeeWX-X", "tag":"WeeWX-X", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"http://localhost/weewx/ XCurrent Conditions"})

dotest (3, "Local, page not found - ERROR",
        {"key":"Page_Bogus", "tag":"Bogus", "host":"local", "user_host_port":"local", "critical":False, "check_interval":1, "rest_of_line":"http://localhost/bogus/ whatever"})

dotest (4, "Remote, page found - OK",
        {"key":"Page_xBrowserSync", "tag":"xBrowserSync", "host":"testhost", "user_host_port":"me@testhost", "critical":True, "check_interval":1, "rest_of_line":"https://www.xbrowsersync.org/ Browser syncing as it should be: secure, anonymous and free!"})

dotest (5, "No such host - WARNING",
        {"key":"Page_Unknown", "tag":"Unknown", "host":"nosuchhost", "user_host_port":"me@nosuchhost", "critical":True, "check_interval":1, "rest_of_line":"http://localhost/weewx/ Current Conditions"})

dotest (6, "Known host, unavailable - WARNING",
        {"key":"Page_Unavailable", "tag":"Unavailable", "host":"testhostX", "user_host_port":"me@testhostX", "critical":True, "check_interval":1, "rest_of_line":"http://localhost/weewx/ Current Conditions"})
