#!/usr/bin/env python3
"""LAN Monitor plugin - service_plugin_test
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.3 240805 - Updated to lanmonitor V3.3
# 3.1 230320 - Added ssh access warning cases
# 3.0 230301 - Packaged
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS
try:
    from service_plugin import monitor
except:
    from lanmonitor.service_plugin import monitor

set_toolname('tool')
globvars.config = config_item()
globvars.config.cfg['nTries']           = 1
globvars.config.cfg['RetryInterval']    = '0s'
globvars.config.cfg['SSH_timeout']      = '4s'
setuplogging(ConsoleLogFormat="{module:>35}.{funcName:20} - {levelname:>8}:  {message}")
logging.getLogger().setLevel(logging.DEBUG)

def dotest (tnum, desc, test):
    print(f"\nTest {tnum} - {desc} {'-'*50}")
    inst = monitor()
    setup_rslt = inst.setup(test)
    logging.debug (f"{test['key']} - setup() returned:  {setup_rslt}")
    if setup_rslt == RTN_PASS:
        logging.debug (f"{test['key']} - eval_status() returned:  {inst.eval_status()}")

dotest (1, "Service local - OK",
        {'key':'Service_local', 'tag':'local', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'   sshd'})

dotest (2, "Service remote - OK",
        {'key':'Service_remote', 'tag':'remote', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'sshd   '})

dotest (3, "Service local fail - CRITICAL",
        {'key':'Service_fail', 'tag':'fail', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'xx'})

dotest (4, "No such host - setup WARNING",
        {'key':'Service_Unknown', 'tag':'Unknown', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'xx'})

dotest (5, "Known host, unavailable - setup WARNING",
        {'key':'Service_Unavailable', 'tag':'Unavailable', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'xx'})
