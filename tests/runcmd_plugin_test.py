#!/usr/bin/env python3
"""Demo/test for runcmd_plugin

Produce / compare to golden results:
    ./runcmd_plugin_test.py | diff runcmd_plugin_test.golden -

    Expected differences:
        Tests 1c, 3c:  uptime will vary
"""

#==========================================================
#
#  Chris Nelson, Copyright 2026
#
# 4.1 260830 - New
#
#==========================================================

__version__ =   '4.1'
TOOLNAME =      'demo_runcmd_plugin'

import argparse
import re
import time
import subprocess
from pathlib import Path

from cjnfuncs.core              import set_toolname, setuplogging, logging, set_logging_level
from cjnfuncs.configman         import config_item

import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, host_connections

try:
    from runcmd_plugin import monitor               # Use version in cwd
except:
    from lanmonitor.runcmd_plugin import monitor    # Use version in the package


cfg = """
[DEFAULT]
Connection_timeout =            4s
Connection_nTries =             1
Connection_retry_interval =     0s

Command_nTries =                1
Command_retry_interval =        0s
Command_max_consecutive_timeouts =  2

[localhost]
hostname = localhost
username = me

[testhost2]
hostname = testhost2
username = me
"""
set_toolname(TOOLNAME)
globvars.config = config_item()
globvars.config.read_string(cfg)

setuplogging(ConsoleLogFormat="{module:>35}.{funcName:20} - {levelname:>8}:  {message}")
set_logging_level(logging.DEBUG)


parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-t', '--test', default='0',
                    help="Test number to run (default 0).  0 runs all tests")
args = parser.parse_args()


# --------------------------------------------------------------------

def dotest (desc, expect, test_key):
    global tnum
    logging.warning (f"\n\n==============================================================================================\n" +
                     f"Test {tnum} - {desc}\n" +
                     f"  GIVEN:      {test_key}\n"
                     f"  EXPECT:     {expect}")

    inst = monitor()
    setup_rslt = inst.setup(test_key)
    logging.debug (f"setup() returned:  {setup_rslt}")
    if setup_rslt == RTN_PASS:
        logging.warning (f"\n  RETURNED:   {inst.eval_status()}")


tnum_parse = re.compile(r"([\d]+)([\w]*)")
def check_tnum(tnum_in, include0='0'):
    global tnum
    tnum = tnum_in
    if args.test == include0  or  args.test == tnum_in:  return True
    try:
        if int(args.test) == int(tnum_parse.match(tnum_in).group(1)):  return True
    except:  pass
    return False

#===============================================================================================

# Basic Pass checks run locally
if check_tnum('1a'):
    dotest ("Simple echo Hello - Pass",
            "{'rslt': 0, 'notif_key': 'Command_Simple', 'message': 'Command_Simple  OK - local - Hello'}",
            {'key':'Command_Simple', 'tag':'Simple', 'host':'local', 'user_host_port':'local',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello'})

if check_tnum('1b'):
    dotest ("echo Hello check as expected_text, log_stdout=False - Pass",
            "{'rslt': 0, 'notif_key': 'Command_Hello_Check', 'message': 'Command_Hello_Check  OK - local'}",
            {'key':'Command_Hello_Check', 'tag':'Hello_Check', 'host':'local', 'user_host_port':'local',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello',
             'expected_text':'Hello', 'log_stdout':False})

xx = f"""My info is
hostname: $(hostname)
uptime: $(uptime)
"""
if check_tnum('1c'):
    dotest ("Complex echo with expected_test and check_line_text, - Pass",
            "{'rslt': 0, 'notif_key': 'Command_Complex_Check', 'message': 'Command_Complex_Check  OK - local - My info is\nhostname: testhost\nuptime:  09:35:05 up 2 days, 16:09,  1 user,  load average: 0.27, 0.24, 0.22'}",
            {'key':'Command_Complex_Check', 'tag':'Complex_Check', 'host':'local', 'user_host_port':'local',
             'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':f'echo "{xx}"',
             'expected_text':'test', 'check_line_text':'hostname'})

if check_tnum('1d'):
    dotest ("Simple echo Hello via localhost - Pass",
            "{'rslt': 0, 'notif_key': 'Command_Simple_localhost', 'message': 'Command_Simple_localhost  OK - localhost - Hello'}",
            {'key':'Command_Simple_localhost', 'tag':'Simple_localhost', 'host':'localhost', 'user_host_port':'localhost',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello'})


# Basic Fail checks run locally
if check_tnum('2a'):
    dotest ("expected_text not found - Fail",
            "{'rslt': 3, 'notif_key': 'Command_local_Hello_Check', 'message': '  CRITICAL: Command_local_Hello_Check - local - echo command failed'}",
            {'key':'Command_Check_fail', 'tag':'Check_fail', 'host':'local', 'user_host_port':'local',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello',
             'expected_text':'Hillo'})


# Basic Pass checks run remotely
if check_tnum('3a'):
    dotest ("Simple echo Hello - Pass",
            "{'rslt': 0, 'notif_key': 'Command_Simple', 'message': 'Command_Simple  OK - testhost2 - Hello'}",
            {'key':'Command_Simple', 'tag':'Simple', 'host':'testhost2', 'user_host_port':'testhost2',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello'})

if check_tnum('3b'):
    dotest ("echo Hello check as expected_text, log_stdout=False - Pass",
            "{'rslt': 0, 'notif_key': 'Command_Hello_Check', 'message': 'Command_Hello_Check  OK - testhost2'}",
            {'key':'Command_Hello_Check', 'tag':'Hello_Check', 'host':'testhost2', 'user_host_port':'testhost2',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello',
             'expected_text':'Hello', 'log_stdout':False})

xx = f"""My info is
hostname: $(hostname)
uptime: $(uptime)
"""
if check_tnum('3c'):
    dotest ("Complex echo with expected_test and check_line_text, - Pass",
            "{'rslt': 0, 'notif_key': 'Command_Complex_Check', 'message': 'Command_Complex_Check  OK - testhost2 - My info is\nhostname: testhost2\nuptime:  09:44:59 up 31 min,  0 users,  load average: 0.35, 0.26, 0.20'}",
            {'key':'Command_Complex_Check', 'tag':'Complex_Check', 'host':'testhost2', 'user_host_port':'testhost2',
             'critical':False, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':f'echo "{xx}"',
             'expected_text':'test', 'check_line_text':'hostname'})


# Basic Fail checks run remotely
if check_tnum('4a'):
    dotest ("expected_text not found - Fail",
            "{'rslt': 3, 'notif_key': 'Command_Check_fail', 'message': '  CRITICAL: Command_Check_fail - testhost2 - command <echo Hello> failed'}",
            {'key':'Command_Check_fail', 'tag':'Check_fail', 'host':'testhost2', 'user_host_port':'testhost2',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello',
             'expected_text':'Hillo'})


# Error checks
if check_tnum('13a'):
    dotest ("expected_text not str - Fail setup()",
            "Command_bad_expected_text - expected_text must be type str (if provided)... setup() returned:  2",
            {'key':'Command_bad_expected_text', 'tag':'bad_expected_text', 'host':'local', 'user_host_port':'local',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello',
             'expected_text':5, 'check_line_text':'my', 'not_text':'.te'})

if check_tnum('13b'):
    dotest ("Unknown hostname",
            "{'rslt': 3, 'notif_key': 'Command_Unknown_hostname', 'message': '  CRITICAL: Command_Unknown_hostname - nosuchhost - command <echo Hello> failed - gaierror: [Errno -2] Name or service not known'}",
            {'key':'Command_Unknown_hostname', 'tag':'Unknown_hostname', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello'})

if check_tnum('13c'):
    dotest ("Host unavailable",
            """{'rslt': 1, 'notif_key': 'Command_Host_unavailable', 'message': "  WARNING: Command_Host_unavailable - testhostX - COULD NOT CONNECT TO EXECUTION HOST - OSError: [Errno 113] Connect call failed ('192.168.15.41', 22)"}""",
            {'key':'Command_Host_unavailable', 'tag':'Host_unavailable', 'host':'testhostX', 'user_host_port':'me@testhostX',
             'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'echo Hello'})



#if check_tnum('50', include0=False):
#     import time
#     # print (globvars.config.dump())
#     Path('/mnt/RAMDRIVE/fsactivity/recursive tests/george').touch()
#     while True:
#         dotest ("No such host",
#             "",
#             {'key':'Activity_development', 'tag':'development', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s reCurSive /mnt/RAMDRIVE/fsactivity/a*'})

#         break
#         time.sleep (5)
#     print (host_connections)


host_connections.close('all')
