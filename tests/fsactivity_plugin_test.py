#!/usr/bin/env python3
"""LAN Monitor plugin - fsactivity_plugin_test
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

import subprocess
import time
from cjnfuncs.core import set_toolname, setuplogging, logging
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS
try:
    from fsactivity_plugin import monitor
except:
    from lanmonitor.fsactivity_plugin import monitor

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

dotest (1, "Local activity pass - OK",
        {'key':'Activity_local_dir_pass', 'tag':'local_dir_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'8d /etc/   '})

dotest (2, "Local activity fail - CRITICAL",
        {'key':'Activity_local_dir_fail', 'tag':'local_dir_fail', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /etc/'})

subprocess.run(['ssh', 'me@testhost2', 'touch', '/mnt/RAMDRIVE/touchfile'])
dotest (3, "Remote directory activity pass - OK",
        {'key':'Activity_remote_dir_pass', 'tag':'remote_dir_pass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'5m /mnt/RAMDRIVE/   '})

dotest (4, "Remote file activity pass - OK",
        {'key':'Activity_remote_file_pass', 'tag':'remote_file_pass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'5m /mnt/RAMDRIVE/touchfile'})

time.sleep(2)
dotest (5, "Remote activity fail - CRITICAL",
        {'key':'Activity_remote_dir_fail', 'tag':'remote_dir_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /mnt/RAMDRIVE/'})

dotest (6, "Local empty dir - CRITICAL",
        {'key':'Activity_empty_dir', 'tag':'empty_dir', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1h junkdir/'}) # empty dir in cwd

dotest (7, "Local no such file - CRITICAL",
        {'key':'Activity_no_such_file', 'tag':'no_such_file', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1h junkdir/xxx'})

dotest (8, "No such host - WARNING",
        {'key':'Activity_Unknown_host', 'tag':'Unknown_host', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1h /mnt/RAMDRIVE/xxx'})

dotest (9, "Known host, unavailable - WARNING",
        {'key':'Activity_Unavailable_host', 'tag':'Unavailable_host', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'1h /mnt/RAMDRIVE/xxx'})
