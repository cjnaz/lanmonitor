#!/usr/bin/env python3
"""LAN Monitor plugin - pinghost_plugin_test
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
    from pinghost_plugin import monitor
except:
    from lanmonitor.pinghost_plugin import monitor

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

dotest ({"key":"Host_local_to_RPi3", "tag":"local_to_RPi3", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"rpi3"})

dotest ({"key":"Host_local_to_IP", "tag":"local_to_IP", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"192.168.1.1"})

dotest ({"key":"Host_RPi3_to_Shop2", "tag":"RPi3_to_Shop2", "host":"rpi3", "user_host_port":"pi@rpi3:22", "critical":True, "check_interval":1, "rest_of_line":"shop2"})

dotest ({"key":"Host_local_to_INV", "tag":"local_to_INV", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"invalid@hostname"})

dotest ({"key":"Host_local_to_Unknown", "tag":"local_to_Unknown", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"XX.lan"})

dotest ({"key":"Host_Unknown_to_Known", "tag":"Unknown_to_Known", "host":"unknown", "user_host_port":"me@unknown", "critical":False, "check_interval":1, "rest_of_line":"shop2"})
