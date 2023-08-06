#!/usr/bin/env python3
"""LAN Monitor plugin - fsactivity_plugin_test
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
    from fsactivity_plugin import monitor
except:
    from lanmonitor.fsactivity_plugin import monitor

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

dotest ({"key":"Activity_local_dir_pass", "tag":"local_dir_pass", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"8d /etc/"})

dotest ({"key":"Activity_remote_pass", "tag":"remote_pass", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"5m /mnt/RAMDRIVE/"})

dotest ({"key":"Activity_local_dir_fail", "tag":"local_dir_fail", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"1s /etc/"})

dotest ({"key":"Activity_empty_dir", "tag":"empty_dir", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"1h junk/"}) # empty dir in cwd

dotest ({"key":"Activity_no_such_file", "tag":"no_such_file", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"1h junk/xxx"})

dotest ({"key":"Activity_Unknown_host", "tag":"Unknown_host", "host":"nosuchhost", "user_host_port":"pi@nosuchhost", "critical":True, "check_interval":1, "rest_of_line":"1h /mnt/share/xxx"})

dotest ({"key":"Activity_Unavailable_host", "tag":"Unavailable_host", "host":"shopcam", "user_host_port":"me@shopcam", "critical":True, "check_interval":1, "rest_of_line":"1h /mnt/share/xxx"})
