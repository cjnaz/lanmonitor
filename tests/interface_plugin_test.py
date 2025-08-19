#!/usr/bin/env python3
"""Demo/test for interface_plugin_test

Produce / compare to golden results:
    ./interface_plugin_test.py | diff interface_plugin_test.golden -
        Expected differences:
            None
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 3.5 250811 - Updated to lanmonitor V3.5
# 3.3 240805 - Updated to lanmonitor V3.3
# 3.1 230320 - Added ssh access warning cases
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging, set_logging_level
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, host_connections
try:
    from interface_plugin import monitor                # Use version in cwd
except:
    from lanmonitor.interface_plugin import monitor     # Use version in the package

set_toolname('tool')

cfg = """
[DEFAULT]
Connection_timeout =            4s
Connection_nTries =             1
Connection_retry_interval =     0s

Command_nTries =                1
Command_retry_interval =        0s
Command_max_consecutive_timeouts =  2

[local]
hostname =                      localhost
username =                      me
port =                          22
"""
globvars.config = config_item()
globvars.config.read_string(cfg)

setuplogging(ConsoleLogFormat="{module:>35}.{funcName:20} - {levelname:>8}:  {message}")
set_logging_level(logging.DEBUG)


def dotest (tnum, desc, test):
    print(f"\nTest {tnum} - {desc} {'-'*50}")
    inst = monitor()
    setup_rslt = inst.setup(test)
    logging.debug (f"{test['key']} - setup() returned:  {setup_rslt}")
    if setup_rslt == RTN_PASS:
        logging.debug (f"{test['key']} - eval_status() returned:  {inst.eval_status()}")

dotest (1, 'Loopback Interface local - OK',
        {'key':'Interface_local_lo', 'tag':'local_lo', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'lo'})

dotest (2, "Loopback Interface remote - OK",
        {'key':'Interface_remote_lo', 'tag':'remote_lo', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'lo'})

# Test relevant for dd-wrt
# dotest (3, "dd-wrt router wireless interface - OK",
#         {'key':'Interface_router_wl0.1', 'tag':'router_wl0.1', 'host':'192.168.1.1', 'user_host_port':'root@192.168.1.1', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'wl0.1'})

dotest (4, "Unknown local interface - CRITICAL",
        {'key':'Interface_bad_intf', 'tag':'bad_intf', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'bad'})

dotest (5, "Missing interface - Setup error",
        {'key':'Interface_no_interface', 'tag':'local', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'  '})

dotest (6, "No such host - CRITICAL",
        {'key':'Interface_Unknown_Host', 'tag':'Unknown_Host', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'lo'})

dotest (7, "Known host, unavailable - WARNING",
        {'key':'Interface_Unavailable_Host', 'tag':'Unavailable_Host', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'lo'})


host_connections.close('all')
