#!/usr/bin/env python3
"""LAN monitor support functions
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.1 230320 - Added cfg param ssh_timeout, fixed cmd_check command fail retry bug, 
#   cmd_check returns RTN_PASS, RTN_FAIL, RTN_WARNING (for remote ssh access issues)
# 3.0 230301 - Packaged
# 1.4 221120 - Summaries optional if SummaryDays is not defined.
# 1.3 220420 - Incorporated funcs3 timevalue and retime (removed convert_time)
# 1.2a 220223 - Bug fix in summary day calculation
# 1.2 210605 - Reworked have_access check to check_LAN_access logic.
# 1.1 210523 - cmd timeout tweaks
# 1.0 210507 - V1.0
# 1.0a 210515 - Set timeouts to 1s for ping and 5s for ssh commands on remotes
#   
#==========================================================

import sys
import subprocess
import datetime
import time
import re

from cjnfuncs.core import logging
from cjnfuncs.timevalue import timevalue

import lanmonitor.globvars as globvars


# Configs / Constants
NOTIF_SUBJ = "LAN Monitor"
RTN_PASS     = 0
RTN_WARNING  = 1
RTN_FAIL     = 2
RTN_CRITICAL = 3


#=====================================================================================
#=====================================================================================
#  s p l i t _ u s e r _ h o s t _ p o r t
#=====================================================================================
#=====================================================================================
USER_HOST_FORMAT = re.compile(r"[\w.-]+@([\w.-]+)$")
USER_HOST_PORT_FORMAT = re.compile(r"[\w.-]+@([\w.-]+):([\d]+)$")

def split_user_host_port(u_h_p):
    """
    ## split_user_host_port (u_h_p) - Handle variations in passed-in user_host_port
    
    ### Parameter
    `u_h_p`
    - Str in the form of - `local`, `user@host`, or `user@host:port`
    - Port number 22 is default
    - `local` indicates the current host

    ### Returns
    - 3-tuple
      - user@host (without port), or `local`
      - host (without user or port), or `local`
      - port number
    
    ### Examples
    ```
        "xyz@host15:4455" returns:
            ("xyz@host15", "host15", "4455")
        "xyz@host15" returns:
            ("xyz@host15", "host15", "22")  (the default port is "22" for ssh)
        "local" returns:
            ("local", "local", "")
    ```
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
    return (user_host_noport, host, port)


#=====================================================================================
#=====================================================================================
#  c m d _ c h e c k
#=====================================================================================
#=====================================================================================
def cmd_check(cmd, user_host_port, return_type=None, check_line_text=None, expected_text=None, not_text=None):
    """
    ## cmd_check (cmd, user_host_port, return_type=None, check_line_text=None, expected_text=None, not_text=None) - Runs the cmd and operates on the response based on return_type

    ### Parameters
    `cmd`
    - Command to be passed to subprocess() in list form

    `user_host_port`
    - Str for the target machine to execute cmd on.  Port optional (default 22).  `local`
    indicates run the cmd on the local machine.

    `return_type`
    - "cmdrun" or "check_string"
    - If "cmdrun" then the `cmd` execution status (`True` if no error) and subprocess
    return structure is returned.
    - If "check_string" then the following parameters are used to evaluate the `cmd` response.
   
    `check_line_text` (default None)
    - A qualifier for which line of the `cmd` response to look for `expected_text` and/or `not_text`
    - If provided, only the first line containing this text is checked.  If not provided then
    all lines of the `cmd` response are checked.

    `expected_text` (default None)
    - Text that must be found

    `not_text`  (default None)
    - Text that must NOT be found
    
    ### cfg dictionary param
    `ssh_timeout` (default 1s)
    - Timeout for completion of all operations on remote hosts (a global setting)

    ### Returns
    - 2-tuple of (success_status, subprocess run return structure)
    - If `user_host_port` is a remote host but a ssh connection was not successful then 
    success_status = RTN_WARNING.
    - If `return_type` = "cmdrun" then success_status = RTN_PASS if the subprocess run returns a 
    passing status (0), else success_status = RTN_FAIL.
    - If `return_type` = "check_string" then success_status = RTN_PASS if the `cmd` stdout response
    contains `expected_text` and not `not_text` (response line qualified by `check_line_text`),
    else success_status = RTN_FAIL.
    """

    if return_type not in ["check_string", "cmdrun"]:
        _msg = f"Invalid return_type <{return_type}> passed to cmd_check"
        logging.error (f"ERROR:  {_msg}")
        raise ValueError (_msg)

    if user_host_port != "local":
        u_h, host, port = split_user_host_port(user_host_port)
        ct = str(int((timevalue(globvars.config.getcfg("ssh_timeout", "1s")).seconds)))
        cmd = ["ssh", u_h, "-p" + port, "-o", "ConnectTimeout=" + ct, "-T"] + cmd

    for nTry in range (globvars.config.getcfg('nRetries')):
        try:
            logging.debug(f"cmd_check command try {nTry+1}: <{cmd}>")
            # runtry = subprocess.run(cmd, capture_output=True, text=True)  # Py 3.7+
            runtry = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)   #Py3.6 requires old-style params
            # logging.warning (f"cmd Try {nTry+1} - {runtry.returncode} - <{runtry.stderr}> - {cmd}")
        except Exception as e:
            logging.error(f"ERROR:  subprocess.run of cmd <{cmd}> failed.\n  {e}")
            continue

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
                        return (RTN_PASS, runtry)
                else:
                    return (RTN_PASS, runtry)

        elif return_type == "cmdrun":
            if runtry.returncode == 0:
                return (RTN_PASS, runtry)

        time.sleep (timevalue(globvars.config.getcfg('RetryInterval')).seconds)

    if user_host_port == "local":
        return (RTN_FAIL, runtry)
    
    logging.debug(f"cmd_check command failed on remote system - attempting simple ssh connection to {u_h}")
    simplessh = ["ssh", u_h, "-p" + port, "-o", "ConnectTimeout=" + ct, "-T", "echo", "hello"]

    for nTry in range (globvars.config.getcfg('nRetries')):
        try:
            logging.debug(f"cmd_check simplessh try {nTry+1}: <{simplessh}>")
            # runtry = subprocess.run(cmd, capture_output=True, text=True)  # Py 3.7+
            simplessh_try = subprocess.run(simplessh, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)   #Py3.6 requires old-style params
            # logging.warning (f"ssh Try {nTry+1} - {simplessh_try.returncode} - <{simplessh_try.stderr}> - {simplessh}")
            if simplessh_try.returncode == 0:       # ssh access works - return original cmd fail info
                return (RTN_FAIL, runtry)
        except Exception as e:
            logging.error(f"ERROR:  subprocess.run of cmd <{simplessh}> failed.\n  {e}")
            continue

    return (RTN_WARNING, simplessh_try)


#=====================================================================================
#=====================================================================================
#  c h e c k _ L A N _ a c c e s s
#=====================================================================================
#=====================================================================================
IP_RE = re.compile(r"[\d]+\.[\d]+\.[\d]+\.[\d]+")   # Validity checks are rudimentary
HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")

def check_LAN_access(host=None):
    """
    ## check_LAN_access (host=None) - Check for basic access to another reliable host on the LAN

    Reliable access to another host on the network, such as a router/gateway, is used
    as a gate for checking items on other hosts on each RecheckInterval.  

    Requires "Gateway <IP address or hostname>" definition in the config file if `host` is
    not provided in the call.

    ### Parameter

    `host` (default None)
    - A resolvable hostname or IP address.  If not provided then config `Gateway` is used.

    ### Returns
    - Returns True if the `host` or config `Gateway` host can be pinged, else False.
    """

    ip_or_hostname = globvars.config.getcfg("Gateway", host)
    if not ip_or_hostname:
        logging.error (f"  ERROR:  PARAMETER 'Gateway' NOT DEFINED IN CONFIG FILE - Aborting.")
        sys.exit(1)

    if (IP_RE.match(ip_or_hostname) is None)  and  (HOSTNAME_RE.match(ip_or_hostname) is None):
        logging.error (f"  ERROR:  INVALID IP ADDRESS OR HOSTNAME <{ip_or_hostname}> - Aborting.")
        sys.exit(1)

    pingrslt = cmd_check(["ping", "-c", "1", "-W", "1", globvars.config.getcfg("Gateway")], 
                         user_host_port="local", return_type="cmdrun")
    if pingrslt[0] == RTN_PASS:
        return True
    else:
        return False


#=====================================================================================
#=====================================================================================
#  n e x t _ s u m m a r y _ t i m e s t r i n g
#=====================================================================================
#=====================================================================================
def next_summary_timestring():
    """
    ## next_summary_timestring () - Calculate the datetime timestring of next summary

    Example config file items
    ```
        SummaryDays   1 2 3 4 5 6 7  # Days of week: 1 = Monday, 7 = Sunday.  = 0 or comment out to disable summaries
        SummaryTime   9:45           # 24 hour clock
    ```

    - NOTE:  May be off by 1 hour over a DTS changes.
    - Don't define SummaryDays to disable summaries.

    ### Returns
    - datetime of next summary
    """
    if globvars.config.getcfg("SummaryDays", None) is None:
        logging.debug(f"SummaryDays not defined.  Summaries are disabled.")
        return None
    try:
        target_hour   = int(globvars.config.getcfg("SummaryTime","").split(":")[0])
        target_minute = int(globvars.config.getcfg("SummaryTime","").split(":")[1])
        today_day_num = datetime.datetime.today().isoweekday()
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        next_summary = now + datetime.timedelta(days=30)
        xx = globvars.config.getcfg("SummaryDays")
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
        _msg = f"SummaryDays <{globvars.config.getcfg('SummaryDays','')}> or SummaryTime <{globvars.config.getcfg('SummaryTime','')}> settings could not be parsed\n  {e}"
        logging.error(f"ERROR:  {_msg}")
        sys.exit(1)
        # raise ValueError (_msg) from None
        