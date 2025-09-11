#!/usr/bin/env python3
"""Demo/test for freemem_plugin_test

Produce / compare to golden results:
    ./freemem_plugin_test.py | diff freemem_plugin_test.golden -
        Expected differences:
            free mem values will vary
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0
# 3.3 240805 - New
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging, set_logging_level
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, host_connections
try:
    from freemem_plugin import monitor                  # Use version in cwd
except:
    from lanmonitor.freemem_plugin import monitor       # Use version in the package

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

dotest (1, "Freemem as a percentage - OK",
        {'key':'Freemem_Per_pass', 'tag':'Per_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'30%   '})

dotest (2, "Freemem as a absolute - OK",
        {'key':'Freemem_Aps_pass', 'tag':'Abs_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'30ki  '})

dotest (3, "Freemem & swap 1 - OK",
        {'key':'Freemem_Both1_pass', 'tag':'Both1_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'  30% 20Mi  '})

dotest (4, "Freemem & swap 2 - OK",
        {'key':'Freemem_Both2_pass', 'tag':'Both2_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'30mi 10%'})

dotest (5, "Invalid swap limit - Setup ERROR",
        {'key':'Freemem_swap_inv_setup_error', 'tag':'swap_inv_setup_error', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'30ti 10X'})

dotest (6, "Invalid both limits - Setup ERROR",
        {'key':'Freemem_both_inv_setup_error', 'tag':'both_inv_setup_error', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'30GiX X10ti'})

dotest (7, "Too many params - Setup ERROR",
        {'key':'Freemem_too_many_setup_error', 'tag':'too_many_setup_error', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'30Gi 10 ti'}) # 20mi'})

dotest (8, "No params - Setup ERROR",
        {'key':'Freemem_No_params_setup_error', 'tag':'No_params_setup_error', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':''})

dotest (9, "Non matching abs suffixes - Setup ERROR",
        {'key':'Freemem_non_matching_suffixes_setup_error', 'tag':'non_matching_suffixes_setup_error', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'5Gi 10Mi'})

dotest (10, "Remote %/% - OK",
        {'key':'Freemem_Remote_per_per_pass', 'tag':'Remote_per_per_pass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'  10% 10%  '})

dotest (11, "Remote Both Abs - OK",
        {'key':'Freemem_Remote_Abs_pass', 'tag':'Remote_Abs_pass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'5mi 5mi'})

dotest (12, "Remote Both Abs - CRITICAL",
        {'key':'Freemem_Remote_Mem_Abs_fail', 'tag':'Remote_Mem_Abs_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'50gi 5Gi'})

dotest (13, "Remote Div0 - CRITICAL",
        {'key':'Freemem_Remote_Gi_Abs_Per_fail', 'tag':'Remote_Gi_Abs_Per_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'0gi 5%'})

dotest (14, "No such host - FAIL",
        {'key':'Freemem_Unknown', 'tag':'Unknown', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'  10% 10%  '})

dotest (15, "Known host, unavailable - WARNING",
        {'key':'Freemem_Unavailable', 'tag':'Unavailable', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'  10% 10%  '})


host_connections.close('all')