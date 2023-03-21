#!/usr/bin/env python3
"""LAN Monitor plugin - interface_plugin_test
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
    from interface_plugin import monitor
except:
    from lanmonitor.interface_plugin import monitor

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

dotest ({"key":"Interface_local_lo", "tag":"local_lo", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"lo"})

dotest ({"key":"Interface_remote_lo", "tag":"remote_lo", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"lo"})

# Test relevant for dd-wrt
# dotest ({"key":"Interface_router_wl0.1", "tag":"router_wl0.1", "host":"192.168.1.1", "user_host_port":"root@192.168.1.1", "critical":True, "check_interval":1, "rest_of_line":"wl0.1"})

dotest ({"key":"Interface_bad_intf", "tag":"bad_intf", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"bad"})

dotest ({"key":"Interface_no_interface", "tag":"local", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":""})

dotest ({"key":"Interface_Unknown", "tag":"Unknown", "host":"nosuchhost", "user_host_port":"pi@nosuchhost", "critical":True, "check_interval":1, "rest_of_line":"lo"})

dotest ({"key":"Interface_Unavailable", "tag":"Unavailable", "host":"shopcam", "user_host_port":"me@shopcam", "critical":True, "check_interval":1, "rest_of_line":"lo"})
