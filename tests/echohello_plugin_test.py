#!/usr/bin/env python3
"""Demo/test for echohello_plugin

Produce / compare to golden results:
    ./echohello_plugin_test.py | diff echohello_plugin_test.golden -
        Expected differences:

           Test 5:
                On Debian (Raspberry Pi Bullseye) returns "TimeoutError" (this is the golden file result)
                On RHEL 9 returns "OSError: [Errno 113] Connect call failed"
                Both result in "setup() returned:  1"
"""

#==========================================================
#
#  Chris Nelson, Copyright 2026
#
# 4.1 260117 - New
#
#==========================================================

from cjnfuncs.core import set_toolname, setuplogging, logging, set_logging_level
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, host_connections
try:
    from echohello_plugin import monitor                # Use version in cwd
except:
    from lanmonitor.service_plugin import monitor       # Use version in the package

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
hostname =                      localhost  # testhost
username =                      me
# port =                          22
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

dotest (1, "Echo local to testhost (self) - OK",
        {'key':'EchoHello_local_to_self', 'tag':'local_to_self', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'me@testhost'})

dotest ('1a', "Echo local to localhost (self) - OK",
        {'key':'EchoHello_local_to_localhost', 'tag':'local_to_localhost', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'me@localhost'})

dotest (2, "Echo local to testhost2 - OK",
        {'key':'EchoHello_local_to_testhost2', 'tag':'local_to_testhost2', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'me@testhost2'})

dotest ('2a', "Echo testhost (self) to testhost2 - OK",
        {'key':'EchoHello_testhost_to_testhost2', 'tag':'testhost_to_testhost2', 'host':'testhost', 'user_host_port':'me@testhost', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'me@testhost2'})

dotest (3, "Echo from testhost2 to 'local' (testhost) - OK",
        {'key':'EchoHello_testhost2_to_local', 'tag':'testhost2_to_local', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'local'})

dotest ('3a', "Echo from testhost2 to me@testhost - OK",
        {'key':'EchoHello_testhost2_to_me@testhost', 'tag':'testhost2_to_me@testhost', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'me@testhost'})


dotest (4, "Run on local, attempt to connect to known unavailable - eval_status timeout error",
        {'key':'EchoHello_local_to_Unavailable', 'tag':'local_to_Unavailable', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'me@testhostX'})

dotest (5, "Attempt to run on known unavailable host - eval_status timeout error",
        {'key':'EchoHello_Unavailable_to_local', 'tag':'Unavailable_to_local', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'local'})


host_connections.close('all')
