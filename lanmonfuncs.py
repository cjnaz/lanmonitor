#!/usr/bin/env python3
"""LAN monitor support functions
"""

# __version__ = "V1.0a 210515"

#==========================================================
#
#  Chris Nelson, 2021
#
# V1.1  210523  cmd timeout tweaks
# V1.0  210507  V1.0
# V1.0a 210515  Set timeouts to 1s for ping and 5s for ssh commands on remotes
#
# Changes pending
#   
#==========================================================

import sys
import os.path
import subprocess
import datetime
import time
import re
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../funcs3/'))
from funcs3 import logging, getcfg, snd_email, snd_notif

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


def convert_time (timeX):
    """ Given time value term such as 90s, 15m, 20h, 3d, 2w return int seconds and units.
        <1h> returns (3600, "hours")
    If no units suffix, the value is interpreted as secs.
        <90> returns (90, "secs ")
    """
    if type(timeX) is int:
        return timeX, "secs "           # Case Int
    try:
        return int(timeX), "secs "      # Case Str without units
    except:
        pass
    try:                                # Case Str with units
        time_value = int(timeX[:-1])
        time_unit =  timeX[-1:].lower()
        if time_unit == "s":
            return time_value, "secs "
        if time_unit == "m":
            return time_value * 60, "mins "
        if time_unit == "h":
            return time_value * 60*60, "hours"
        if time_unit == "d":
            return time_value * 60*60*24, "days "
        if time_unit == "w":
            return time_value * 60*60*24*7, "weeks"
        raise ValueError(f"Illegal time units <{time_unit}>")
    except Exception as e:
        logging.error (f"ERROR:  Could not convert time value <{timeX}>\n  {e}")
        raise


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
                logging.error(f"ERROR:  {_msg}")
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
        time.sleep (convert_time(getcfg('RetryInterval'))[0])


have_access_dict = {}

def have_access(user_host_port):
    """If user_host_port != "local" then check ping and ssh access to the host.
    Remember passing result and avoid redoing the ping and ssh tests on later checks.
    If ping/ssh tests fail they will be retried if referenced in a later monitored item.
    The dictionary is cleared on each RecheckInterval in the lanmonitor main code.
    ping or ssh access fails return a tuple of (False, error_message_string).
    (True, "") is returned if local or if ping and ssh tests pass for non-local host.

    NOTE that this optimization can result in confusion:
        if access once passed then fails the plugin will be called and may flag an error
        while the actual problem is no access.
    """
    user_host_port = user_host_port.lower()
    if user_host_port == "local":
        return (True, "")
    if user_host_port in have_access_dict:
        return (True, "")

    _, host, _ = split_user_host_port(user_host_port)
    if host != "local":     # Check for remote access if non-local
        pingrslt = cmd_check(["ping", "-c", "1", "-W", "1", host], user_host_port="local", return_type="cmdrun")
        if not pingrslt[0]:
            return (False, "HOST CANNOT BE REACHED")
        else:
            sshrslt = cmd_check(["echo", "hello"], user_host_port=user_host_port, return_type="cmdrun")
            if "Connection refused" in sshrslt[1].stderr:
                return (False, f"SSH CONNECTION REFUSED <{user_host_port}>")
            # if "The authenticity of host" in sshrslt[1].stdout:       # Never happens thru the script, only interactive
            #     return (False, f"SSH CONNECTION NOT APPROVED.  ssh to <{user_host_port}> manually first.")

    have_access_dict[user_host_port] = True
    return (True, "")


def next_summary_timestring():
    """Calculate timestring of next summary.
    SummaryDays			0 1 2 3 4 5 6	# Days of week.  0 = Sunday
    SummaryTime			9:45		    # 24 hour clock
    NOTE:  May be off by 1 hour over a DTS changes.
    """
    try:
        target_hour   = int(getcfg("SummaryTime","").split(":")[0])
        target_minute = int(getcfg("SummaryTime","").split(":")[1])
        today_day_num = datetime.datetime.today().isoweekday()    # Sunday = 0, Saturday = 6
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        next_summary = now + datetime.timedelta(days=30)
        for daynum in getcfg("SummaryDays").split():
            offset_num_days = int(daynum) - today_day_num
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
        raise ValueError (_msg) from None
        