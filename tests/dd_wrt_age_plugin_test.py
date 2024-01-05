#!/usr/bin/env python3
"""LAN Monitor plugin - dd-wrt_age_plugin_test
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
    from dd_wrt_age_plugin import monitor
except:
    from lanmonitor.dd_wrt_age_plugin import monitor

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

dotest (1, "Age passing - OK",
        {"key":"DD-wrt_age_Pass", "tag":"Pass", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"90d 192.168.1.1"})

dotest (2, "Age failing - CRITICAL",
        {"key":"DD-wrt_age_Fail", "tag":"Fail", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"0d 192.168.1.1"})

dotest (3, "Host not responding - WARNING",
        {"key":"DD-wrt_age_noreply", "tag":"Fail", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"0d 192.168.1.99"})

dotest (4, "Bad age limit - setup ERROR",
        {"key":"DD-wrt_age_badline", "tag":"Fail", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"0y 192.168.1.99"})

dotest (5, "No such host - WARNING",
        {"key":"DD-wrt_age_Unknown", "tag":"Unknown", "host":"nosuchhost", "user_host_port":"me@nosuchhost", "critical":True, "check_interval":1, "rest_of_line":"90d 192.168.1.1"})

dotest (6, "Known host, unavailable - WARNING",
        {"key":"DD-wrt_age_Unavailable", "tag":"Unavailable", "host":"testhostX", "user_host_port":"me@testhostX", "critical":True, "check_interval":1, "rest_of_line":"90d 192.168.1.1"})

