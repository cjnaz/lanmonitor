#!/usr/bin/env python3
"""Demo/test for fsactivity_plugin

Produce / compare to golden results:
    ./fsactivity_plugin_test.py | diff fsactivity_plugin_test.golden -
        Expected differences:
            File timestamps and ages for newfile, george, mahesh
            Ages for too old tests 2e, 2f, 4e, 4f, 6b1, 6b2, 6c
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 3.5 250811 - Updated to lanmonitor V3.5
#
#==========================================================

__version__ =   '3.5'
TOOLNAME =      'demo_fsactivity_plugin'

import argparse
import re
import time
import subprocess
from pathlib import Path
import shutil

from cjnfuncs.core              import set_toolname, setuplogging, logging, set_logging_level
from cjnfuncs.configman         import config_item

import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, host_connections

try:
    from fsactivity_plugin import monitor               # Use version in cwd
except:
    from lanmonitor.fsactivity_plugin import monitor    # Use version in the package

set_toolname(TOOLNAME)

cfg = """
[DEFAULT]
Connection_timeout =            4s
Connection_nTries =             1
Connection_retry_interval =     0s

Command_nTries =                1
Command_retry_interval =        0s
Command_max_consecutive_timeouts =  2
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
shutil.rmtree ('/mnt/RAMDRIVE/fsactivity', ignore_errors=True)
shutil.copytree ('./plugin_test_trees/fsactivity', '/mnt/RAMDRIVE/fsactivity', dirs_exist_ok=True)
Path('/mnt/RAMDRIVE/fsactivity/newfile').touch()

if check_tnum('1a'):
    dotest ("Local dir activity pass",
            "{'rslt': 0, 'notif_key': 'Activity_local_dir_pass', 'message': 'Activity_local_dir_pass  OK - local -    0.0 mins  (   1 mins  max)  /mnt/RAMDRIVE/fsactivity/newfile'}",
            {'key':'Activity_local_dir_pass', 'tag':'local_dir_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m  /mnt/RAMDRIVE/fsactivity/   '})

if check_tnum('1b'):
    dotest ("Local specific file activity pass",
            "{'rslt': 0, 'notif_key': 'Activity_local_dir_pass', 'message': 'Activity_local_dir_pass  OK - local -    0.0 weeks (1000 weeks max)  /mnt/RAMDRIVE/fsactivity/a1file'}",
            {'key':'Activity_local_dir_pass', 'tag':'local_dir_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1000w /mnt/RAMDRIVE/fsactivity/a1file'})

if check_tnum('1c'):
    dotest ("Local wildcard file activity pass",
            "{'rslt': 0, 'notif_key': 'Activity_local_dir_pass', 'message': 'Activity_local_dir_pass  OK - local -    0.0 weeks (1000 weeks max)  /mnt/RAMDRIVE/fsactivity/a2file'}",
            {'key':'Activity_local_dir_pass', 'tag':'local_dir_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1000w /mnt/RAMDRIVE/fsactivity/a*file'})

if check_tnum('1d'):
    dotest ("Local space in filename pass",
            "{'rslt': 0, 'notif_key': 'Activity_local_dir_pass', 'message': 'Activity_local_dir_pass  OK - local -    0.0 weeks (1000 weeks max)  /mnt/RAMDRIVE/fsactivity/space in name'}",
            {'key':'Activity_local_dir_pass', 'tag':'local_dir_pass', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1000w /mnt/RAMDRIVE/fsactivity/* name'})


# Basic Fail cases run locally
if check_tnum('2a'):
    dotest ("Local empty dir activity FAIL",
            "{'rslt': 3, 'notif_key': 'Activity_local_empty_dir_fail', 'message': '  WARNING: Activity_local_empty_dir_fail - local - FILE(S) NOT FOUND AT </mnt/RAMDRIVE/fsactivity/empty_dir>/ ()'}",
            {'key':'Activity_local_empty_dir_fail', 'tag':'local_empty_dir_fail', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity/empty_dir/'})

if check_tnum('2b1'):
    dotest ("Local specific dir not found FAIL",
            "{'rslt': 3, 'notif_key': 'Activity_local_specific_filedir_not_found_fail', 'message': '  WARNING: Activity_local_specific_filedir_not_found_fail - local - FILE(S) NOT FOUND AT </mnt/RAMDRIVE/fsactivity/nosuchdir/> (find: ‘/mnt/RAMDRIVE/fsactivity/nosuchdir/’: No such file or directory)'}",
            {'key':'Activity_local_specific_filedir_not_found_fail', 'tag':'local_specific_filedir_not_found_fail', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity/nosuchdir/'})

if check_tnum('2b2'):
    dotest ("Local specific file not found FAIL",
            "{'rslt': 3, 'notif_key': 'Activity_local_specific_filedir_not_found_fail', 'message': '  WARNING: Activity_local_specific_filedir_not_found_fail - local - FILE(S) NOT FOUND AT </mnt/RAMDRIVE/fsactivity/nosuchfile> ()'}",
            {'key':'Activity_local_specific_filedir_not_found_fail', 'tag':'local_specific_filedir_not_found_fail', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity/nosuchfile'})

if check_tnum('2c'):
    dotest ("Local wildcard file not found FAIL",
            "{'rslt': 2, 'notif_key': 'Activity_local_wildcard_file_not_found_fail', 'message': '  WARNING: Activity_local_wildcard_file_not_found_fail - local - FILE(S) NOT FOUND AT </mnt/RAMDRIVE/fsactivity/nosuch*> ()'}",
            {'key':'Activity_local_wildcard_file_not_found_fail', 'tag':'local_wildcard_file_not_found_fail', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity/nosuch*'})

if check_tnum('2d'):
    time.sleep (1)
    dotest ("Local dir too old FAIL",
            "{'rslt': 2, 'notif_key': 'Activity_local_dir_too_old_fail', 'message': '  FAIL: Activity_local_dir_too_old_fail  STALE FILES - local -    2.9 secs  (   1 secs  max)  /mnt/RAMDRIVE/fsactivity/newfile'}",
            {'key':'Activity_local_dir_too_old_fail', 'tag':'local_dir_too_old_fail', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /mnt/RAMDRIVE/fsactivity/'})

if check_tnum('2e'):
    time.sleep (1)
    dotest ("Local specific file too old FAIL",
            "{'rslt': 2, 'notif_key': 'Activity_local_specific_file_too_old_fail', 'message': '  FAIL: Activity_local_specific_file_too_old_fail  STALE FILES - local - 18101.7 secs  (   1 secs  max)  /mnt/RAMDRIVE/fsactivity/a1file'}",
            {'key':'Activity_local_specific_file_too_old_fail', 'tag':'local_specific_file_too_old_fail', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /mnt/RAMDRIVE/fsactivity/a1file'})

if check_tnum('2f'):
    time.sleep (1)
    dotest ("Local wildcard file too old FAIL",
            "{'rslt': 2, 'notif_key': 'Activity_local_wildcard_file_too_old_fail', 'message': '  FAIL: Activity_local_wildcard_file_too_old_fail  STALE FILES - local - 18093.2 secs  (   1 secs  max)  /mnt/RAMDRIVE/fsactivity/a2file'}",
            {'key':'Activity_local_wildcard_file_too_old_fail', 'tag':'local_wildcard_file_too_old_fail', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /mnt/RAMDRIVE/fsactivity/a*file'})

# target timeout > warning


# Basic Pass checks run remotely
if check_tnum('3a'):
    subprocess.run(['ssh', 'me@testhost2', 'rm', '-rf', '/mnt/RAMDRIVE/fsactivity'],
                    capture_output=True, text=True)
    subprocess.run(['scp', '-rp', './plugin_test_trees/fsactivity', 'me@testhost2:/mnt/RAMDRIVE/'],
                    capture_output=True, text=True)
    subprocess.run(['ssh', 'me@testhost2', 'touch', '/mnt/RAMDRIVE/fsactivity/newfile'],
                    capture_output=True, text=True)
    dotest ("Remote dir activity pass",
            "{'rslt': 0, 'notif_key': 'Activity_remote_dir_pass', 'message': 'Activity_remote_dir_pass  OK - testhost2 -    0.0 mins  (   1 mins  max)  /mnt/RAMDRIVE/fsactivity/newfile'}",
            {'key':'Activity_remote_dir_pass', 'tag':'remote_dir_pass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity/   '})

if check_tnum('3b'):
    dotest ("Remote specific file activity pass",
            "{'rslt': 0, 'notif_key': 'Activity_remote_dir_pass', 'message': 'Activity_remote_dir_pass  OK - testhost2 -    0.0 weeks (1000 weeks max)  /mnt/RAMDRIVE/fsactivity/a1file'}",
            {'key':'Activity_remote_dir_pass', 'tag':'remote_dir_pass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1000w /mnt/RAMDRIVE/fsactivity/a1file'})

if check_tnum('3c'):
    dotest ("Remote wildcard file activity pass",
            "{'rslt': 0, 'notif_key': 'Activity_remote_dir_pass', 'message': 'Activity_remote_dir_pass  OK - testhost2 -    0.0 weeks (1000 weeks max)  /mnt/RAMDRIVE/fsactivity/a2file'}",
            {'key':'Activity_remote_dir_pass', 'tag':'remote_dir_pass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1000w /mnt/RAMDRIVE/fsactivity/a*file'})

if check_tnum('3d'):
    dotest ("Remote space in filename pass",
            "{'rslt': 0, 'notif_key': 'Activity_remote_dir_pass', 'message': 'Activity_remote_dir_pass  OK - testhost2 -    0.0 weeks (1000 weeks max)  /mnt/RAMDRIVE/fsactivity/space in name'}",
            {'key':'Activity_remote_dir_pass', 'tag':'remote_dir_pass', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1000w /mnt/RAMDRIVE/fsactivity/* name'})


# Basic Fail cases run remotely
if check_tnum('4a'):
    dotest ("Remote empty dir activity FAIL",
            "{'rslt': 3, 'notif_key': 'Activity_remote_empty_dir_fail', 'message': '  WARNING: Activity_remote_empty_dir_fail - testhost2 - FILE(S) NOT FOUND AT </mnt/RAMDRIVE/fsactivity/empty_dir> ()'}",
            {'key':'Activity_remote_empty_dir_fail', 'tag':'remote_empty_dir_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity/empty_dir/'})

if check_tnum('4b1'):
    dotest ("Remote specific dir not found FAIL",
            "{'rslt': 3, 'notif_key': 'Activity_remote_specific_filedir_not_found_fail', 'message': '  WARNING: Activity_remote_specific_filedir_not_found_fail - testhost2 - FILE(S) NOT FOUND AT </mnt/RAMDRIVE/fsactivity/nosuchdir/> (find: ‘/mnt/RAMDRIVE/fsactivity/nosuchdir/’: No such file or directory)'}",
            {'key':'Activity_remote_specific_filedir_not_found_fail', 'tag':'remote_specific_filedir_not_found_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity/nosuchdir/'})

if check_tnum('4b2'):
    dotest ("Remote specific file not found FAIL",
            "{'rslt': 3, 'notif_key': 'Activity_remote_specific_filedir_not_found_fail', 'message': '  WARNING: Activity_remote_specific_filedir_not_found_fail - testhost2 - FILE(S) NOT FOUND AT </mnt/RAMDRIVE/fsactivity/nosuchfile> ()'}",
            {'key':'Activity_remote_specific_filedir_not_found_fail', 'tag':'remote_specific_filedir_not_found_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity/nosuchfile'})


if check_tnum('4c'):
    dotest ("Remote wildcard file not found FAIL",
            "{'rslt': 2, 'notif_key': 'Activity_remote_wildcard_file_not_found_fail', 'message': '  WARNING: Activity_remote_wildcard_file_not_found_fail - testhost2 - FILE(S) NOT FOUND AT </mnt/RAMDRIVE/fsactivity/nosuch*> ()'}",
            {'key':'Activity_remote_wildcard_file_not_found_fail', 'tag':'remote_wildcard_file_not_found_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity/nosuch*'})

if check_tnum('4d'):
    time.sleep (1)
    dotest ("Remote dir too old FAIL",
            "{'rslt': 2, 'notif_key': 'Activity_remote_dir_too_old_fail', 'message': '  FAIL: Activity_remote_dir_too_old_fail  STALE FILES - testhost2 -    2.5 secs  (   1 secs  max)  /mnt/RAMDRIVE/fsactivity/newfile'}",
            {'key':'Activity_remote_dir_too_old_fail', 'tag':'remote_dir_too_old_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /mnt/RAMDRIVE/fsactivity/'})

if check_tnum('4e'):
    time.sleep (1)
    dotest ("Remote specific file too old FAIL",
            "{'rslt': 2, 'notif_key': 'Activity_remote_specific_file_too_old_fail', 'message': '  FAIL: Activity_remote_specific_file_too_old_fail  STALE FILES - testhost2 - 18706.4 secs  (   1 secs  max)  /mnt/RAMDRIVE/fsactivity/a1file'}",
            {'key':'Activity_remote_specific_file_too_old_fail', 'tag':'remote_specific_file_too_old_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /mnt/RAMDRIVE/fsactivity/a1file'})

if check_tnum('4f'):
    time.sleep (1)
    dotest ("Remote wildcard file too old FAIL",
            "{'rslt': 2, 'notif_key': 'Activity_remote_wildcard_file_too_old_fail', 'message': '  FAIL: Activity_remote_wildcard_file_too_old_fail  STALE FILES - testhost2 - 18697.5 secs  (   1 secs  max)  /mnt/RAMDRIVE/fsactivity/a2file'}",
            {'key':'Activity_remote_wildcard_file_too_old_fail', 'tag':'remote_wildcard_file_too_old_fail', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /mnt/RAMDRIVE/fsactivity/a*file'})


# Other cases
if check_tnum('5a'):
    dotest ("No such host",
            "{'rslt': 2, 'notif_key': 'Activity_no_such_host', 'message': '  WARNING: Activity_no_such_host - nosuchhost - Exception while connecting to me@nosuchhost:22: ConnectionError - Connection to <me@nosuchhost:22> FAILED after 1 attempts: gaierror: [Errno -2] Name or service not known'}",
            {'key':'Activity_no_such_host', 'tag':'no_such_host', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /mnt/RAMDRIVE/fsactivity/a*file'})

if check_tnum('5b'):
    dotest ("Known host, unavailable",
            """{'rslt': 1, 'notif_key': 'Activity_known_unavailable', 'message': "  WARNING: Activity_known_unavailable - testhostx - Exception while connecting to me@testhostx:22: ConnectionError - Connection to <me@testhostx:22> FAILED after 1 attempts: OSError: [Errno 113] Connect call failed ('192.168.15.41', 22)"}""",
            {'key':'Activity_known_unavailable', 'tag':'known_unavailable', 'host':'testhostx', 'user_host_port':'me@testhostx', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s /mnt/RAMDRIVE/fsactivity/a*file'})


# Recursive checks
if check_tnum('6a'):
    Path('/mnt/RAMDRIVE/fsactivity/recursive tests/george').touch()
    dotest ("Recursive find",
            "{'rslt': 0, 'notif_key': 'Activity_recursive', 'message': 'Activity_recursive  OK - local -    0.0 mins  (   1 mins  max)  /mnt/RAMDRIVE/fsactivity/recursive tests/george'}",
            {'key':'Activity_recursive', 'tag':'recursive', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m recursive /mnt/RAMDRIVE/fsactivity/'})

if check_tnum('6b1'):
    dotest ("Recursion with specific file specified",
            "{'rslt': 2, 'notif_key': 'Activity_recursive_with_specific_file', 'message': '  FAIL: Activity_recursive_with_specific_file  STALE FILES - local - 3233.4 mins  (   1 mins  max)  /mnt/RAMDRIVE/fsactivity/recursive tests/a3file'}",
            {'key':'Activity_recursive_with_specific_file', 'tag':'recursive_with_specific_file', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m recursive /mnt/RAMDRIVE/fsactivity/a3file'})

if check_tnum('6b2'):
    dotest ("Recursion with specific file specified",
            "{'rslt': 2, 'notif_key': 'Activity_recursive_with_specific_file', 'message': '  FAIL: Activity_recursive_with_specific_file  STALE FILES - local - 3649.3 mins  (   1 mins  max)  /mnt/RAMDRIVE/fsactivity/a2file'}",
            {'key':'Activity_recursive_with_specific_file', 'tag':'recursive_with_specific_file', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m recursive /mnt/RAMDRIVE/fsactivity/a2file'})


if check_tnum('6c'):
    subprocess.run(['ssh', 'me@testhost2', 'rm', '-rf', '/mnt/RAMDRIVE/fsactivity'],
                    capture_output=True, text=True)
    subprocess.run(['scp', '-rp', './plugin_test_trees/fsactivity', 'me@testhost2:/mnt/RAMDRIVE/'],
                    capture_output=True, text=True)
    dotest ("Remote recursive find",
            "{'rslt': 2, 'notif_key': 'Activity_remote_recursive', 'message': '  FAIL: Activity_remote_recursive  STALE FILES - testhost2 -   42.0 mins  (   1 mins  max)  /mnt/RAMDRIVE/fsactivity/recursive tests/a4file'}",
            {'key':'Activity_remote_recursive', 'tag':'remote_recursive', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m recursive /mnt/RAMDRIVE/fsactivity/'})

if check_tnum('6d'):
    subprocess.run(['ssh', 'me@testhost2', 'touch', '/mnt/RAMDRIVE/fsactivity/recursive\ tests/mahesh'],
                    capture_output=True, text=True)
    dotest ("Remote recursive find",
            "{'rslt': 0, 'notif_key': 'Activity_remote_recursive', 'message': 'Activity_remote_recursive  OK - testhost2 -    0.0 mins  (   1 mins  max)  /mnt/RAMDRIVE/fsactivity/recursive tests/mahesh'}",
            {'key':'Activity_remote_recursive', 'tag':'remote_recursive', 'host':'testhost2', 'user_host_port':'me@testhost2', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m recursive /mnt/RAMDRIVE/fsactivity/'})



# Run from testhost2.  Loops test on testhost.  Cycle testhost network down and up.
tnum = '20'
if args.test == tnum:
    setuplogging (ConsoleLogFormat = '{asctime} {module:>15}.{funcName:20} {levelname:>8}:  {message}')
    loop_count = 0
    while True:
        loop_count += 1

        dotest ("Remote - testhost2 > testhost",
                "",
                {'key':'Activity_network_down_test', 'tag':'network_down_test', 'host':'testhost', 'user_host_port':'me@testhost', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1m /mnt/RAMDRIVE/fsactivity   '})
        logging.info (f"Loop {loop_count}")
        time.sleep (3)



tnum = '50'
if args.test == tnum:

    import time
    # print (globvars.config.dump())
    Path('/mnt/RAMDRIVE/fsactivity/recursive tests/george').touch()
    while True:
        dotest ("No such host",
            "",
            {'key':'Activity_development', 'tag':'development', 'host':'local', 'user_host_port':'local', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'1s reCurSive /mnt/RAMDRIVE/fsactivity/a*'})

        break
        time.sleep (5)
    print (host_connections)


host_connections.close('all')
