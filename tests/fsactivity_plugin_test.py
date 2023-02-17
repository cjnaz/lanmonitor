#!/usr/bin/env python3
"""LAN Monitor plugin - fsactivity_plugin_test
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

dotest ({"key":"Activity_Shop2_backups", "tag":"Shop2_backups", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"8d /mnt/share/backups/Shop2/"})

dotest ({"key":"Activity_rpi3_ramdrive", "tag":"rpi3_ramdrive", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"5m		/mnt/RAMDRIVE"})

dotest ({"key":"Activity_Shop2_backups_fail", "tag":"Shop2_backups_fail", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"1h /mnt/share/backups/Shop2/"})

dotest ({"key":"Activity_empty_dir", "tag":"empty_dir", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"1h junk"}) # empty dir in cwd

dotest ({"key":"Activity_badpath", "tag":"badpath", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"1h /mnt/share/xxx"})

dotest ({"key":"Activity_badhost", "tag":"badhost", "host":"rpi3.lan", "user_host_port":"pi@rpi3.lan", "critical":True, "check_interval":1, "rest_of_line":"1h /mnt/share/xxx"})
