#!/usr/bin/env python3
"""LAN Monitor plugin - freespace_plugin_test
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
    from freespace_plugin import monitor
except:
    from lanmonitor.freespace_plugin import monitor

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

dotest ({"key":"Free_Per_pass", "tag":"Per_pass", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"30% /home"})

dotest ({"key":"Free_Per_fail", "tag":"Per_fail", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"100% /home"})

dotest ({"key":"Free_Abs_pass", "tag":"Abs_pass", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"18000 /mnt/RAMDRIVE"})

dotest ({"key":"Free_Abs_fail", "tag":"Abs_fail", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"30000 /mnt/RAMDRIVE"})

dotest ({"key":"Free_nosuchpath", "tag":"nosuchpath", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10% /mnt/nosuchpath"})

dotest ({"key":"Free_pathWithSpaces", "tag":"pathWithSpaces", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10% /mnt/share/tmp/Ripped videos"})

dotest ({"key":"Free_badlimit", "tag":"badlimit", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"10x% /home"})

dotest ({"key":"Free_Unknown", "tag":"Unknown", "host":"nosuchhost", "user_host_port":"pi@nosuchhost", "critical":True, "check_interval":1, "rest_of_line":"30% /home"})

dotest ({"key":"Free_Unavailable", "tag":"Unavailable", "host":"shopcam", "user_host_port":"me@shopcam", "critical":True, "check_interval":1, "rest_of_line":"30% /home"})
