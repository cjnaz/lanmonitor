#!/usr/bin/env python3
"""Demo/test for pinghost_plugin_test

Produce / compare to golden results:
    ./pinghost_plugin_test.py | diff pinghost_plugin_test.golden -
        Expected differences:
            test 1/2/3 ping values will vary
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

__version__ =   '3.5'

import argparse
from cjnfuncs.core import set_toolname, setuplogging, logging, set_logging_level
from cjnfuncs.configman import config_item
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, host_connections
try:
    from pinghost_plugin import monitor                 # Use version in cwd
except:
    from lanmonitor.pinghost_plugin import monitor      # Use version in the package

parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-t', '--test', default='0',
                    help="Test number to run (default 0).  0 runs all tests")
args = parser.parse_args()

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

# --------------------------------------------------------------------

def dotest (tnum, desc, test):
    print(f"\nTest {tnum} - {desc} {'-'*50}")
    inst = monitor()
    setup_rslt = inst.setup(test)
    logging.debug (f"{test['key']} - setup() returned:  {setup_rslt}")
    if setup_rslt == RTN_PASS:
        logging.debug (f"{test['key']} - eval_status() returned:  {inst.eval_status()}")

#===============================================================================================

tnum = '1'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Local to testhost2 by name - OK",
                {'key':'Host_local_to_testhost2', 'tag':'local_to_testhost2', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':1, 'check_interval':1, 'rest_of_line':'testhost2   '})

tnum = '2'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Local to testhost2 by IP address - OK",
                {'key':'Host_local_to_IP', 'tag':'local_to_IP', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':1, 'check_interval':1, 'rest_of_line':'   192.168.15.42'})

tnum = '3'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Remote to other host (testhost) - OK",
                {'key':'Host_testhost2_to_testhost', 'tag':'testhost2_to_testhost', 'host':'testhost2', 'user_host_port':'me@testhost2:22', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'testhost'})

tnum = '4'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Local to invalid hostname - setup ERROR",
                {'key':'Host_local_to_INV', 'tag':'local_to_INV', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':1, 'check_interval':1, 'rest_of_line':'invalid@hostname'})

tnum = '5'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Local to unknown host - CRITICAL",
                {'key':'Host_local_to_Unknown', 'tag':'local_to_Unknown', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':1, 'check_interval':1, 'rest_of_line':'XX.lan'})

tnum = '6a'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Local to known unavailable host with long cmd_timeout - FAIL",
                {'key':'Host_local_to_Unavailable', 'tag':'local_to_Unavailable', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'testhostX'})

tnum = '6b'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Local to known unavailable host with short cmd_timeout - FAIL",
                {'key':'Host_local_to_Unavailable', 'tag':'local_to_Unavailable', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':1, 'check_interval':1, 'rest_of_line':'testhostX'})

tnum = '7a'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Remote to known unavailable remote with long cmd_timeout - FAIL",
                {'key':'Host_testhost2_to_Unavailable', 'tag':'testhost2_to_Unavailable', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'testhostX'})

tnum = '7b'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Remote to known unavailable remote with short cmd_timeout - FAIL",
                {'key':'Host_testhost2_to_Unavailable', 'tag':'testhost2_to_Unavailable', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':1, 'check_interval':1, 'rest_of_line':'testhostX'})

tnum = '8'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Attempt to run on unknown remote - CRITICAL",
                {'key':'Host_Unknown_remote', 'tag':'Unknown', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'testhost'})

tnum = '9'
if args.test == '0'  or  args.test == tnum:
        dotest (tnum, "Attempt to run on known unavailable remote - WARNING",
                {'key':'Host_Unavailable_remote', 'tag':'Unavailable_to_Known', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'testhost'})

tnum = '50'
if args.test == tnum:
        dotest (tnum, "DEVELOPMENT",
                {'key':'Host_DEVELOPMENT', 'tag':'DEVELOPMENT', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':1, 'check_interval':1, 'rest_of_line':'testhost2'})


host_connections.close('all')