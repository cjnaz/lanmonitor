#!/usr/bin/env python3
"""LAN Monitor plugin - yum_update_history_plugin_test
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2023
#
# 3.1 230320 - Added ssh access warning cases
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.cjnfuncs import set_toolname, setuplogging, logging, cfg
from lanmonitor.lanmonfuncs import RTN_PASS
try:
    from yum_update_history_plugin import monitor
except:
    from lanmonitor.yum_update_history_plugin import monitor

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

dotest ({"key":"YumUpdate_Pass", "tag":"Pass", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"90d update"})

dotest ({"key":"YumUpdate_TooOld", "tag":"TooOld", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10m update"})

dotest ({"key":"YumUpdate_baddef", "tag":"badline", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10m"})

dotest ({"key":"YumUpdate_badtime", "tag":"badtime", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10y update"})

dotest ({"key":"YumUpdate_remote", "tag":"remote", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"10m update"})

dotest ({"key":"YumUpdate_noupdates", "tag":"noupdates", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10m update xx"})

dotest ({"key":"YumUpdate_Unknown", "tag":"Unknown", "host":"nosuchhost", "user_host_port":"pi@nosuchhost", "critical":True, "check_interval":1, "rest_of_line":"90d update"})

dotest ({"key":"YumUpdate_Unavailable", "tag":"Unavailable", "host":"shopcam", "user_host_port":"me@shopcam", "critical":True, "check_interval":1, "rest_of_line":"90d update"})
