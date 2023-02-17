#!/usr/bin/env python3
"""LAN Monitor plugin - dd-wrt_age_plugin_test
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2023
#
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.cjnfuncs import set_toolname, setuplogging, logging, cfg
from lanmonitor.lanmonfuncs import RTN_PASS
try:
    from dd_wrt_age_plugin import monitor
except:
    from lanmonitor.dd_wrt_age_plugin import monitor

tool = set_toolname("tool")
cfg["nRetries"]         = 1
cfg["RetryInterval"]    = "0s"
cfg["ConsoleLogFormat"] = "{module:>35}.{funcName:20} - {levelname:>8}:  {message}"
setuplogging()
logging.getLogger().setLevel(logging.DEBUG)

test_num = 0
def dotest (test):
    global test_num
    test_num += 1
    print(f"\nTest {test_num} {'-'*50}")
    inst = monitor()
    setup_rslt = inst.setup(test)
    logging.debug (f"{test['key']} - setup() returned:  {setup_rslt}")
    if setup_rslt == RTN_PASS:
        logging.debug (f"{test['key']} - eval_status() returned:  {inst.eval_status()}")

dotest ({"key":"DD-wrt_age_Pass", "tag":"Pass", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"90d 192.168.1.1"})

dotest ({"key":"DD-wrt_age_Fail", "tag":"Fail", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"0d 192.168.1.1"})

dotest ({"key":"DD-wrt_age_noreply", "tag":"Fail", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"0d 192.168.1.99"})

dotest ({"key":"DD-wrt_age_badline", "tag":"Fail", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"0y 192.168.1.99"})
