#!/usr/bin/env python3
"""LAN Monitor plugin - selinux_plugin_test
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
    from selinux_plugin import monitor
except:
    from lanmonitor.selinux_plugin import monitor

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

dotest ({"key":"SELinux_local", "tag":"local", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"enforcing"})

dotest ({"key":"SELinux_RPiX", "tag":"RPiX", "host":"RPiX", "user_host_port":"pi@rpiX", "critical":True, "check_interval":1, "rest_of_line":"enforcing"})

dotest ({"key":"SELinux_RPi3", "tag":"RPi3", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":False, "check_interval":1, "rest_of_line":"enforcing"})

dotest ({"key":"SELinux_badmode", "tag":"Shop2", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"enforcingX"})

dotest ({"key":"SELinux_RPi3_CRIT", "tag":"RPi3_CRIT", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"enforcing"})