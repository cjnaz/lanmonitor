#!/usr/bin/env python3
"""Demo/test for lanmonfuncs

Produce / compare to golden results:
    ./funcs_test.py | diff funcs_test-golden.txt -
        Differences:
            ping values will vary
            test 4a will vary btw returncode 252 and 253
            test 7e/7f object addresses will vary
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
import time

from cjnfuncs.core              import set_toolname, setuplogging, logging, set_logging_level #, restore_logging_level
from cjnfuncs.configman         import config_item

import lanmonitor.globvars as globvars
import lanmonitor.lanmonfuncs as lanmonfuncs

set_toolname(TOOLNAME)


cfg = """
[DEFAULT]
Connection_timeout =            1.5s
Connection_nTries =             2
Connection_retry_interval =     0.4s

Command_timeout =               1.0s
Command_nTries =                2
Command_retry_interval =        0.2s
Command_max_consecutive_timeouts =  4

[local]
hostname =                      localhost
username =                      me
port =                          22
#env =                          {'LC_123': 'This is a test'}

[testhost]
hostname =                      testhost
username =                      me
port =                          22

[testhost2]
hostname =                      testhost2
username =                      me
port =                          22
Command_max_consecutive_timeouts = 1

[testhostx]
hostname =                      testhostx
username =                      me
port =                          22
Connection_timeout =            0.5
Connection_nTries =             3
Connection_retry_interval =     0.2

[bad host def]

[testhost2 with defaults]
hostname =                      testhost2
username =                      me

[testhost2 define all]
hostname =                      testhost2
username =                      me
port =                          22
Connection_timeout =            10s
Connection_nTries =             11
Connection_retry_interval =     12s
Command_nTries =                13
Command_retry_interval          14.2s
Command_max_consecutive_timeouts 15
env = {'xyz': 'wyz'}

[Test 8]
hostname =                      testhost2
username =                      me
Command_nTries =                3
Command_retry_interval          0s
Command_max_consecutive_timeouts 2

[Test 20]
hostname =                      testhost
username =                      me

Connection_timeout =            1.5s
Connection_nTries =             2
Connection_retry_interval =     0.4s

Command_timeout =               1.0s
Command_nTries =                2
Command_retry_interval =        0.2s
Command_max_consecutive_timeouts =  4

"""

globvars.config = config_item()
globvars.config.read_string(cfg)

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
            cmd= "echo Hello!", user_host_port='testhostx', cmd_timeout= 1,
            return_type='cmdrun')
    logging.info (f"\n{lanmonfuncs.host_connections}")
    # dotest ("echo on known unavailable host",
    #         "RTN_WARNING - returncode=252, stderr=...TimeoutError",
    #         cmd= "echo Hello!", user_host_port='me@testhostx', cmd_timeout= 1,
    #         return_type='cmdrun')
    # logging.info (f"\n{lanmonfuncs.host_connections}")

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
# cwd is the login user's home directory.  ~/.bash_logout containing <if [ "$SHLVL" = 1 ]; then>
if check_tnum('5a'):
    dotest ("Global text match check",
            # "RTN_PASS - returncode=0, stdout=dbus status",
            # cmd= "cat /mnt/share/dev/packages/lanmonitor/tests/funcs_test_dbus.txt", user_host_port='local', cmd_timeout= 1,
            "RTN_PASS - returncode=0, stdout= .bashrc_logout file",
            cmd= "cat .bash_logout", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            # expected_text=      'active (running)'
            expected_text=      '$SHLVL'
    )

if check_tnum('5b'):
    dotest ("Qualified line text match check",
            "RTN_PASS - returncode=0, stdout= .bashrc_logout file",
            cmd= "cat .bash_logout", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLVL"',
            expected_text=      '= 1'
    )

if check_tnum('5c'):
    dotest ("Qualified line text match check with not_text",
            "RTN_PASS - returncode=0, stdout= .bashrc_logout file",
            cmd= "cat .bash_logout", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLVL"',
            expected_text=      '= 1',
            not_text=           '#'
    )
        
if check_tnum('5d'):
    dotest ("check_line_text no match",
            "RTN_FAIL - returncode=1, stdout= .bashrc_logout file, stderr='check_string mode mismatch'",
            cmd= "cat .bash_logout", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLxVL"',
            expected_text=      '= 1',
            not_text=           '#'
    )
        
if check_tnum('5e'):
    dotest ("expected_text no match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat .bash_logout", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLVL"',
            expected_text=      '= 2'
    )
        
if check_tnum('5f'):
    dotest ("not_text match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat .bash_logout", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLVL"',
            not_text=           'SHLVL'
    )
        
if check_tnum('5g'):
    dotest ("Neither expected_text nor not_text are given",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat .bash_logout", user_host_port='local', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:'
    )


# Check for return_type check_string on remote
if check_tnum('6a'):
    dotest ("Global text match check",
            "RTN_PASS - returncode=0, stdout= .bashrc_logout file",
            cmd= "cat .bash_logout", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            expected_text=      '$SHLVL'
    )

if check_tnum('6b'):
    dotest ("Qualified line text match check",
            "RTN_PASS - returncode=0, stdout= .bashrc_logout file",
            cmd= "cat .bash_logout", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLVL"',
            expected_text=      '= 1'
    )

if check_tnum('6c'):
    dotest ("Qualified line text match check with not_text",
            "RTN_PASS - returncode=0, stdout= .bashrc_logout file",
            cmd= "cat .bash_logout", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLVL"',
            expected_text=      '= 1',
            not_text=           '#'
    )
        
if check_tnum('6d'):
    dotest ("check_line_text no match",
            "RTN_FAIL - returncode=1, stdout= .bashrc_logout file, stderr='check_string mode mismatch'",
            cmd= "cat .bash_logout", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLxVL"',
            expected_text=      '= 1',
            not_text=           '#'
    )
        
if check_tnum('6e'):
    dotest ("expected_text no match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat .bash_logout", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLVL"',
            expected_text=      '= 2'
    )
        
if check_tnum('6f'):
    dotest ("not_text match",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat .bash_logout", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'if [ "$SHLVL"',
            not_text=           'SHLVL'
    )
        
if check_tnum('6g'):
    dotest ("Neither expected_text nor not_text are given",
            "RTN_FAIL - returncode=1, stdout=dbus status, stderr='check_string mode mismatch'",
            cmd= "cat .bash_logout", user_host_port='me@testhost2', cmd_timeout= 1,
            return_type=        'check_string',
            check_line_text=    'Active:'
    )


# Checks for connection defined by host section in config
if check_tnum('7a'):
    dotest ("No host section in config",
            "RAISED - cjnfuncs.core.ConfigError: Host section <bad host def X> not in config.",
            cmd= "echo Hello", user_host_port='bad host def X', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('7b'):
    dotest ("No hostname definition in config host section",
            "RAISED - cjnfuncs.core.ConfigError: Param <[bad host def] hostname> not in <None> and no default or fallback.",
            cmd= "echo Hello", user_host_port='bad host def', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('7c'):
    globvars.config.cfg['bad host def']['hostname'] = 'xyz'
    dotest ("No username definition in config host section",
            "RAISED - cjnfuncs.core.ConfigError: Param <[bad host def] username> not in <None> and no default or fallback.",
            cmd= "echo Hello", user_host_port='bad host def', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('7d'):
    globvars.config.cfg['bad host def']['hostname'] = 'xyz'
    globvars.config.cfg['bad host def']['username'] = 'xyz'
    dotest ("hostname and username defined in config host section",
            "RTN_WARNING - returncode=252, Exception while connecting to xyz@xyz:22: ConnectionError ... No address associated with hostname",
            cmd= "echo Hello", user_host_port='bad host def', cmd_timeout= 1,
            return_type='cmdrun')

if check_tnum('7e'):
    lanmonfuncs.host_connections.close('all')   # Whack any previous definition of me@testhost2:22
    dotest ("host section with minimal defs and defaults",
            "RTN_PASS - returncode=0, stdout=Hello!",
            cmd= "echo Hello", user_host_port='testhost2 with defaults', cmd_timeout= 1,
            return_type='cmdrun')
    logging.info (f"\n{lanmonfuncs.host_connections.connections['me@testhost2:22']}")

if check_tnum('7f'):
    dotest ("host section with everything defined",
            "RTN_PASS - returncode=0, stdout=Hello!",
            cmd= "echo Hello", user_host_port='testhost2 define all', cmd_timeout= 1,
            return_type='cmdrun')
    logging.info (f"\n{lanmonfuncs.host_connections.connections['me@testhost2:22']}")


# Check consecutive command timeouts logic
# These tests are effective when run in the full test 8 sequence.
if check_tnum('8a'):
    lanmonfuncs.host_connections.close('all')   # Whack any previous definition of me@testhost2:22
    dotest ("Check command timeout logic",
            "RTN_WARNING - returncode=252, ... ConnectionError: ... TimeoutError:",
            cmd= "sleep 2", user_host_port='Test 8', cmd_timeout= 0.5,
            return_type='cmdrun')

if check_tnum('8b'):
    globvars.config.cfg['Test 8']['Command_nTries'] = 1
    globvars.config.cfg['Test 8']['Command_max_consecutive_timeouts'] = 2
    lanmonfuncs.host_connections.close('all')   # Whack any previous definition of me@testhost2:22
    dotest ("Cause 1st of 2 timeouts",
            "RTN_FAIL - returncode=254, ... TimeoutError:",
            cmd= "sleep 2", user_host_port='Test 8', cmd_timeout= 0.5,
            return_type='cmdrun')
    logging.info (f"Consecutive timeouts count: {lanmonfuncs.host_connections.connections['me@testhost2:22']['consecutive_command_timeouts']}")

if check_tnum('8c'):
    dotest ("Cause 2nd of 2 timeouts",
            "RTN_WARNING - returncode=252, ... ConnectionError: ... TimeoutError:",
            cmd= "sleep 2", user_host_port='Test 8', cmd_timeout= 0.5,
            return_type='cmdrun')

if check_tnum('8d'):
    lanmonfuncs.host_connections.close('all')   # Whack any previous definition of me@testhost2:22
    globvars.config.cfg['Test 8']['Command_nTries'] = 1
    globvars.config.cfg['Test 8']['Command_max_consecutive_timeouts'] = 2
    dotest ("Cause 1st timeout",
            "RTN_FAIL - returncode=254, ... TimeoutError:",
            cmd= "sleep 2", user_host_port='Test 8', cmd_timeout= 0.5,
            return_type='cmdrun')
    logging.info (f"Consecutive timeouts count: {lanmonfuncs.host_connections.connections['me@testhost2:22']['consecutive_command_timeouts']}")

if check_tnum('8e'):
    dotest ("Reset of consecutive_command_timeouts",
            "RTN_PASS - returncode=0, stdout='Hello!'",
            cmd= "echo Hello!", user_host_port='Test 8', cmd_timeout= 0.5,
            return_type='cmdrun')
    logging.info (f"Consecutive timeouts count: {lanmonfuncs.host_connections.connections['me@testhost2:22']['consecutive_command_timeouts']}")

if check_tnum('8f'):
    dotest ("Cause 1st of 2 timeouts",
            "RTN_FAIL - returncode=254, ... TimeoutError:",
            cmd= "sleep 2", user_host_port='Test 8', cmd_timeout= 0.5,
            return_type='cmdrun')
    logging.info (f"Consecutive timeouts count: {lanmonfuncs.host_connections.connections['me@testhost2:22']['consecutive_command_timeouts']}")

if check_tnum('8g'):
    dotest ("Cause 2nd of 2 timeouts",
            "RTN_WARNING - returncode=252, ... ConnectionError: ... TimeoutError:",
            cmd= "sleep 2", user_host_port='Test 8', cmd_timeout= 0.5,
            return_type='cmdrun')

if check_tnum('8h'):
    dotest ("Create new connection",
            "RTN_PASS - returncode=0, stdout='Hello!'",
            cmd= "echo Hello!", user_host_port='Test 8', cmd_timeout= 0.5,
            return_type='cmdrun')
    logging.info (f"Consecutive timeouts count: {lanmonfuncs.host_connections.connections['me@testhost2:22']['consecutive_command_timeouts']}")



# Run from testhost2.  Loops test on testhost.  Cycle testhost network donw and up.
tnum = '20'
if args.test == tnum:
    setuplogging (ConsoleLogFormat = '{asctime} {module:>15}.{funcName:20} {levelname:>8}:  {message}')
    loop_count = 0
    while True:
        loop_count += 1
        dotest ("Checks connection up/down logic",
            "Conseuctive command timeouts trigger closed connection.  Recover when network comes back up.",
            cmd= "echo Hello!!",
            user_host_port='Test 20',
            # user_host_port='testhost',
            cmd_timeout= 1,
            return_type=        'cmdrun')
        # break
        logging.info (f"Loop {loop_count}")
        time.sleep (3)



tnum = '50'
if args.test == tnum:

    import time
    # print (globvars.config.dump())
    while True:
        dotest ("Development/testing",
            "",
            cmd= "echo Hello!!",
            # user_host_port='local',
            user_host_port='testhost',
            cmd_timeout= 1,
            return_type=        'cmdrun')
        break
        time.sleep (5)

tnum = '51'
if args.test == tnum:
    # print (globvars.config.dump())
    globvars.config.cfg['local']['Max_consecutive_timeouts'] = 3
    globvars.config.cfg['local']['Command_retry_interval'] = 3
    dotest ("Development/testing - Max consec timeouts",
            "",
            # cmd= "env | grep LC_",
            cmd= "echo Hello!",
            user_host_port='local',
            cmd_timeout= 0.2,
            return_type=        'cmdrun',
            # check_line_text=    'ActiveX:',
            # expected_text=      'active (running)',
            not_text=           'inactive (dead)'
            )

    print (lanmonfuncs.host_connections)

lanmonfuncs.host_connections.close('all')
