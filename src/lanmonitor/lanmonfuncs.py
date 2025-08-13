#!/usr/bin/env python3
"""LAN monitor support functions
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 3.5 250728 - Fabric/paramiko incorporation
# 3.3 240805 - Reworked debug level logging in cmd_check, Added cmd_timeout for each monitored item.
# 3.1 230320 - Added cfg param SSH_timeout, fixed cmd_check command fail retry bug, 
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
import asyncio
import threading

import asyncssh

from cjnfuncs.core import logging, set_logging_level, restore_logging_level, ConfigError
from cjnfuncs.rwt  import run_with_timeout
from cjnfuncs.timevalue import timevalue
import lanmonitor.globvars as globvars


# Configs / Constants
NOTIF_SUBJ = "LAN Monitor"
RTN_PASS     =          0
RTN_WARNING  =          1
RTN_FAIL     =          2
RTN_CRITICAL =          3

NTRIES =                2           # Default value.  May be set in config with nTries
RETRY_INTERVAL =        '0.5s'      # Default value.  May be set in config with RetryInterval
SSH_TIMEOUT =           '1.0s'      # Default value.  May be set in config with SSH_timeout
GATEWAY_TIMEOUT =       '1.0s'      # Default value.  May be set in config with Gateway_timeout

CONNECTION_TIMEOUT_DEFAULT = 2.0       # Connection attempt timeout
CONNECTION_NTRIES_DEFAULT = 2
CONNECTION_RETRY_INTERVAL_DEFAULT = 0.5

COMMAND_MAX_CONSECUTIVE_TIMEOUTS_DEFAULT = 4   # At this count, close/delete the conn
COMMAND_NTRIES_DEFAULT = 2
COMMAND_RETRY_INTERVAL_DEFAULT = 0.5


RTNCODE_TIMEOUT =       254
RTNCODE_ERROR =         253
RTNCODE_REMOTE_CONNECT_ERROR= 252


#=====================================================================================
#=====================================================================================
#  c m d _ c h e c k
#=====================================================================================
#=====================================================================================
def cmd_check(cmd, user_host_port, return_type, cmd_timeout, check_line_text=None, expected_text=None, not_text=None):
    """
    ## cmd_check (cmd, user_host_port, return_type, cmd_timeout, check_line_text=None, expected_text=None, not_text=None) - Runs the cmd and operates on the response based on return_type

    The `cmd` is executed by a call to fabric.local() if `user_host_port` is `local`, or via an ssh connection by
    fabric.run() if `user_host_port` is a remote host.
    If there is no exception and the executed `cmd` returns an exit code = 0 then cmd_check checks the
    run response (stdout) per the `return_type` selection.  Finally, a tuple of `(success_status, subprocess.CompletedProcess structure)`
    is returned.  

    The total execution time of a failing local cmd_check call can be as long as:

        nTries*cmd_timeout + (nTries-1)*RetryInterval

    For cmd_check calls on remote systems, the simple ssh access check can add this additional execution time:

        nTries*SSH_timeout 

    ### Args
    `cmd`  (str or list)
    - Command to be passed to fabric.run() or fabric.local() in list (eg: ['echo', 'hello']) or str (eg: 'echo hello') form
    - The `cmd` may use `~` user home expansion and `?` and `*` wildcard expansion.
    - The `cmd` may also use `|` pipes and `>` redirection
    - The `cmd` execution must have a passing (0) exit code else it will be retried and result in a 
      RTN_FAIL `success_status`.  An exception raised by the `cmd` run will also cause retries.

    `user_host_port`  (str)
    - Target machine to execute `cmd` on, eg: 'me@testhost2:2222'.  The port number is optional (default 22).
    - `local` indicates run `cmd` on the local machine

    `cmd_timeout`  (float, value in seconds)
    - timeout value used when executing `cmd`

    `return_type`  (str - either 'cmdrun' or 'check_string')
    - If `return_type` = 'cmdrun' then RTN_PASS (`cmd` exit code = 0) or RTN_FAIL (`cmd` exit code > 0) and
    the `CompletedProcess` structure is returned.
    - If `return_type` = 'check_string':
      - If the `cmd` run exit code = 0 then the following args are used to evaluate the `CompletedProcess.stdout` field.
        `success_status` is set to RTN_PASS or RTN_FAIL per the string checks, and returned with the
        `CompletedProcess` structure.  String check failures are noted in `CompletedProcess.stderr`.
      - If the `cmd` run exit code > 0 then RTN_FAIL and the `CompletedProcess` structure is returned.
   
    `check_line_text` (str, default None)
    - A qualifier for which line of `CompletedProcess.stdout` to look for `expected_text` and/or `not_text`
    - If provided, only the first line containing this text is checked.  If not provided then
    all lines of the `CompletedProcess.stdout` are checked.

    `expected_text` (str, default None)
    - Text that must be found in the `check_line_text` (or all of `CompletedProcess.stdout`)

    `not_text`  (str, default None)
    - Text that must NOT be found in the `check_line_text` (or all of `CompletedProcess.stdout`)
    
    ### cfg dictionary params
    `nTries` (int, default 2)
    - Total number of times to attempt to execute the `cmd` if it returns an exit code > 0 or raises an exception

    `RetryInterval` (float, default 0.5s)
    - Wait time between `cmd` nTries

    `SSH_timeout` (int, default 1s)
    - Timeout used for SSH connections to remote hosts.

    ### Returns
    - 2-tuple of `(success_status, subprocess.CompletedProcess())`
      - `success_status` values:
        - `RTN_PASS` - the `cmd` run exited with exit code = 0.  If `return_type`='check_string' then checks pass.  Any `cmd` output is in `CompletedProcess.stdout`.
        - `RTN_FAIL` - the `cmd` run exited with exit code > 0, or an exception was raised, or `return_type`='check_string' checks fail.
        `CompletedProcess.stderr` contains the failure data.
        - `RTN_WARNING` - only for execution on a remote host, indicates an SSH connection failure

      - If `return_type` = 'check_string':  `success_status` = 'RTN_PASS' if the `cmd` stdout response contains `expected_text` and not `not_text` 
      (response line qualified by `check_line_text`), else `success_status` = 'RTN_FAIL'.

      - The returned `CompletedProcess` structure contains these fields:
        - `args` - the command string executed
        - `returncode` - integer command execution status
            - 0:  `cmd` executed successfully
            - \>0: `cmd`-specific error exit code
            - RTNCODE_REMOTE_TIMEOUT (252): Connection timeout to a remote host
            - RTNCODE_ERROR (253): General exception 
            - RTNCODE_TIMEOUT (254): Timeout during `cmd` execution 
        - `stdout` - holds any text from a passing `cmd` execution
        - `stderr` - holds any info on `cmd` execution errors and exceptions.  '\\n's are replaced with ' '.

    - A ValueError exception is raised if the call to cmd_check has errors, such as invalid `return_type` or `user_host_port`.

    ### Behaviors and rules
    - If an exception is raised when trying to execute the `cmd` then the `CompletedProcess.returncode` field is set to
    RTNCODE_TIMEOUT (254), RTNCODE_ERROR (253), or RTNCODE_REMOTE_TIMEOUT (252), and the `CompletedProcess.stderr` field carries the details. 
    If used, these codes should be imported from this module.
    - When unable to connect to a known host (DNS resolves) the failure information can vary, perhaps based on the `SSH_timeout` setting, including:
      - (RTN_WARNING, CompletedProcess(returncode=252, stderr='Host <me@testhostx> connection failed:  TimeoutError: timed out'))
      - (RTN_WARNING, CompletedProcess(returncode=253, stderr='Host <me@testhostx> connection failed:  timeout: timed out'))
      - (RTN_WARNING, CompletedProcess(returncode=253, stderr='Host <me@testhostx> connection failed:  NoValidConnectionsError: [Errno None] Unable to connect to port 22 on ...'))
    """

    global host_connections

    if return_type not in ['check_string', 'cmdrun']:
        _msg = f"Invalid return_type <{return_type}> passed to cmd_check"
        logging.error (f"ERROR:  {_msg}")
        raise ValueError (_msg)

    if isinstance(cmd, list):
        cmd = ' '.join(cmd)

    # connection_timeout = timevalue(globvars.config.getcfg('Connection_timeout', CONNECTION_TIMEOUT_DEFAULT)).seconds  # As specified in top-level config - legacy
    # command_ntries = globvars.config.getcfg('nTries', NTRIES)   # legacy

    
    # Construct the uhp             # TODO move connection var assignments into only new connection flow
    if '@' in user_host_port  or  ';' in '@' in user_host_port:
        user, host, port = split_user_host_port(user_host_port)
        host_section = ''
        # connection_timeout = CONNECTION_TIMEOUT_DEFAULT
        # connection_nTries = CONNECTION_NTRIES_DEFAULT
        # connection_retry_interval = CONNECTION_RETRY_INTERVAL_DEFAULT

        # command_ntries = COMMAND_NTRIES_DEFAULT
        # command_retry_interval = COMMAND_RETRY_INTERVAL_DEFAULT
        # command_max_consecutive_timeouts = COMMAND_MAX_CONSECUTIVE_TIMEOUTS_DEFAULT
        # env = {}
    else:   # Hostname only provided.  Get params from config, with these fallbacks
        if user_host_port not in globvars.config.sections():
            raise ConfigError (f"Host section <{user_host_port}> not in config.")
        host_section = user_host_port
        host =                  globvars.config.getcfg('hostname',                  section=host_section)
        user =                  globvars.config.getcfg('username',                  section=host_section)
        port =                  str(globvars.config.getcfg('port', '22',            section=host_section))
        # connection_timeout =    timevalue(globvars.config.getcfg('Connection_timeout', CONNECTION_TIMEOUT_DEFAULT, section=host_section)).seconds
        # connection_nTries =     globvars.config.getcfg('Connection_nTries', CONNECTION_NTRIES_DEFAULT,   section=host_section)
        # connection_retry_interval =     timevalue(globvars.config.getcfg('Connection_retry_interval', CONNECTION_RETRY_INTERVAL_DEFAULT,   section=host_section)).seconds

        # command_ntries =        globvars.config.getcfg('Command_nTries', COMMAND_NTRIES_DEFAULT,   section=host_section)
        # command_retry_interval= timevalue(globvars.config.getcfg('Command_retry_interval', COMMAND_RETRY_INTERVAL_DEFAULT,   section=host_section)).seconds
        # command_max_consecutive_timeouts =     globvars.config.getcfg('Command_max_consecutive_timeouts', COMMAND_MAX_CONSECUTIVE_TIMEOUTS_DEFAULT,   section=host_section)
        # env  =                  globvars.config.getcfg('env',      {},              section=host_section)

    uhp = f"{user}@{host}:{port}"

    error_msg = ''

    # Get host SSH connection
    if uhp not in host_connections.connections:
        connection_timeout =    timevalue(globvars.config.getcfg('Connection_timeout', CONNECTION_TIMEOUT_DEFAULT, section=host_section)).seconds
        connection_nTries =     globvars.config.getcfg('Connection_nTries', CONNECTION_NTRIES_DEFAULT,   section=host_section)
        connection_retry_interval =     timevalue(globvars.config.getcfg('Connection_retry_interval', CONNECTION_RETRY_INTERVAL_DEFAULT,   section=host_section)).seconds

        command_ntries =        globvars.config.getcfg('Command_nTries', COMMAND_NTRIES_DEFAULT,   section=host_section)
        command_retry_interval= timevalue(globvars.config.getcfg('Command_retry_interval', COMMAND_RETRY_INTERVAL_DEFAULT,   section=host_section)).seconds
        command_max_consecutive_timeouts =     globvars.config.getcfg('Command_max_consecutive_timeouts', COMMAND_MAX_CONSECUTIVE_TIMEOUTS_DEFAULT,   section=host_section)
        env  =                  globvars.config.getcfg('env',      {},              section=host_section)
        try:
            host_connections.new_connection(uhp,
                    connection_timeout= connection_timeout,
                    connection_nTries=  connection_nTries,
                    connection_retry_interval=    connection_retry_interval) #  TODO password
                    # command_ntries =    command_ntries,
                    # max_consec_timeouts=max_consecutive_timeouts)
            
            host_connections.connections[uhp]['command_ntries'] = command_ntries
            host_connections.connections[uhp]['command_retry_interval'] = command_retry_interval
            host_connections.connections[uhp]['command_max_consecutive_timeouts'] = command_max_consecutive_timeouts
            host_connections.connections[uhp]['env'] = env
            host_connections.connections[uhp]['consecutive_command_timeouts'] = 0
                    # conn = self.connections[uhp] = {'ssh_conn': ssh_conn,
                    #                                 'consecutive_command_timeouts': 0,
                    #                                 'max_consec_timeouts': max_consec_timeouts}

        except Exception as e:
            error_msg = f"Exception while connecting to {uhp}: {type(e).__name__} - "  + str(e).replace('\n',' ')
            logging.debug(error_msg)
            # logging.exception(error_msg)
            return (RTN_WARNING, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_CONNECT_ERROR, stdout='', stderr=error_msg))
    
    # # Construct the uhp             # TODO move connection var assignments into only new connection flow
    # if '@' in user_host_port  or  ';' in '@' in user_host_port:
    #     user, host, port = split_user_host_port(user_host_port)
    #     connection_timeout = CONNECTION_TIMEOUT_DEFAULT
    #     connection_nTries = CONNECTION_NTRIES_DEFAULT
    #     connection_retry_interval = CONNECTION_RETRY_INTERVAL_DEFAULT

    #     command_ntries = COMMAND_NTRIES_DEFAULT
    #     command_retry_interval = COMMAND_RETRY_INTERVAL_DEFAULT
    #     command_max_consecutive_timeouts = COMMAND_MAX_CONSECUTIVE_TIMEOUTS_DEFAULT
    #     env = {}
    # else:   # Hostname only provided.  Get params from config, with these fallbacks
    #     if user_host_port not in globvars.config.sections():
    #         raise ConfigError (f"Host section <{user_host_port}> not in config.")
    #     host_section = user_host_port
    #     host =                  globvars.config.getcfg('hostname',                  section=host_section)
    #     user =                  globvars.config.getcfg('username',                  section=host_section)
    #     port =                  str(globvars.config.getcfg('port', '22',            section=host_section))
    #     connection_timeout =    timevalue(globvars.config.getcfg('Connection_timeout', CONNECTION_TIMEOUT_DEFAULT, section=host_section)).seconds
    #     connection_nTries =     globvars.config.getcfg('Connection_nTries', CONNECTION_NTRIES_DEFAULT,   section=host_section)
    #     connection_retry_interval =     timevalue(globvars.config.getcfg('Connection_retry_interval', CONNECTION_RETRY_INTERVAL_DEFAULT,   section=host_section)).seconds

    #     command_ntries =        globvars.config.getcfg('Command_nTries', COMMAND_NTRIES_DEFAULT,   section=host_section)
    #     command_retry_interval= timevalue(globvars.config.getcfg('Command_retry_interval', COMMAND_RETRY_INTERVAL_DEFAULT,   section=host_section)).seconds
    #     command_max_consecutive_timeouts =     globvars.config.getcfg('Command_max_consecutive_timeouts', COMMAND_MAX_CONSECUTIVE_TIMEOUTS_DEFAULT,   section=host_section)
    #     env  =                  globvars.config.getcfg('env',      {},              section=host_section)

    # uhp = f"{user}@{host}:{port}"

    # error_msg = ''

    # # Get host SSH connection
    # if uhp not in host_connections.connections:
    #     try:
    #         host_connections.new_connection(uhp,
    #                 connection_timeout= connection_timeout,
    #                 connection_nTries=  connection_nTries,
    #                 connection_retry_interval=    connection_retry_interval) #  TODO password
    #                 # command_ntries =    command_ntries,
    #                 # max_consec_timeouts=max_consecutive_timeouts)
            
    #         host_connections.connections[uhp]['command_ntries'] = command_ntries
    #         host_connections.connections[uhp]['command_retry_interval'] = command_retry_interval
    #         host_connections.connections[uhp]['command_max_consecutive_timeouts'] = command_max_consecutive_timeouts
    #         host_connections.connections[uhp]['env'] = env
    #         host_connections.connections[uhp]['consecutive_command_timeouts'] = 0
    #                 # conn = self.connections[uhp] = {'ssh_conn': ssh_conn,
    #                 #                                 'consecutive_command_timeouts': 0,
    #                 #                                 'max_consec_timeouts': max_consec_timeouts}

    #     except Exception as e:
    #         error_msg = f"Exception while connecting to {uhp}: {type(e).__name__} - "  + str(e).replace('\n',' ')
    #         logging.debug(error_msg)
    #         # logging.exception(error_msg)
    #         return (RTN_WARNING, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_CONNECT_ERROR, stdout='', stderr=error_msg))

    # Run the command, with retries
    for nTry in range (host_connections.connections[uhp]['command_ntries']):

        if nTry > 0: #host_connections.connections[uhp]['command_ntries']-1:
            time.sleep (host_connections.connections[uhp]['command_retry_interval'])

        try:
            logging.debug(f"cmd try {nTry+1} on <{uhp}>:  <{cmd}>")

            run_try = host_connections.run_command(
                command =       cmd,
                uhp =           uhp,
                command_timeout=cmd_timeout) #,
                # env =           env)

            run_result = subprocess.CompletedProcess(
                args=           cmd,
                returncode=     run_try.exit_status,
                stdout=         run_try.stdout.strip(),
                stderr=         run_try.stderr.strip().replace('\n',' '))

            if run_result.returncode > 0:           # no exception, but non-passing result
                error_msg = run_result.stderr
                logging.debug(f"cmd try {nTry+1} failed (returncode {run_result.returncode}):  <{error_msg}>")
            # logging.debug(f"cmd_check subprocess.run returned <{run_try}>")      # Uncomment for debug.  stdout can be huge.

        except TimeoutError as e:
            error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
            run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_TIMEOUT, stdout='', stderr=error_msg)
            logging.debug(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")
            continue

        except ConnectionError as e:
            # Raised in run_command() on excessive command timeouts or connection not defined (should not happen)
            error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
            run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_CONNECT_ERROR, stdout='', stderr=error_msg)
            logging.debug(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")
            return (RTN_WARNING, run_result)

        except Exception as e:
            error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
            run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg)
            logging.debug(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")
            # logging.exception(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")
            continue


        if return_type == 'check_string':

            # Isolate text line to check
            if check_line_text is None:
                text_to_check = run_result.stdout
            else:
                text_to_check = ''
                for line in run_result.stdout.split('\n'):
                    if check_line_text in line:
                        text_to_check = line
                        break
            if text_to_check == '':
                _msg = "No text_to_check!"

            else:
                # Check for expected text
                if expected_text is not None:
                    if expected_text in text_to_check:
                        if not_text is not None:
                            # But not not_text
                            if not_text not in text_to_check:
                                return (RTN_PASS, run_result)   # check_string expected_text and not_text Pass exit
                            else:
                                _msg = f"not_text <{not_text}> found in text_to_check"
                        return (RTN_PASS, run_result)           # check_string expected_text Pass exit
                    else:
                        _msg = f"expected_text <{expected_text}> not found in text_to_check"
                else:
                    # Check for not_text without expected_text
                    if not_text is not None:
                        if not_text not in text_to_check:
                            return (RTN_PASS, run_result)       # check_string not_text Pass exit
                        else:
                            _msg = f"not_text <{not_text}> found in text_to_check"
                    else:
                        raise ValueError("expected_text and non_text can't both be None")

            run_result.returncode = 1
            run_result.stderr = _msg

        else:   # return_type == 'cmdrun':
            if run_result.returncode == 0:
                return (RTN_PASS, run_result)                   # cmdrun Pass exit


        # if nTry < host_connections.connections[uhp]['command_ntries']-1:
        #     time.sleep (host_connections.connections[uhp]['command_retry_interval'])

        # End of ntries loop

    return (RTN_FAIL, run_result)                               # Fail exit after ntries



#=====================================================================================
#=====================================================================================
#  s p l i t _ u s e r _ h o s t _ p o r t
#=====================================================================================
#=====================================================================================
USER_HOST_FORMAT = re.compile(r"([\w.-]+)@([\w.-]+)$")
USER_HOST_PORT_FORMAT = re.compile(r"([\w.-]+)@([\w.-]+):([\d]+)$")

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
      - user or `local` (cast to lower case)
      - host or `local` (cast to lower case)
      - port number
    
    ### Examples
    ```
        "xyz@host15:4455" returns:
            ("xyz", "host15", "4455")
        "xyz@host15" returns:
            ("xyz", "host15", "22")  (the default port is "22" for ssh)
        "local" returns:
            ("local", "local", "")
    ```
    """
    # user_host_noport = u_h_p.split(':')[0]
    # host = u_h_p
    # port = ''
    u_h_p = u_h_p.lower().strip()
    if u_h_p == 'local':
        return ('local', 'local', '')

    else:
        if ':' not in u_h_p:
            u_h_p += ':22'
    # port = '22'
    # out = USER_HOST_FORMAT.match(u_h_p)
    # if out:
    #     user = out.group(1).lower()
    #     host = out.group(2).lower()
    # else:
        out = USER_HOST_PORT_FORMAT.match(u_h_p)
        if out:
            user = out.group(1).lower()
            host = out.group(2).lower()
            port = out.group(3)
        else:
            _msg = f"Expecting <user@host> or <user@host:port> format, but found <{u_h_p}>."
            # logging.error(f"ERROR:  {_msg}")
            raise ValueError (_msg)
    return (user, host, port)


#=====================================================================================
#=====================================================================================
#  c l a s s   A s y n c S S H M a n a g e r
#=====================================================================================
#=====================================================================================

class AsyncSSHManager:
    def __init__(self, logging_level=logging.WARNING):
        self.connections = {}
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._start_loop, daemon=True)
        self._thread.start()
        asyncssh.set_log_level(logging_level)


    # def new_connection(self, uhp, connection_timeout, ntries_connection, btw_retries_sec, max_consec_timeouts, password=None):
    #     return self.run_coroutine(self._new_connection(uhp, connection_timeout, ntries_connection, btw_retries_sec, max_consec_timeouts, password))


    # async def _new_connection(self, uhp, connection_timeout, ntries_connection, btw_retries_sec, max_consec_timeouts, password):
    def new_connection(self, uhp, connection_timeout, connection_nTries, connection_retry_interval, password=None):
        return self.run_coroutine(self._new_connection(uhp, connection_timeout, connection_nTries, connection_retry_interval, password))


    async def _new_connection(self, uhp, connection_timeout, connection_nTries, connection_retry_interval, password):
        conn = self.connections.get(uhp)    # TODO Allow call if already exists??  cleanup conn

        if not conn:        #  if connection doesn't exist
            for _try in range(1, connection_nTries+1):
                try:
                    logging.debug (f"Connection attempt {_try} to <{uhp}>")
                    user, host, port = split_user_host_port(uhp)
                    ssh_conn = await asyncio.wait_for (asyncssh.connect(host=host,
                                                                        username=user,
                                                                        port=port,
                                                                        password=password,
                                                                        connect_timeout=connection_timeout,
                                                                        keepalive_interval=5,
                                                                        keepalive_count_max=3)
                                                        , timeout=connection_timeout+1)
                    # self.connections[uhp]['ssh_conn'] = ssh_conn
                    self.connections[uhp] = {'ssh_conn': ssh_conn}
                    # conn = self.connections[uhp] = {'ssh_conn': ssh_conn,
                    #                                 'consecutive_command_timeouts': 0,
                    #                                 'max_consec_timeouts': max_consec_timeouts}
                    logging.warning (f"Connection (re)established:  <{uhp}>")
                    break
                    
                except (asyncio.TimeoutError, asyncssh.Error, OSError) as e:
                    # last_exc = e
                    logging.debug (f"Connection attempt {_try} to <{uhp}> FAILED:  {type(e).__name__}: {e}")
                    if _try < connection_nTries:
                        await asyncio.sleep(connection_retry_interval)
                        continue
                    raise ConnectionError(f"Connection to <{uhp}> FAILED after {connection_nTries} attempts: {type(e).__name__}: {e}")


    def run_command(self, command, uhp, command_timeout): #, password=None): #, env={}):
        return self.run_coroutine(self._run_command(command, uhp, command_timeout)) #, password) #, env))


    async def _run_command(self, command, uhp, command_timeout): #, password) #, env):

        conn = self.connections.get(uhp)
        if not conn:
            raise ConnectionError(f"Connection to <{uhp}> unknown")
            # TODO re-get connection?

        ssh_conn = conn['ssh_conn']

        try:
            # result = await asyncio.wait_for(ssh_conn.run(command, env=env), timeout=command_timeout)
            result = await asyncio.wait_for(ssh_conn.run(command), timeout=command_timeout)
            conn['consecutive_command_timeouts'] = 0
            return result
            
        # except (asyncio.TimeoutError, asyncssh.Error, OSError) as e:      # TODO trap other exceptions
        except asyncio.TimeoutError as e:
            logging.debug (f"Command execution on <{uhp}> EXCEPTION:  {type(e).__name__}: {e}")
            conn['consecutive_command_timeouts'] += 1
            if conn['consecutive_command_timeouts'] == conn['command_max_consecutive_timeouts']:
                logging.debug (f"Excessive command timeouts on <{uhp}> - Closing connection")
                await self._close_connection(ssh_conn)
                del self.connections[uhp]
                raise ConnectionError(f"Command execution error on <{uhp}>:  {type(e).__name__}: {e}") # from e
            raise TimeoutError(f"Command execution error on <{uhp}>:  {type(e).__name__}: {e}") # from e

        # Any other exception is passed up
        # except Exception as e:
        #     # last_exc = e
        #     # logging.debug (f"Command execution attempt {_try} to <{uhp}> EXCEPTION:  {type(e).__name__}: {e}")
        #     logging.debug (f"Command execution on <{uhp}> EXCEPTION:  {type(e).__name__}: {e}")
        #     raise (f"Command execution error on <{uhp}>:  {type(e).__name__}: {e}") from e


    def close (self, uhp='all'):
        """Close a specific connection or all"""
        if uhp == 'all':
            self.run_coroutine(self._close_all())
            self.connections.clear()
        else:
            if conn := self.connections.get(uhp):
                self.run_coroutine(self._close_connection(conn['ssh_conn']))
                del self.connections[uhp]


    async def _close_connection(self, ssh_conn):
        if ssh_conn:            # TODO dump if??
            try:
                ssh_conn.close()
                await ssh_conn.wait_closed()    
            except Exception:
                pass


    async def _close_all(self):
        for conn in self.connections:
            await self._close_connection(self.connections[conn]['ssh_conn'])


    def is_connected(self, uhp):
        conn = self.connections.get(uhp)
        if conn:
            ssh_conn = conn['ssh_conn']
            return bool(ssh_conn._transport  and  not ssh_conn._transport._conn_lost)
        return False


    def __repr__(self):
        # Return formatted list of current connections
        xx = "Current connections:\n"
        # print (self.connections_dict)
        for key in self.connections:
            xx += f"  <{key}>\n"
        return xx


    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()


    def run_coroutine(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()


host_connections = AsyncSSHManager() #logging.DEBUG)


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

    ip_or_hostname = globvars.config.getcfg('Gateway', host)
    if not ip_or_hostname:
        logging.error (f"  ERROR:  PARAMETER 'Gateway' NOT DEFINED IN CONFIG FILE - Aborting.")
        sys.exit(1)

    if (IP_RE.match(ip_or_hostname) is None)  and  (HOSTNAME_RE.match(ip_or_hostname) is None):
        logging.error (f"  ERROR:  INVALID IP ADDRESS OR HOSTNAME <{ip_or_hostname}> - Aborting.")
        sys.exit(1)

    gateway_timeout = timevalue(globvars.config.getcfg('Gateway_timeout', GATEWAY_TIMEOUT)).seconds
    pingrslt = cmd_check(['ping', '-c', '1', globvars.config.getcfg('Gateway')],
                         cmd_timeout=gateway_timeout, user_host_port='local', return_type='cmdrun')
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
    if globvars.config.getcfg('SummaryDays', None) is None:
        logging.debug(f"SummaryDays not defined.  Summaries are disabled.")
        return None
    try:
        target_hour   = int(globvars.config.getcfg('SummaryTime','').split(':')[0])
        target_minute = int(globvars.config.getcfg('SummaryTime','').split(':')[1])
        today_day_num = datetime.datetime.today().isoweekday()
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        next_summary = now + datetime.timedelta(days=30)
        xx = globvars.config.getcfg('SummaryDays')
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
        