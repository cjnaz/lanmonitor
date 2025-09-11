#!/usr/bin/env python3
"""Demo/test for freespace_plugin_test

Produce / compare to golden results:
    ./freespace_plugin_test.py | diff freespace_plugin_test.golden -
        Expected differences:
            Passing tests free space values will vary
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0
# 3.3 240805 - Updated to lanmonitor V3.3.
# 3.1 230320 - Added ssh access warning cases
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging, set_logging_level
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, host_connections
try:
    from freespace_plugin import monitor                # Use version in cwd
except:
    from lanmonitor.freespace_plugin import monitor     # Use version in the package

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

dotest (1, "Freespace as a percentage - OK",
        {'key':'Free_Per_pass', 'tag':'Per_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'30% /home   '})

dotest (2, "Freespace as a percentage - CRITICAL",
        {'key':'Free_Per_fail', 'tag':'Per_fail', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'100% /home'})

dotest (3, "Freespace as a absolute min remote - OK",
        {'key':'Free_Abs_pass', 'tag':'Abs_pass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1000 /mnt/RAMDRIVE   '})

dotest (4, "Freespace as a absolute min remote - CRITICAL",
        {'key':'Free_Abs_fail', 'tag':'Abs_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'300000 /mnt/RAMDRIVE'})

dotest (5, "Known host, No such path - CRITICAL",
        {'key':'Free_nosuchpath', 'tag':'nosuchpath', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10% /mnt/nosuchpath'})

dotest (6, "Space in path - OK",
        {'key':'Free_pathWithSpaces', 'tag':'pathWithSpaces', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10% /mnt/share/tmp/Ripped videos'})

dotest (7, "Bad limit value - setup ERROR",
        {'key':'Free_badlimit', 'tag':'badlimit', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'10x% /home'})

dotest (8, "No such host - CRITICAL",
        {'key':'Free_Unknown', 'tag':'Unknown', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'30% /home'})

dotest (9, "Known host, unavailable - WARNING",
        {'key':'Free_Unavailable', 'tag':'Unavailable', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'30% /home'})


host_connections.close('all')