#!/usr/bin/env python3
"""LAN Monitor plugin - apt_upgrade_history_plugin_test
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
    from apt_upgrade_history_plugin import monitor
except:
    from lanmonitor.apt_upgrade_history_plugin import monitor

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

dotest ({"key":"AptUpgrade_Pass", "tag":"Pass", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"500w apt full-upgrade"})

dotest ({"key":"AptUpgrade_TooOld", "tag":"TooOld", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"10h apt full-upgrade"})

dotest ({"key":"AptUpgrade_NoUpgrades", "tag":"NoUpgrades", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"10h apt full-upgradeS"})

dotest ({"key":"AptUpgrade_CantAccess", "tag":"CantAccess", "host":"nosuchhost", "user_host_port":"pi@nosuchhost", "critical":True, "check_interval":1, "rest_of_line":"10h apt full-upgrade"})

dotest ({"key":"AptUpgrade_baddef", "tag":"badline", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10m"})

dotest ({"key":"AptUpgrade_badtime", "tag":"badtime", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10y apt full-upgrade"})
