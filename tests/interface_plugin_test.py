#!/usr/bin/env python3
"""LAN Monitor plugin - interface_plugin_test
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
    from interface_plugin import monitor
except:
    from lanmonitor.interface_plugin import monitor

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

dotest (1, "Loopback Interface local - OK",
        {"key":"Interface_local_lo", "tag":"local_lo", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"lo"})

dotest (2, "Loopback Interface remote - OK",
        {"key":"Interface_remote_lo", "tag":"remote_lo", "host":"testhost", "user_host_port":"me@testhost", "critical":True, "check_interval":1, "rest_of_line":"lo"})

# Test relevant for dd-wrt
# dotest (3, "dd-wrt router wireless interface - OK",
#         {"key":"Interface_router_wl0.1", "tag":"router_wl0.1", "host":"192.168.1.1", "user_host_port":"root@192.168.1.1", "critical":True, "check_interval":1, "rest_of_line":"wl0.1"})

dotest (4, "Unknown local interface - CRITICAL",
        {"key":"Interface_bad_intf", "tag":"bad_intf", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"bad"})

dotest (5, "Missing interface - CRITICAL",
        {"key":"Interface_no_interface", "tag":"local", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":""})

dotest (6, "No such host - WARNING",
        {"key":"Interface_Unknown", "tag":"Unknown", "host":"nosuchhost", "user_host_port":"me@nosuchhost", "critical":True, "check_interval":1, "rest_of_line":"lo"})

dotest (7, "Known host, unavailable - WARNING",
        {"key":"Interface_Unavailable", "tag":"Unavailable", "host":"testhostX", "user_host_port":"me@testhostX", "critical":True, "check_interval":1, "rest_of_line":"lo"})
