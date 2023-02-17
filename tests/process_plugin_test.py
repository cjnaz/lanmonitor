#!/usr/bin/env python3
"""LAN Monitor plugin - process_plugin_test
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
    from process_plugin import monitor
except:
    from lanmonitor.process_plugin import monitor

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

dotest ({"key":"Process_x11vnc", "tag":"x11vnc", "host":"local", "user_host_port":"local", "critical":False, "check_interval":1, "rest_of_line":"/usr/bin/x11vnc"})

dotest ({"key":"Process_RPi3_sshd", "tag":"Process_RPi3_sshd", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":False, "check_interval":1, "rest_of_line":"/usr/sbin/sshd"})

dotest ({"key":"Process_XXX", "tag":"XXX", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"/usr/bin/XXX"})
