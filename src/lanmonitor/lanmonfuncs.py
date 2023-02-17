#!/usr/bin/env python3
"""LAN monitor support functions
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2023
#
# 3.0 230301 - Packaged
# V1.4  221120  Summaries optional if SummaryDays is not defined.
# V1.3  220420  Incorporated funcs3 timevalue and retime (removed convert_time)
# V1.2a 220223  Bug fix in summary day calculation
# V1.2  210605  Reworked have_access check to check_LAN_access logic.
# V1.1  210523  cmd timeout tweaks
# V1.0  210507  V1.0
# V1.0a 210515  Set timeouts to 1s for ping and 5s for ssh commands on remotes
#   
#==========================================================

import sys
import os.path
import subprocess
import datetime
import time
import re
from cjnfuncs.cjnfuncs import logging, getcfg, timevalue #, snd_email, snd_notif

# Configs / Constants
NOTIF_SUBJ = "LAN Monitor"
RTN_PASS     = 0
RTN_WARNING  = 1
RTN_FAIL     = 2
RTN_CRITICAL = 3


# Module global vars
args = None
keylen = 0      # Padding vars used for pretty printing
hostlen = 0


USER_HOST_FORMAT = re.compile(r"[\w.-]+@([\w.-]+)$")
USER_HOST_PORT_FORMAT = re.compile(r"[\w.-]+@([\w.-]+):([\d]+)$")

def split_user_host_port(u_h_p):
    """ Handle variations in passed-in user_host_port (u_h_p)
        "local", "user@host", or "user@host:port"
    Return separate user_host, host, and port values
    EG:
        "xyz@host15:4455" returns:
            ["xyz@host15", "host15", "4455"]
        "xyz@host15" returns:
            ["xyz@host15", "host15", "22"]  (the default port is "22" for ssh)
        "local" returns
            ["local", "local", ""]
    """
    user_host_noport = u_h_p.split(":")[0]
    host = u_h_p
    port = ""
    if host != "local":
        port = "22"
        out = USER_HOST_FORMAT.match(u_h_p)
        if out:
            host = out.group(1)
        else:
            out = USER_HOST_PORT_FORMAT.match(u_h_p)
            if out:
                host = out.group(1)
                port = out.group(2)
            else:
                _msg = f"Expecting <user@host> or <user@host:port> format, but found <{u_h_p}>."
                # logging.error(f"ERROR:  {_msg}")
                raise ValueError (_msg)
    return user_host_noport, host, port


def cmd_check(cmd, user_host_port, return_type=None, check_line_text=None, expected_text=None, not_text=None):
    """  Runs the cmd and operates on the response based on return_type.
    return_types:
        check_string        Returns True if expected_text occurs in response of the cmd, plus the full full subprocess run structure
            check_line_text     If provided, only the first line containing this text is checked
            expected_text       Text that must be found
            not_text            Text that must NOT be found
        cmdrun              Returns True if the cmd return code was 0, plus the full full subprocess run structure
    """

    if user_host_port != "local":
        u_h, _, port = split_user_host_port(user_host_port)
        cmd = ["ssh", u_h, "-p" + port, "-o", "ConnectTimeout=1", "-T"] + cmd

    for nTry in range (getcfg('nRetries')):
        try:
            logging.debug(f"cmd_check subprocess command try {nTry+1}: <{cmd}>")
            # runtry = subprocess.run(cmd, capture_output=True, text=True)  # Py 3.7+
            runtry = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)   #Py3.6 requires old-style params
        except Exception as e:
            logging.error(f"ERROR:  subprocess.run of cmd <{cmd}> failed.\n  {e}")
            return False, None

        if return_type == "check_string":
            if check_line_text is None:
                text_to_check = runtry.stdout
            else:
                text_to_check = ""
                for line in runtry.stdout.split("\n"):
                    if check_line_text in line:
                        text_to_check = line
                        break
                
            if expected_text in text_to_check:
                if not_text is not None:
                    if not_text not in text_to_check:
                        return True, runtry
                else:
                    return True, runtry
            else:
                if nTry == getcfg('nRetries')-1:
                    return False, runtry

        elif return_type == "cmdrun":
            if runtry.returncode == 0:
                return True, runtry
            elif nTry == getcfg('nRetries')-1:
                return False, runtry

        else:
            _msg = f"Invalid return_type <{return_type}> passed to cmd_check"
            logging.error (f"ERROR:  {_msg}")
            raise ValueError (_msg)
        time.sleep (timevalue(getcfg('RetryInterval')).seconds)


IP_RE = re.compile(r"[\d]+\.[\d]+\.[\d]+\.[\d]+")   # Validity checks are rudimentary
HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")

def check_LAN_access():
    """Check for basic access to another reliable host on the LAN, typically the router/gateway.
    Used as an execution gate for all non-local items on each RecheckInterval.

    Requires "Gateway <IP address or hostname>" definition in the config file.

    Returns True if the "Gateway" host can be pinged, else False.
    """

    ip_or_hostname = getcfg("Gateway", False)
    if not ip_or_hostname:
        logging.error (f"  ERROR:  PARAMETER 'Gateway' NOT DEFINED IN CONFIG FILE - Aborting.")
        sys.exit(1)

    if (IP_RE.match(ip_or_hostname) is None)  and  (HOSTNAME_RE.match(ip_or_hostname) is None):
        logging.error (f"  ERROR:  INVALID IP ADDRESS OR HOSTNAME <{ip_or_hostname}> - Aborting.")
        sys.exit(1)

    pingrslt = cmd_check(["ping", "-c", "1", "-W", "1", getcfg("Gateway")], user_host_port="local", return_type="cmdrun")
    if pingrslt[0]:
        return True
    else:
        return False


def next_summary_timestring():
    """Calculate timestring of next summary.
    SummaryDays			1 2 3 4 5 6 7	# Days of week: 1 = Monday, 7 = Sunday.  = 0 or comment out to disable summaries
    SummaryTime			9:45		    # 24 hour clock
    NOTE:  May be off by 1 hour over a DTS changes.
    Don't define SummaryDays to disable summaries.
    """
    if getcfg("SummaryDays", None) is None:
        logging.debug(f"SummaryDays not defined.  Summaries are disabled.")
        return None
    try:
        target_hour   = int(getcfg("SummaryTime","").split(":")[0])
        target_minute = int(getcfg("SummaryTime","").split(":")[1])
        today_day_num = datetime.datetime.today().isoweekday()
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        next_summary = now + datetime.timedelta(days=30)
        xx = getcfg("SummaryDays")
        days = [xx]  if type(xx) is int  else [int(day) for day in xx.split()]
        for daynum in days:
            offset_num_days = daynum - today_day_num
            if offset_num_days < 0:
                offset_num_days += 7
            plus_day =  now + datetime.timedelta(days=offset_num_days)
            with_time = plus_day.replace(hour=target_hour, minute=target_minute)
            if with_time < datetime.datetime.now():
                with_time = with_time + datetime.timedelta(days=7)
            if with_time < next_summary:
                next_summary = with_time
        logging.debug(f"Next summary:  {next_summary}")
        return next_summary
    except Exception as e:
        _msg = f"SummaryDays <{getcfg('SummaryDays','')}> or SummaryTime <{getcfg('SummaryTime','')}> settings could not be parsed\n  {e}"
        logging.error(f"ERROR:  {_msg}")
        sys.exit(1)
        # raise ValueError (_msg) from None
        