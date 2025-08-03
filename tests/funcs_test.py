#!/usr/bin/env python3
"""Demo/test for lanmonfuncs

Produce / compare to golden results:
    ./funcs_test.py | diff funcs_test-golden.txt -
        Differences will be ping values, and test 4a will vary btw returncode 252 and 253
"""

#==========================================================
#
#  Chris Nelson, 2025-2025
#
#==========================================================

__version__ =   '3.5'
TOOLNAME =      'demo_funcs'

import argparse
import re
from pathlib import Path

from cjnfuncs.core              import set_toolname, setuplogging, logging, set_logging_level #, restore_logging_level
from cjnfuncs.configman         import config_item

import lanmonitor.globvars as globvars
import lanmonitor.lanmonfuncs as lanmonfuncs

set_toolname(TOOLNAME)

globvars.config = config_item()
globvars.config.cfg['nTries']           = 2
globvars.config.cfg['RetryInterval']    = '0s'
globvars.config.cfg['SSH_timeout']      = '2s'

setuplogging(ConsoleLogFormat="{module:>35}.{funcName:20} - {levelname:>8}:  {message}")
set_logging_level(logging.DEBUG)

parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('-t', '--test', default='0',
                    help="Test number to run (default 0).  0 runs all tests")
args = parser.parse_args()


# --------------------------------------------------------------------

def dotest (desc, expect, *args, **kwargs):
    global tnum
    logging.warning (f"\n\n==============================================================================================\n" +
                     f"Test {tnum} - {desc}\n" +
                     f"  GIVEN:      {args}, {kwargs}\n"
                     f"  EXPECT:     {expect}")
    try:
        rslt = lanmonfuncs.cmd_check(*args, **kwargs)
        rslt_code = {0:'RTN_PASS', 1:'RTN_WARNING', 2:'RTN_FAIL', 3:'RTN_CRITICAL'}[rslt[0]]
        rslt_record = rslt[1]
        logging.warning (f"\n  RETURNED:   {rslt_code} - {rslt_record}")
        return rslt
    except Exception as e:
        # logging.exception (f"\n  RAISED:     {type(e).__name__}: {e}")
        logging.error (f"\n  RAISED:     {type(e).__name__}: {e}")
        return e


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
    dotest ("A basic function test",
            "RTN_PASS - returncode=0, stdout='Hello!'",
            cmd= "echo Hello!", user_host_port='local', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('1b'):
    dotest ("ping known from local",
            "RTN_PASS - returncode=0, stdout=PING results",
            cmd= "ping -c 1 testhost", user_host_port='local', cmd_timeout= 1,
            return_type='cmdrun')


# Basic Fail checks run locally
if check_tnum('2a'):
    dotest ("Invalid command switch",
            "RTN_FAIL - returncode=2, stderr=...invalid option",
            cmd= "ls -laxyz", user_host_port='local', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('2b'):
    dotest ("Cmd times out",
            "RTN_FAIL - timeout, returncode=254, stderr=CommandTimedOut",
            cmd= "sleep 2", user_host_port='local', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('2c'):
    dotest ("Unknown command",
            "RTN_FAIL - returncode=127, stderr=...command not found",
            cmd= "nosuchcmd 5", user_host_port='local', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('2d'):
    dotest ("Invalid return_type",
            "RAISED - ValueError: Invalid return_type <cmdrunX> passed to cmd_check",
            cmd= "nosuchcmd 5", user_host_port='local', cmd_timeout= 1,
            return_type='cmdrunX')

if check_tnum('2e'):
    dotest ("ping unknown host",
            "RTN_FAIL - returncode=2, stderr=ping: nosuchhost.me: Name or service not known",
            cmd= "ping nosuchhost.me", user_host_port='local', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('2f'):
    dotest ("ping known unavailable host, short timeout",
            "RTN_FAIL - returncode=254, stderr=CommandTimedOut",
            cmd= "ping testhostx", user_host_port='local', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('2g'):
    dotest ("No permission",
            "RTN_FAIL - returncode=1, stderr=...Permission denied",
            cmd= "touch /junk", user_host_port='local', cmd_timeout= 1,
            return_type='cmdrun')


# Basic Pass checks run remotely
if check_tnum('3a'):
    dotest ("echo on known available host",
            "RTN_PASS - returncode=0, stdout=Hello!",
            cmd= "echo Hello!", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type='cmdrun')
    logging.info (f"\n{lanmonfuncs.host_connections}")

if check_tnum('3b'):
    dotest ("ping known from known remote",
            "RTN_PASS - returncode=0, stdout=PING results",
            cmd= "ping -c 1 testhost", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type='cmdrun')


# Basic Fail checks run remotely
if check_tnum('4a'):
    # Varies between 252 and 253, including:
    # RETURNED:   RTN_WARNING - CompletedProcess(... returncode=252, ... stderr='Host <me@testhostx> connection failed:  TimeoutError: timed out')
    # RETURNED:   RTN_FAIL    - CompletedProcess(... returncode=253, ... stderr='Host <me@testhostx> connection failed:  timeout: timed out')
    # RETURNED:   RTN_FAIL    - CompletedProcess(... returncode=253, ... stderr='Host <me@testhostx> connection failed:  NoValidConnectionsError: [Errno None] Unable to connect to port 22 on ...')
    dotest ("echo on known unavailable host",
            "RTN_WARNING - returncode=252, stderr=...TimeoutError",
            cmd= "echo Hello!", user_host_port='me@testhostx', cmd_timeout= 1,
            return_type='cmdrun')
    logging.info (f"\n{lanmonfuncs.host_connections}")

if check_tnum('4b'):
    dotest ("connect to known host with wrong user",
            "RTN_FAIL - returncode=253, stderr=...AuthenticationException",
            cmd= "echo Hello!", user_host_port='you@testhost2', cmd_timeout= 1,
            return_type='cmdrun')
    logging.info (f"\n{lanmonfuncs.host_connections}")

if check_tnum('4c'):
    dotest ("connect to known host with wrong port",
            "RTN_FAIL - returncode=253, stderr=...NoValidConnectionsError",
            cmd= "echo Hello!", user_host_port='me@testhost2:2222', cmd_timeout= 1,
            return_type='cmdrun')
    logging.info (f"\n{lanmonfuncs.host_connections}")

if check_tnum('4d'):
    dotest ("Run remote with timeout",
            "RTN_FAIL - returncode=254, stderr=...CommandTimedOut",
            cmd= "sleep 2", user_host_port='me@testhost2:22', cmd_timeout= 1,
            return_type='cmdrun')
    logging.info (f"\n{lanmonfuncs.host_connections}")

if check_tnum('4e'):
    dotest ("No permission error on remote",
            "RTN_FAIL - returncode=1, stderr=...Permission denied",
            cmd= "touch /junk", user_host_port='me@testhost2:22', cmd_timeout= 1,
            return_type='cmdrun')
    logging.info (f"\n{lanmonfuncs.host_connections}")


# Check for return_type check_string on local.  Static file used to eliminate diffs.
if check_tnum('5a'):
    dotest ("Global text match check",
            "RTN_PASS - returncode=0, stdout=dbus status",
            cmd= "cat funcs_test_dbus.txt", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            expected_text=      'active (running)'
    )

if check_tnum('5b'):
    dotest ("Qualified line text match check",
            "RTN_PASS - returncode=0, stdout=dbus status",
            cmd= "cat funcs_test_dbus.txt", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:',
            expected_text=      'active (running)'
    )

if check_tnum('5c'):
    dotest ("Qualified line text match check with not_text",
            "RTN_PASS - returncode=0, stdout=dbus status",
            cmd= "cat funcs_test_dbus.txt", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:',
            expected_text=      'active (running)',
            not_text=           'inactive (dead)'
    )
        
if check_tnum('5d'):
    dotest ("check_line_text no match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat funcs_test_dbus.txt", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'ActiveX:',
            expected_text=      'active (running)',
            not_text=           'inactive (dead)'
    )
        
if check_tnum('5e'):
    dotest ("expected_text no match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat funcs_test_dbus.txt", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:',
            expected_text=      'inactive (dead)'
    )
        
if check_tnum('5f'):
    dotest ("not_text match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat funcs_test_dbus.txt", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:',
            not_text=           'active (running)'
    )
        
if check_tnum('5g'):
    dotest ("Neither expected_text nor not_text are given",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat funcs_test_dbus.txt", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:'
    )


# Check for return_type check_string on remote
if check_tnum('6a'):
    dotest ("Global text match check",
            "RTN_PASS - returncode=0, stdout=dbus status",
            cmd= "cat funcs_test_dbus.txt", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            expected_text=      'active (running)'
    )

if check_tnum('6b'):
    dotest ("Qualified line text match check",
            "RTN_PASS - returncode=0, stdout=dbus status",
            cmd= "cat funcs_test_dbus.txt", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:',
            expected_text=      'active (running)'
    )

if check_tnum('6c'):
    dotest ("Qualified line text match check with not_text",
            "RTN_PASS - returncode=0, stdout=dbus status",
            cmd= "cat funcs_test_dbus.txt", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:',
            expected_text=      'active (running)',
            not_text=           'inactive (dead)'
    )
        
if check_tnum('6d'):
    dotest ("check_line_text no match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat funcs_test_dbus.txt", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'ActiveX:',
            expected_text=      'active (running)',
            not_text=           'inactive (dead)'
    )
        
if check_tnum('6e'):
    dotest ("expected_text no match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat funcs_test_dbus.txt", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:',
            expected_text=      'inactive (dead)'
    )
        
if check_tnum('6f'):
    dotest ("not_text match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat funcs_test_dbus.txt", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:',
            not_text=           'active (running)'
    )
        
if check_tnum('6g'):
    dotest ("Neither expected_text nor not_text are given",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat funcs_test_dbus.txt", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:'
    )


tnum = '50'
if args.test == tnum:
    dotest ("Development/testing",
            "",
            cmd= "cat /mnt/share/dev/packages/lanmonitor/tests/funcs_test_dbus.txt | grep Active: > junk.txt",
            # user_host_port='local',
            user_host_port='me@testhost2',
            cmd_timeout= 1,
            return_type=        'cmdrun')

tnum = '51'
if args.test == tnum:
    dotest ("Development/testing",
            "",
            cmd= "sleep 2",
            # user_host_port='local',
            user_host_port='local',
            cmd_timeout= 0.2,
            return_type=        'cmdrun',
            # check_line_text=    'ActiveX:',
            # expected_text=      'active (running)',
            not_text=           'inactive (dead)'
            )



lanmonfuncs.host_connections.closeall()
