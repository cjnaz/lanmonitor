#!/usr/bin/env python3
"""LAN monitor support functions
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - asyncssh and invoke incorporation for remote/local command execution in cmd_check, RTN_DISREGARD
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
import invoke

from cjnfuncs.core import logging, ConfigError
from cjnfuncs.timevalue import timevalue, get_next_dt
import lanmonitor.globvars as globvars


# Configs / Constants
NOTIF_SUBJ =                                "LAN Monitor"
RTN_PASS =                                  0
RTN_WARNING =                               1
RTN_FAIL =                                  2
RTN_CRITICAL =                              3
RTN_DISREGARD =                             4

RTNCODE_REMOTE_CONNECTION_DOWN =            250
RTNCODE_COMMAND_TIMEOUT =                   251
RTNCODE_ERROR =                             252
RTNCODE_CONNECT_ATTEMPT_FAILED =            253

RTN_DISREGARD_LOG_INTERVAL =                '1h'
GATEWAY_TIMEOUT_DEFAULT =                   '1.0s'

CONNECTION_TIMEOUT_DEFAULT =                '2.0s'
CONNECTION_NTRIES_DEFAULT =                 2
CONNECTION_RETRY_INTERVAL_DEFAULT =         '0.5s'
CONNECTION_KEEPALIVE_INTERVAL_DEFAULT =     '60s'
CONNECTION_KEEPALIVE_COUNT_MAX_DEFAULT =    3
CONNECTION_COMMAND_MAX_TIMEOUTS_DEFAULT =   4

COMMAND_TIMEOUT_DEFAULT =                   '1.0s'
COMMAND_NTRIES_DEFAULT =                    2
COMMAND_RETRY_INTERVAL_DEFAULT =            '0.5s'



#=====================================================================================
#=====================================================================================
#  c m d _ c h e c k
#=====================================================================================
#=====================================================================================
def cmd_check(cmd, user_host_port, return_type, cmd_timeout, check_line_text=None, expected_text=None, not_text=None):
    """
    ## cmd_check (cmd, user_host_port, return_type, cmd_timeout, check_line_text=None, expected_text=None, not_text=None) - Runs the cmd and operates on the response based on return_type

    The `cmd` is executed by a call to invoke.run() for `local`, or asyncssh.run() for remote connections.
    If there is no exception and the executed `cmd` returns an exit code = 0 then cmd_check checks the
    run response (stdout) per the `return_type` selection.  
    Finally, a tuple of `(success_status, subprocess.CompletedProcess)` is returned.  

    For cmd_check calls on remote hosts the time to establish a remote connection can be as long as below.
    The remote host connection is made once and reused indefinitely, with keepalive managed by asyncssh.
    If the connection is lost it will automatically be reestablished on the next cmd_check call for the specific host.
        Connection_nTries*Connection_timeout + (Connection_nTries-1)*Connection_retry_interval

    The maximum total execution time of a failing cmd_check call can be as long as:
        Command_nTries*cmd_timeout + (Command_nTries-1)*Command_retry_interval


    ### Args
    `cmd`  (str)
    - Command to be passed to invoke.run() or asyncssh.run() in str form (eg: 'echo hello')
    - The `cmd` may use `~` user home expansion and `?` and `*` wildcard expansion for paths
    - The `cmd` may also use `|` pipes and `>` redirection
    - The `cmd` execution must have a passing (0) exit code or it will be retried and result in a 
      RTN_FAIL `success_status`.  An exception raised by the `cmd` run will also cause retries.

    `user_host_port`  (str)
    - Target machine to execute `cmd` on, eg: 'me@testhost2:2222'.  The port number is optional (default 22).
    - Alternately, `user_host_port` may be a reference to a host section in the config file.
    - `local` indicates run `cmd` on the local machine as the current user using invoke.run()

    `cmd_timeout`  (float, value in seconds, or None)
    - If not None, then this timeout value is used when executing `cmd`
    - If None, see the last Behaviors and rules note, below

    `return_type`  (str - either 'cmdrun' or 'check_string')
    - If `return_type` = 'cmdrun' then RTN_PASS (`cmd` exit code = 0) or RTN_FAIL (`cmd` exit code != 0) and
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
    

    ### cfg dictionary params - Optionally defined per remote host:
    `Connection_timeout` (int, float, or timevalue, default 2.0s)
    - Timeout used for asyncssh connections to the remote host

    `Connection_nTries` (int, default 2)
    - Maximum number of attempts to open an asyncssh connection to the remote host

    `Connection_retry_interval` (int, float, or timevalue, default 0.5s)
    - Wait time between remote host `Connection_nTries`

    `Connection_keepalive_interval` (int, float, or timevalue, default 60s)
    - Keepalive ping interval used by asyncssh for the connected remote host

    `Connection_keepalive_count_max` (int, default 3)
    - The remote ssh connection is dropped after this number of failed keepalive pings

    `Connection_command_max_timeouts` (int, default 4)
    - Once reaching this number of consecutive timeouts on a remote connection - possibly
    over successive calls to cmd_check - the remote connection is closed, thus forcing
    an attempted reconnect on the next call.

    `Command_timeout` (int, float, or timevalue, default 1.0s)
    - Max time allowed for a command execution call, if not specified by the monitor item (cmd_check cmd_timeout = None)

    `Command_nTries` (int, default 2)
    - Maximum number of attempts to run `cmd` on the local or remote connection
    - (Note that the `cmd_timeout` is passed in on each call to cmd_check)

    `Command_retry_interval` (int, float, or timevalue, default 0.5s)
    - Wait time between `Command_nTries` on the local or remote connection


    ### Returns
    - 2-tuple of `(success_status, subprocess.CompletedProcess())`
      - `success_status` values:
        - `RTN_PASS` ** (0) - the `cmd` run exited with its exit code = 0.  If `return_type`='check_string' then the checks must also pass.  
        Any `cmd` output is in `stdout`.
        - `RTN_WARNING` (1) - only for execution on a remote host, indicates an initial asyncssh connection failure or exceeding
        `Connection_command_max_timeouts` (potentially a connection problem) and thus triggering the connection to be closed.
        `stderr` contains the failure data.
        - `RTN_FAIL` (2) - the `cmd` run exited with exit code > 0, or an exception was raised, or `return_type`='check_string' and checks fail.
        `stderr` contains the failure data.  Command execution timeouts result as RTN_FAIL.

      - If `return_type` = 'check_string':  `success_status` = 'RTN_PASS' if the `cmd` stdout response contains the `expected_text` and 
      not the `not_text` (response line qualified by `check_line_text`), else `success_status` = 'RTN_FAIL'.  The initial `cmd` run exit code 
      may be non-zero, but the string checks are executed only on stdout.

      - The returned `CompletedProcess` structure contains these fields:
        - `args` - the command string executed
        - `returncode` - integer command execution status
            - 0:  `cmd` executed successfully
            - \>0: `cmd`-specific error exit code
            - `RTNCODE_REMOTE_CONNECTION_DOWN` ** (250): Max consecutive command execution timeouts reached, or keepalive failure.  Returned with RTN_WARNING.
            - `RTNCODE_COMMAND_TIMEOUT` (251): Timeout during `cmd` execution (not reaching the remote host Connection_command_max_timeouts limit).  Returned with RTN_FAIL.
            - `RTNCODE_ERROR` (252): Failure establishing a remote connection - PermissionDenied, ConnectionRefusedError, giaerror ...  Returned with RTN_FAIL.
            - `RTNCODE_CONNECT_ATTEMPT_FAILED` (253): Failure to establish a remote connection - ConnectionError, OSError.  Returned with RTN_WARNING.
        - `stdout` - holds any text returned from a passing `cmd` execution
        - `stderr` - holds any info on `cmd` execution errors and exceptions.  '\\n's are replaced with ' '.
      - ** Import these constant names from lanmonfuncs

    - A ValueError exception is raised if the call to cmd_check has errors, such as invalid `return_type` or `user_host_port`.

    ### Behaviors and rules
    - A typical `cmd` execution timeout exception results in `success_status = RTN_FAIL` with `returncode = RTNCODE_COMMAND_TIMEOUT`,
    with further details in `stderr`.
    - Attempting to connect to a remote host but the hostname cannot be resolved (DNS failure) results in `success_status = RTN_FAIL` 
    with `returncode = RTNCODE_ERROR`, with further details in `stderr`.
    - Attempting to connect to a known remote host (no DNS failure) but the connection still fails (eg, timeouts), result in `success_status = RTN_WARNING` 
    with `returncode = RTNCODE_CONNECT_ATTEMPT_FAILED`, with further details in `stderr`.
    - If `cmd` is executed on a remote system and the number of consecutive `cmd` execution timeouts reaches the 
    `Connection_command_max_timeouts` limit then the remote connection is closed, `success_status = RTN_WARNING` with 
    `returncode = RTNCODE_REMOTE_CONNECTION_DOWN`, and with further details in `stderr` is returned.
    - Any other exception results in `success_status = RTN_FAIL`, `returncode = RTNCODE_ERROR`, with further details in `stderr`.
    - If there are no timeout or other exceptions then `returncode` is the value returned from the `cmd` execution (with `return_type` = 'cmdrun'), with results 
    in `stdout` or `stderr`.  If `return_type` = 'check_string' the returncode value is from the string match checks.
    - The order of precedence for Connection_ and Command_ defaults is:
      1. For command execution timeout, the `timeout` value specified in a dictionary-style monitor item is highest precedent.
      2. `Command_timeout` specified in a host-section is used, if provided.
      3. `Command_timeout` specified in a [DEFAULT] section is used, if provided.
      4. The `COMMAND_TIMEOUT_DEFAULT` value ('1.0s') is used if no other timeout values are provided.
      - All other Connection_ and Command_ defaults follow the same scheme, except that only the command execution `timeout` can be specified on a monitor item definition.
    """

    global host_connections

    if return_type not in ['check_string', 'cmdrun']:
        _msg = f"Invalid return_type <{return_type}> passed to cmd_check"
        logging.error (f"ERROR:  {_msg}")
        raise ValueError (_msg)


    # Construct the uhp
    if user_host_port == 'local':
        host_section = uhp = 'local'
    else:
        if '@' in user_host_port:
            user, host, port = split_user_host_port(user_host_port)
            host_section = ''
        else:   # Section name provided - get params from config
            host_section = user_host_port
            if host_section not in globvars.config.sections():
                error_msg = f"__*****__Host section <{host_section}> not in config."
                return (RTN_FAIL, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg))
                # Or, sys.exit() - Not exiting since this would terminate testing

            try:
                host =      globvars.config.getcfg('hostname',       section=host_section)
                user =      globvars.config.getcfg('username',       section=host_section)
                port =  str(globvars.config.getcfg('port',     '22', section=host_section))
            except Exception as e:
                error_msg = f"__*****__Missing item(s) in host section <{host_section}> - {type(e).__name__}: {e}"
                return (RTN_FAIL, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg))

        uhp = f"{user}@{host}:{port}"


    # Get host local or SSH connection
    if uhp not in host_connections.connections:
        command_timeout =                   timevalue(globvars.config.getcfg('Command_timeout',                 COMMAND_TIMEOUT_DEFAULT,                section=host_section)).seconds
        command_ntries =                              globvars.config.getcfg('Command_nTries',                  COMMAND_NTRIES_DEFAULT,                 section=host_section)
        command_retry_interval =            timevalue(globvars.config.getcfg('Command_retry_interval',          COMMAND_RETRY_INTERVAL_DEFAULT,         section=host_section)).seconds

        if uhp == 'local':
            logging.getLogger("invoke").setLevel(logging.WARNING)
            connection_timeout = connection_nTries = connection_retry_interval = connection_keepalive_interval = connection_keepalive_count_max = 0  # Passed to new_connection() and Ignored in new_connection for local
            connection_command_max_timeouts = connection_env = 0        # Stored in host_connections.connections[uhp] and ignored for local
        else:   # Remote
            connection_timeout =            timevalue(globvars.config.getcfg('Connection_timeout',              CONNECTION_TIMEOUT_DEFAULT,             section=host_section)).seconds
            connection_nTries =                       globvars.config.getcfg('Connection_nTries',               CONNECTION_NTRIES_DEFAULT,              section=host_section)
            connection_retry_interval =     timevalue(globvars.config.getcfg('Connection_retry_interval',       CONNECTION_RETRY_INTERVAL_DEFAULT,      section=host_section)).seconds
            connection_keepalive_interval = timevalue(globvars.config.getcfg('Connection_keepalive_interval',   CONNECTION_KEEPALIVE_INTERVAL_DEFAULT,  section=host_section)).seconds
            connection_keepalive_count_max =          globvars.config.getcfg('Connection_keepalive_count_max',  CONNECTION_KEEPALIVE_COUNT_MAX_DEFAULT, section=host_section)
            connection_command_max_timeouts =         globvars.config.getcfg('Connection_command_max_timeouts', CONNECTION_COMMAND_MAX_TIMEOUTS_DEFAULT,section=host_section)
            connection_env  =                         globvars.config.getcfg('Connection_env',                  {},                                     section=host_section)

        try:
            host_connections.new_connection(        uhp,                # If local, then just creates placeholder host_connections.connections['local'] dict
                    connection_timeout=             connection_timeout,
                    connection_nTries=              connection_nTries,
                    connection_retry_interval=      connection_retry_interval,
                    connection_keepalive_interval=  connection_keepalive_interval,
                    connection_keepalive_count_max= connection_keepalive_count_max)
            
        except Exception as e:
            error_msg = f"Exception while connecting to {uhp}: {type(e).__name__} - "  + str(e).replace('\n',' ')
            logging.debug(error_msg)
            if 'TimeoutError' in error_msg  or  'OSError' in error_msg:
                # OSError will occur for a known unavailable host (DNS resolved but no response)
                return (RTN_WARNING, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_CONNECT_ATTEMPT_FAILED, stdout='', stderr=error_msg))
            else:
                return (RTN_FAIL, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg))


        host_connections.connections[uhp]['command_timeout'] =                  command_timeout
        host_connections.connections[uhp]['command_ntries'] =                   command_ntries
        host_connections.connections[uhp]['command_retry_interval'] =           command_retry_interval
        host_connections.connections[uhp]['connection_command_max_timeouts'] =  connection_command_max_timeouts
        host_connections.connections[uhp]['connection_env'] =                   connection_env
        host_connections.connections[uhp]['consecutive_command_timeouts'] =     0

        if uhp == 'local':
            xx =  f"        Command timeout        <{command_timeout}>, nTries <{command_ntries}>, Retry interval <{command_retry_interval}s>"
        else:
            xx =  f"        Connection timeout     <{connection_timeout}s>, nTries <{connection_nTries}>, Retry interval <{connection_retry_interval}s>\n"
            xx += f"        Connection keepalive   <{connection_keepalive_interval}s>, max count <{connection_keepalive_count_max}>\n"
            xx += f"        Connection environment <{connection_env}>\n"
            xx += f"        Command timeout        <{command_timeout}>, nTries <{command_ntries}>, Retry interval <{command_retry_interval}s>, Max consecutive timeouts <{connection_command_max_timeouts}>"
        logging.debug (f"Connection (re)established:  <{uhp}>\n{xx}")


    # Run the command, with retries
    _cmd_timeout = host_connections.connections[uhp]['command_timeout']  if cmd_timeout is None  else cmd_timeout

    for nTry in range (host_connections.connections[uhp]['command_ntries']):
        if nTry > 0:
            time.sleep (host_connections.connections[uhp]['command_retry_interval'])
        logging.debug(f"cmd try {nTry+1} on <{uhp}>:  <{cmd}>")

        if uhp == 'local':
            try:
                run_try = invoke.run(cmd, hide=True, timeout=_cmd_timeout, warn=True)

                run_result = subprocess.CompletedProcess(
                    args=           run_try.command,
                    returncode=     run_try.exited,
                    stdout=         run_try.stdout.strip(),
                    stderr=         run_try.stderr.strip().replace('\n',' '))

            except invoke.exceptions.CommandTimedOut as e:
                error_msg = '__*****__' + type(e).__name__ + ": " + str(e).replace('\n',' ')
                run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_COMMAND_TIMEOUT, stdout='', stderr=error_msg)
                logging.debug(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")
                continue

            except Exception as e:
                error_msg = '__*****__' + type(e).__name__ + ": " + str(e).replace('\n',' ')
                run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg)
                logging.debug(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")
                # logging.exception(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")     # for debug
                continue

        else:   # Remote execution
            try:
                run_try = host_connections.run_command(
                    command =       cmd,
                    uhp =           uhp,
                    command_timeout=_cmd_timeout)

                run_result = subprocess.CompletedProcess(
                    args=           cmd,
                    returncode=     run_try.exit_status,
                    stdout=         run_try.stdout.strip(),
                    stderr=         run_try.stderr.strip().replace('\n',' '))

            except TimeoutError as e:
                error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
                run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_COMMAND_TIMEOUT, stdout='', stderr=error_msg)
                logging.debug(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")
                continue

            except ConnectionError as e:
                # Raised in run_command() on excessive command timeouts, or connection lost/keepalive fail/...
                error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
                run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_CONNECTION_DOWN, stdout='', stderr=error_msg)
                logging.debug(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")
                return (RTN_WARNING, run_result)

            except Exception as e:
                # Raised in run_command() - catchall
                error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
                run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg)
                logging.debug(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")
                # logging.exception(f"cmd try {nTry+1} failed (exception):  <{error_msg}>")     # for debug
                continue

        if run_result.returncode != 0:           # no exception, but non-passing result
            run_result.stderr = error_msg = '__*****__' + run_result.stderr
            logging.debug(f"cmd try {nTry+1} failed (returncode {run_result.returncode}):  <{error_msg}>")
        # logging.debug(f"cmd_check subprocess.run returned <{run_try}>")      # for debug.  stdout can be huge.


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

            run_result.returncode = 1                           # check_string fail returncode
            run_result.stderr = _msg

        else:   # return_type == 'cmdrun':
            if run_result.returncode == 0:
                return (RTN_PASS, run_result)                   # cmdrun Pass exit

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
      - user or `local` (cast to lower case)
      - host or `local` (cast to lower case)
      - port number
    - Raises ValueError if the u_h_p cannot be parsed
    
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
    u_h_p = u_h_p.lower().strip()
    if u_h_p == 'local':
        return ('local', 'local', '')

    else:
        if ':' not in u_h_p:
            u_h_p += ':22'
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
#  c l a s s   C o n n e c t i o n s M a n a g e r
#=====================================================================================
#=====================================================================================

class ConnectionsManager:
    """
    `host_connections` is the single instance of this class.
    All established local and remote/ssh connections are stored in the `host_connections.connections`
    dictionary.
    Local commands are executed by the invoke.run() call in cmd_check(), while remote commands are 
    executed by asyncssh using run_command() in this class.

    The value-portion of each `host_connections.connections` entry is in-turn a dictionary.  new_connection()
    populates `host_connections.connections['local'] = {'ssh_conn': None}` for the local connection, and populates
    `host_connections.connections[uhp] = {'ssh_conn': asyncssh.connect()}` for new remote connections.

    cmd_check() populates several other keys in each connection's dictionary that are used by invoke.run() (for local)
    or asyncssh.run() in self.run_command().  The fully populated connection dictionary contains:

        'ssh_conn'                          None (for local) or as returned by asyncssh.connect()
        'command_timeout'                   Connection-specific default command execution timeout if not specified on the cmd_check call
        'command_ntries'                    Connection-specific command nTries
        'command_retry_interval'            Connection-specific command retry interval
        'connection_command_max_timeouts'   The connection is dropped if this timeout count is reached
        'consecutive_command_timeouts'      Incremented on each command execution timeout, reset to 0 on command success
        'connection_env'                    Connection-specific environment vars passed with each asyncssh.run() call (not used for local)
    """

    def __init__(self, logging_level=logging.WARNING):
        self.connections = {}
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._start_loop, daemon=True)
        self._thread.start()
        asyncssh.set_log_level(logging_level)


    def new_connection(self, uhp, 
                       connection_timeout, connection_nTries, connection_retry_interval,
                       connection_keepalive_interval, connection_keepalive_count_max, 
                       password=None):

        if uhp == 'local':
            self.connections[uhp] = {'ssh_conn': None}
        else:
            self.run_coroutine(self._new_connection(uhp, 
                                                    connection_timeout, connection_nTries, connection_retry_interval,
                                                    connection_keepalive_interval, connection_keepalive_count_max,
                                                    password))


    async def _new_connection(self, uhp, 
                              connection_timeout, connection_nTries, connection_retry_interval,
                              connection_keepalive_interval, connection_keepalive_count_max,
                              password):
        # Adds new uhp connection to the self.connections dict
        # Allows a new_connection call if already exists, but ignores it
        # Raises
        #   asyncio.TimeoutError - Occurs if connection attempt times out
        #   asyncssh.Error       - Occurs if any asyncssh errors
        #   OSError              - Occurs if any TCP socket level errors (no route to host, refused, DNS...)
        # All other exceptions are passed up

        conn = self.connections.get(uhp)

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
                                                                        keepalive_interval=connection_keepalive_interval,
                                                                        keepalive_count_max=connection_keepalive_count_max),
                                                        timeout=connection_timeout+1)
                    self.connections[uhp] = {'ssh_conn': ssh_conn}
                    break
                    
                except (asyncio.TimeoutError, asyncssh.Error, OSError) as e:
                    logging.debug (f"Connection attempt {_try} to <{uhp}> FAILED:  {type(e).__name__}: {e}")
                    if _try < connection_nTries:
                        await asyncio.sleep(connection_retry_interval)
                        continue
                    raise ConnectionError(f"Connection to <{uhp}> FAILED after {connection_nTries} attempts __*****__{type(e).__name__}: {e}")
                

    def run_command(self, command, uhp, command_timeout):
        return self.run_coroutine(self._run_command(command, uhp, command_timeout))


    async def _run_command(self, command, uhp, command_timeout):
        # Returns
        #   command execution result with stdout / stderr
        # Raises
        #   TimeoutError    if command run timed out, but not reached consecutive timeouts limit
        #   ConnectionError if:
        #                   excessive number of timeouts (checked in this code)
        #                   ChannelOpenError
        #                   ConnectionLost (keepalve closed the channel)
        # All other exceptions are passed up

        conn = self.connections.get(uhp)
        if not conn:
            raise ConnectionError(f"__*****__Connection to <{uhp}> not established")    # This should not happen
        ssh_conn = conn['ssh_conn']

        try:
            result = await asyncio.wait_for(ssh_conn.run(command, env= conn['connection_env']), 
                                            timeout=command_timeout)
            conn['consecutive_command_timeouts'] = 0
            return result

        except asyncio.TimeoutError as e:
            error_msg = f"Command execution error on <{uhp}>:  __*****__{type(e).__name__}: {e}"
            conn['consecutive_command_timeouts'] += 1
            logging.debug (f"consecutive_command_timeouts <{uhp}>: {conn['consecutive_command_timeouts']}")
            if conn['consecutive_command_timeouts'] == conn['connection_command_max_timeouts']:
                await self._close_connection(ssh_conn)
                del self.connections[uhp]
                logging.warning (f"Excessive command timeouts on <{uhp}> - Closed connection")
                raise ConnectionError(error_msg)
            raise TimeoutError(error_msg)
        
        except (asyncssh.ConnectionLost, asyncssh.ChannelOpenError) as e:
            del self.connections[uhp]
            raise ConnectionError(f"Command execution error on <{uhp}> - ConnectionLost:   __*****__{type(e).__name__}: {e}")


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
        for key in self.connections:
            xx += f"  <{key}>\n"
        return xx


    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()


    def run_coroutine(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()


host_connections = ConnectionsManager() #logging.DEBUG)


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
    - If neither config `Gateway` nor called `host` are provided then return True (default to LAN access passes)
    """

    ip_or_hostname = globvars.config.getcfg('Gateway', host)
    if not ip_or_hostname:
        return True

    if (IP_RE.match(ip_or_hostname) is None)  and  (HOSTNAME_RE.match(ip_or_hostname) is None):
        logging.error (f"  ERROR:  INVALID IP ADDRESS OR HOSTNAME <{ip_or_hostname}> - Aborting.")
        sys.exit(1)

    gateway_timeout = timevalue(globvars.config.getcfg('Gateway_timeout', GATEWAY_TIMEOUT_DEFAULT)).seconds
    pingrslt = cmd_check(f'ping -c 1 {globvars.config.getcfg("Gateway")}',
                         cmd_timeout=gateway_timeout, user_host_port='local', return_type='cmdrun')
    if pingrslt[0] == RTN_PASS:
        return True
    else:
        return False


#=====================================================================================
#=====================================================================================
#  n e x t _ s u m m a r y _ d t
#=====================================================================================
#=====================================================================================
def next_summary_dt():
    """
    ## next_summary_dt() - Calculate the datetime of next summary

    Example config file items
    ```
        SummaryDays   [1, 3, 5]     # Days of week: 1 = Monday, 7 = Sunday.  = 0 for every day
        SummaryTime   9:45          # 24 hour clock
    ```

    Don't define SummaryDays to disable summaries

    ### Returns
    - datetime of next summary
    """

    if (days := globvars.config.getcfg('SummaryDays', None)) is None:
        logging.debug(f"SummaryDays not defined.  Summaries are disabled.")
        return None

    try:
        times = globvars.config.getcfg('SummaryTime', '')
        next_summary_dt = get_next_dt(times, days)
        logging.debug(f"Next summary:  {next_summary_dt}")
        return next_summary_dt

    except Exception as e:
        # _msg = f"SummaryDays <{days}> or SummaryTime <{times}> settings could not be parsed\n  {type(e).__name__}: {e}"
        _msg = f"SummaryDays <{days}> or SummaryTime <{times}> settings could not be parsed - {e}"
        raise ConfigError (_msg)
