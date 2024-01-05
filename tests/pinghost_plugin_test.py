#!/usr/bin/env python3
"""LAN Monitor plugin - pinghost_plugin_test
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.1 230320 - Added ssh access warning cases
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS
try:
    from pinghost_plugin import monitor
except:
    from lanmonitor.pinghost_plugin import monitor

set_toolname("tool")
globvars.config = config_item()
globvars.config.cfg["nRetries"]         = 1
globvars.config.cfg["RetryInterval"]    = "0s"
setuplogging(ConsoleLogFormat="{module:>35}.{funcName:20} - {levelname:>8}:  {message}")
logging.getLogger().setLevel(logging.DEBUG)

def dotest (tnum, desc, test):
    print(f"\nTest {tnum} - {desc} {'-'*50}")
    inst = monitor()
    setup_rslt = inst.setup(test)
    logging.debug (f"{test['key']} - setup() returned:  {setup_rslt}")
    if setup_rslt == RTN_PASS:
        logging.debug (f"{test['key']} - eval_status() returned:  {inst.eval_status()}")

dotest (1, "Local to testhost by name - OK",
        {"key":"Host_local_to_testhost", "tag":"local_to_testhost", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"testhost"})

dotest (2, "Local to IP address - OK",
        {"key":"Host_local_to_IP", "tag":"local_to_IP", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"192.168.1.1"})

dotest (3, "testhost to other host - OK",
        {"key":"Host_testhost_to_Shop2", "tag":"testhost_to_Shop2", "host":"testhost", "user_host_port":"me@testhost:22", "critical":True, "check_interval":1, "rest_of_line":"shop2"})

dotest (4, "Local to invalid hostname - setup ERROR",
        {"key":"Host_local_to_INV", "tag":"local_to_INV", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"invalid@hostname"})

dotest (5, "Local to unknown - CRITICAL",
        {"key":"Host_local_to_Unknown", "tag":"local_to_Unknown", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"XX.lan"})

dotest (6, "Local to known but unavailable - ERROR",
        {"key":"Host_local_to_Unavailable", "tag":"local_to_Unavailable", "host":"local", "user_host_port":"local", "critical":False, "check_interval":1, "rest_of_line":"testhostX"})

dotest (7, "Attempt to run on unknown remote - WARNING",
        {"key":"Host_Unknown_remote", "tag":"Unknown", "host":"nosuchhost", "user_host_port":"me@nosuchhost", "critical":True, "check_interval":1, "rest_of_line":"testhost"})

dotest (8, "Attempt to run on known unavailable remote - WARNING",
        {"key":"Host_Unavailable_remote", "tag":"Unavailable_to_Known", "host":"testhostX", "user_host_port":"me@testhostX", "critical":False, "check_interval":1, "rest_of_line":"testhost"})
