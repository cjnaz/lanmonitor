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

# from fabric import Connection
# from invoke import CommandTimedOut
import asyncssh
import asyncio

from cjnfuncs.core import logging, set_logging_level, restore_logging_level
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

RTNCODE_TIMEOUT =       254
RTNCODE_ERROR =         253
RTNCODE_REMOTE_CONNECT_ERROR= 252


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


# connect() - ntries =2, set from config
    # key is user@host:port  (uhp)
    # connect timeout from config, default 2s


# run command
    # get connection.  If not connected then call connect
    # run command with ntries
    # on repeated command fails on same non-localhost, dump connection
        # counter of consecutive fails per uhp
        # limit set from config, default 4 command fails?

import asyncio
import asyncssh
import threading
from typing import Optional, Tuple, Dict

CONNECTION_TIMEOUT_DEFAULT = 2       # Connection attempt timeout
COMMAND_TIMEOUT_DEFAULT = 1         # Per-command timeout
# MAX_RETRIES = 2             # Retry count for connecting
NTRIES_CONNECTION = 2
# NTRIES_COMMAND = 2
MAX_CONSECUTIVE_FAILS = 4   # At this count, close/delete the conn
SEC_BTW_CONNECTION_ATTEMPTS = 0.5
# SEC_BTW_COMMAND_ATTEMPTS = 0.5

# Config...
# Core tool params
# nTries                      2           # Num times to try to read an item before erroring
# SSH_timeout                 4s          # Max time for ssh connections to non-local hosts.  Default 1.0s
# Cmd_timeout                 4s          # Max time allowed for a subprocess.run call, if not specified on the monitor item.  Default 1.0s.


class AsyncSSHManager:
    # def __init__(self, connection_timout=CONNECTION_TIMEOUT, logging_level=logging.WARNING):
    def __init__(self, logging_level=logging.WARNING):
        # self.connections: Dict[Tuple[str, int, str], asyncssh.SSHClientConnection] = {}
        self.connections = {}
        # self.credentials: Dict[Tuple[str, int, str], dict] = {}
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._start_loop, daemon=True)
        self._thread.start()
        asyncssh.set_log_level(logging_level)
        # self.command_timeout_default = globvars.config.getcfg('Cmd_timeout', COMMAND_TIMEOUT_DEFAULT)
        # self.connection_timeout_default = globvars.config.getcfg('SSH_timeout', CONNECTION_TIMEOUT_DEFAULT)
        # self.logging_level = logging_level
        # self.connection_timout = connection_timout

    def new_connection(self, uhp, connection_timeout, ntries_connection, btw_retries_sec, max_consec_timeouts, password=None):
        return self.run_coroutine(self._new_connection(uhp, connection_timeout, ntries_connection, btw_retries_sec, max_consec_timeouts, password))


    async def _new_connection(self, uhp, connection_timeout, ntries_connection, btw_retries_sec, max_consec_timeouts, password):
        conn = self.connections.get(uhp)    # TODO Allow call if already exists??

        if not conn:        # connection doesn't exist
            # last_exc = None
            for _try in range(1, ntries_connection+1):
                try:
                    logging.debug (f"Connection attempt {_try} to <{uhp}>")
                    user, host, port = split_user_host_port(uhp)
                    ssh_conn = await asyncio.wait_for (asyncssh.connect(host=host, username=user, port=port,
                                                        password=password), timeout=connection_timeout)
                    conn = self.connections[uhp] = {'ssh_conn': ssh_conn,
                                                    'consecutive_command_timeouts': 0,
                                                    'max_consec_timeouts': max_consec_timeouts}
                    logging.warning (f"Connection (re)established:  <{uhp}>")
                    break
                    
                except (asyncio.TimeoutError, asyncssh.Error, OSError) as e:
                    # last_exc = e
                    logging.debug (f"Connection attempt {_try} to <{uhp}> FAILED:  {type(e).__name__}: {e}")
                    if _try < ntries_connection:
                        await asyncio.sleep(btw_retries_sec)
                        continue
                    raise ConnectionError(f"Connection to <{uhp}> FAILED after {ntries_connection} attempts: {type(e).__name__}: {e}")

        # ssh_conn = conn['ssh_conn']



    def Nrun_command(self, command, uhp, command_timeout, connection_timeout,
                     password=None, env={}):
        
        # Apply default arg values from constants, overridden by config values
        # command_timeout = command_timeout  if command_timeout  else self.command_timeout_default

        return self.run_coroutine(self.N_run_command(command, uhp, password,
                                                     command_timeout, connection_timeout, env))


    async def N_run_command(self, command, uhp, password,
                     command_timeout, connection_timeout, env):
        
        # async def check_consec_except(uhp):
        #     consec_except_count = uhp['consecutive_command_fails']
        #     logging.debug (f"Consecutive exception count for <{uhp}>: {consec_except_count}")
        #     if consec_except_count == MAX_CONSECUTIVE_FAILS:
        #         # logging.debug (f"Excessive command fails on <{uhp}>")
        #         logging.debug (f"Too many consecutive exceptions for <{uhp}> - Closing connection")
        #         await self._close_connection(ssh_conn)
        #         del self.connections[uhp]
        #         # conn['ssh_conn'].close()    # pops from self.connections
        #         raise ValueError(f"Excessive consecutive command execution errors on <{uhp}> - Connection closed:  {type(e).__name__}: {e}")


        # Runs command on uhp, returning asyncssh.completed structure or raises
            # ConnectionError

        # Get connection if previously established, else make new connection
        # Connection structure:  key: {'ssh_conn': ssh_connection, 'consecutive_command_fails': 0}
        conn = self.connections.get(uhp)

        # if not conn:        # connection doesn't exist
        #     last_exc = None
        #     for _try in range(1, NTRIES_CONNECTION+1):
        #         try:
        #             logging.debug (f"Connection attempt {_try} to <{uhp}>")
        #             user, host, port = split_user_host_port(uhp)
        #             ssh_conn = await asyncio.wait_for (asyncssh.connect(host=host, username=user, port=port,
        #                                                 password=password), timeout=connection_timeout)
        #             conn = self.connections[uhp] = {'ssh_conn': ssh_conn, 'consecutive_command_fails': 0}
        #             logging.warning (f"Connection (re)established:  <{uhp}>")
        #             break
                    
        #         except (asyncio.TimeoutError, asyncssh.Error, OSError) as e:
        #             last_exc = e
        #             logging.debug (f"Connection attempt {_try} to <{uhp}> FAILED:  {type(e).__name__}: {e}")
        #             if _try < NTRIES_CONNECTION:
        #                 await asyncio.sleep(SEC_BTW_CONNECTION_ATTEMPTS)
        #                 continue
        #             raise ConnectionError(f"Connection to <{uhp}> FAILED after {NTRIES_CONNECTION} attempts: {type(last_exc).__name__}: {last_exc}")

        if not conn:
            raise ConnectionError(f"Connection to <{uhp}> unknown")

        ssh_conn = conn['ssh_conn']



            # ssh_conn = await self._connect_with_retry(host, port, username, password,
            #                                       timeout=connection_timeout)
            # self.connections[key] = conn
            # self.credentials[key] = {"password": password}


        # if not conn or not conn._transport or conn._transport._conn_lost:
        #     # print (f"no connection to {host}")
        #     await self._close_connection(conn)
        #     conn = await self._connect_with_retry(host, port, username, password,
        #                                           timeout=connection_timeout)
        #     self.connections[key] = conn
        #     self.credentials[key] = {"password": password}

        # for _try in range(1, NTRIES_COMMAND):
        try:
            # logging.debug (f"Command execution attempt {_try} to <{uhp}>, command <{command}>")
            result = await asyncio.wait_for(ssh_conn.run(command, env=env), timeout=command_timeout)
            conn['consecutive_command_fails'] = 0
            # TODO if result returncode not 0, retry
            return result
            
        # except (asyncio.TimeoutError, asyncssh.Error, OSError) as e:
        except asyncio.TimeoutError as e:
            logging.debug (f"Command execution on <{uhp}> EXCEPTION:  {type(e).__name__}: {e}")
            conn['consecutive_command_fails'] += 1
            if conn['consecutive_command_fails'] == MAX_CONSECUTIVE_FAILS:
                logging.debug (f"Excessive command timeouts on <{uhp}> - Closing connection")
                await self._close_connection(ssh_conn)
                del self.connections[uhp]
                # conn['ssh_conn'].close()    # pops from self.connections
                # raise ValueError(f"Excessive consecutive command execution errors on <{uhp}> - Connection closed:  {type(e).__name__}: {e}")
                # break
                # self.connections[uhp].pop()
            # await asyncio.sleep(SEC_BTW_COMMAND_ATTEMPTS)
            # raise ConnectionError(f"Command execution error on <{uhp}>:  {type(last_exc).__name__}: {last_exc}")
            raise TimeoutError(f"Command execution error on <{uhp}>:  {type(e).__name__}: {e}") # from e

        # Any other exception is passed up
        # except Exception as e:
        #     # last_exc = e
        #     # logging.debug (f"Command execution attempt {_try} to <{uhp}> EXCEPTION:  {type(e).__name__}: {e}")
        #     logging.debug (f"Command execution on <{uhp}> EXCEPTION:  {type(e).__name__}: {e}")
        #     raise (f"Command execution error on <{uhp}>:  {type(e).__name__}: {e}") from e


        # try:
        #     result = await asyncio.wait_for(ssh_conn.run(command, env=env), timeout=command_timeout)
        #     # logging.debug (f"Returned from conn.run():  <{result}>")
        #     # return result.stdout.strip()
        #     return result
        # except asyncio.TimeoutError:
        #     raise TimeoutError(f"[{host}] Command timed out: {command}")
        # except (asyncssh.Error, OSError, EOFError) as e:
        #     # Connection is broken, clear and retry once
        #     await self._close_connection(conn)
        #     del self.connections[key]
        #     try:
        #         creds = self.credentials.get(key, {})
        #         new_conn = await self._connect_with_retry(host, port, username, creds.get("password"),
        #                                                   timeout=connection_timeout)
        #         self.connections[key] = new_conn
        #         result = await asyncio.wait_for(new_conn.run(command), timeout=command_timeout)
        #         # return result.stdout.strip()
        #         return result
        #     except Exception as e2:
        #         raise ConnectionError(f"[{host}] Failed to reconnect and run command: {type(e2).__name__}: {e2}")



    # # def run_command(self, host: str, username: str, command: str, *, port: int = 22, password: Optional[str] = None,
    # #                 command_timeout = COMMAND_TIMEOUT, connection_timeout=CONNECTION_TIMEOUT, env: dict = {}):
    # def run_command(self, command, host, username, port, password=None,
    #                 command_timeout =   COMMAND_TIMEOUT,
    #                 connection_timeout= CONNECTION_TIMEOUT,
    #                 env =               {}):
    #     # set_logging_level(self.logging_level, save=True)
    #     xx = self.run_coroutine(self._run_command(command, host, username, port, password,
    #                                               command_timeout, connection_timeout, env))
    #     # restore_logging_level()
    #     return xx #self.run_coroutine(self._run_command(host, port, username, password, command, timeout))


    # # async def _run_command(self, host: str, port: int, username: str, password: Optional[str],
    # #                        command: str, timeout: int, env: dict):
    # async def _run_command(self, command, host, username, port, password,
    #                        command_timeout,
    #                        connection_timeout,
    #                        env):
    #     key = (host, port, username)
    #     # print (command, host, username, port, password, command_timeout,
    #     #                    connection_timeout,
    #     #                    env)

    #     conn = self.connections.get(key)

    #     if not conn or not conn._transport or conn._transport._conn_lost:
    #         # print (f"no connection to {host}")
    #         await self._close_connection(conn)
    #         conn = await self._connect_with_retry(host, port, username, password,
    #                                               timeout=connection_timeout)
    #         self.connections[key] = conn
    #         self.credentials[key] = {"password": password}

    #     try:
    #         result = await asyncio.wait_for(conn.run(command, env=env), timeout=command_timeout)
    #         # logging.debug (f"Returned from conn.run():  <{result}>")
    #         # return result.stdout.strip()
    #         return result
    #     except asyncio.TimeoutError:
    #         raise TimeoutError(f"[{host}] Command timed out: {command}")
    #     except (asyncssh.Error, OSError, EOFError) as e:
    #         # Connection is broken, clear and retry once
    #         await self._close_connection(conn)
    #         del self.connections[key]
    #         try:
    #             creds = self.credentials.get(key, {})
    #             new_conn = await self._connect_with_retry(host, port, username, creds.get("password"),
    #                                                       timeout=connection_timeout)
    #             self.connections[key] = new_conn
    #             result = await asyncio.wait_for(new_conn.run(command), timeout=command_timeout)
    #             # return result.stdout.strip()
    #             return result
    #         except Exception as e2:
    #             raise ConnectionError(f"[{host}] Failed to reconnect and run command: {type(e2).__name__}: {e2}")


    # async def _connect_with_retry(self, host, port, username, password, timeout):  # TODO password ??
    #     # print (host, port, username,password, timeout)
    #     last_exc = None
    #     for attempt in range(1, MAX_RETRIES + 1):       # TODO ntries, or leave to command failure retries?
    #         try:
    #             conn = await asyncio.wait_for(
    #                 # asyncssh.connect(host, port=port, username=username, password=password, env=env),
    #                 # asyncssh.connect(host, port=port, username=username, password=password),
    #                 # timeout=timeout)
    #                 asyncssh.connect(host, port=port, username=username, password=password), timeout=timeout )
    #             logging.warning (f"Connection (re)established:  {username}@{host}:{port}")
    #             return conn
                
    #         except (asyncio.TimeoutError, asyncssh.Error, OSError) as e:
    #             last_exc = e
    #             await asyncio.sleep(1)
    #     raise ConnectionError(f"[{host}] Could not connect after {MAX_RETRIES} attempts: {type(last_exc).__name__}: {last_exc}")


    def close (self, uhp):
        """Close a specific connection or all."""
        if uhp == 'all':
            self.run_coroutine(self._close_all())
        else:
            if conn := self.connections.get(uhp):
                self.run_coroutine(self._close_connection(conn['ssh_conn']))
                del self.connections[uhp]



    # def close(self, host: Optional[str] = None, port: int = 22, username: Optional[str] = None):
    #     """Close a specific connection or all."""
    #     # set_logging_level(self.logging_level, save=True)
    #     if host and username:
    #         key = (host, port, username)
    #         conn = self.connections.pop(key, None)
    #         if conn:
    #             self.run_coroutine(self._close_connection(conn))
    #         self.credentials.pop(key, None)
    #     else:
    #         self.run_coroutine(self._close_all())
        # restore_logging_level()


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
        
        # for conn in list(self.connections.values()):
        #     await self._close_connection(conn)
        self.connections.clear()
        # self.credentials.clear()


    def is_connected(self, uhp):
        conn = self.connections.get(uhp)
        if conn:
            ssh_conn = conn['ssh_conn']
            return bool(ssh_conn._transport  and  not ssh_conn._transport._conn_lost)
        return False


    # def is_connected(self, host: str, port: int = 22, username: str = "") -> bool:
    #     key = (host, port, username)
    #     conn = self.connections.get(key)
    #     return bool(conn and conn._transport and not conn._transport._conn_lost)


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



# #=====================================================================================
# #=====================================================================================
# #  c o n n e c t i o n s _ m a n a g e r
# #=====================================================================================
# #=====================================================================================
# class connections_manager:
#     def __init__(self, logging_level=logging.WARNING): #, timeout=1):
#         global host_connections
#         # logging.getLogger("fabric").setLevel(logging_level)       # TODO settable
#         # logging.getLogger("invoke").setLevel(logging_level)
#         # logging.getLogger("paramiko").setLevel(logging_level)
#         self.connections_dict = {}
#         # self.connections_dict['local'] = Connection('localhost')
#         # self.connect_timeout = timeout
#         host_connections = self

#     async def get(self, user_host_port, connection_timeout=1):
#         uhp = user_host_port.lower()
#         if uhp == 'local':
#             uhp = 'cjn@localhost:50763'
#             # return self.connections_dict[uhp]
#         # else:
#         if ':' not in uhp:
#             uhp += ':22'

#         if uhp not in self.connections_dict  or  self.connections_dict[uhp].is_closed():
#             print ("calling self._connect")
#             await self._connect(uhp, connection_timeout)

#         # if self.conn is None  or self.conn.is_closed():
#         #     print ("(re)connecting")
#         #     try:
#         #         await self.connect()
#         #     except Exception as e:
#         #         return {"status": "No connection", "reason": f"{type(e).__name__}>>>: {e}"}

#         _conn = self.connections_dict[uhp]
#         # if _conn.is_connected:
#         #     return _conn
#         # else:
#         #     return False
#         if not _conn.is_closed():
#             return _conn
#         else:
#             return False

#     async def _connect(self, uhp, timeout):
#         # Connection failure raises various exceptions including TimeoutError / AuthenticationException / NoValidConnectionsError
#         # which must be caught/handled in cmd_check()
#         user, host, port = split_user_host_port(uhp)
#         # _conn = Connection(host=host, user=user, port=port, connect_timeout=timeout) #self.connect_timeout)
#         # _conn = asyncio.run(asyncssh.connect(host, username=user, port=port))
#         print (host, user, port)
#         _conn = await asyncio.wait_for(
#                 asyncssh.connect(
#                     host,
#                     username=user,
#                     port= port #,
#                     # known_hosts=None
#                 ),
#                 timeout=timeout)
#         # _conn = Connection(host=host, user=user, port=port, connect_kwargs={'timeout': 10})
#         # _conn.open()
#         # _conn.transport.set_keepalive(30)
#         # _conn.transport.timeout
#         self.connections_dict[uhp] = _conn
#         logging.warning (f"Connection (re)established:  <{uhp}> - {self.connections_dict[uhp]}")
#         return

#     def __repr__(self):
#         # Return formatted list of current connections
#         xx = "Current connections:\n"
#         # print (self.connections_dict)
#         for key in self.connections_dict:
#             xx += f"  <{key:20}>:  {self.connections_dict[key]}\n"
#         return xx

#     async def _closeall(self):
#         for key in self.connections_dict:
#             # if key != 'local':
#             await self.connections_dict[key].close()
#         self.connections_dict.clear()
#         # self.connections_dict['local'] = Connection('localhost')

#     def closeall(self):
#         asyncio.run(self._closeall())


# host_connections = connections_manager()

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
    - _The value must be an integer number of seconds. Not a float._

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

    connection_timeout_default = timevalue(globvars.config.getcfg('SSH_timeout', CONNECTION_TIMEOUT_DEFAULT)).seconds  # As specified in top-level config - legacy

    if '@' in user_host_port  or  ';' in '@' in user_host_port:
        user, host, port = split_user_host_port(user_host_port)
        connection_timeout = connection_timeout_default
        env = {}
    else:   # Hostname only provided.  Get params from config, with these defaults
        host_section = user_host_port
        host =                  globvars.config.getcfg('hostname', host_section,    section=host_section)
        user =                  globvars.config.getcfg('username',                  section=host_section)
        port =                  str(globvars.config.getcfg('port', '22',            section=host_section))
        # connection_timeout =    globvars.config.getcfg('SSH_timeout', connection_timeout_default, section=host_sec)
        connection_timeout =    timevalue(globvars.config.getcfg('SSH_timeout', connection_timeout_default, section=host_section)).seconds
        env  =                  globvars.config.getcfg('env',      {},              section=host_section)
    # print (user, host, port)

    # print (globvars.config.dump())

        # if host in globvars.config.sections():
            # user =                  globvars.config.getcfg('username', user, section=host)
            # port =                  str(globvars.config.getcfg('port', port, section=host))
            # env  =                  globvars.config.getcfg('env',      {},   section=host)
            # connection_timeout =    globvars.config.getcfg('SSH_timeout',  CONNECTION_TIMEOUT_DEFAULT,     section=host)
            # host =                  globvars.config.getcfg('hostname',       section=host)   # TODO connection_timout

    uhp = f"{user}@{host}:{port}"
    # print (uhp)

    # print (user, host, port)

# globvars.config.cfg['local']['username'] = 'me'
# globvars.config.cfg['local']['hostname'] = 'localhost'
# globvars.config.cfg['local']['port'] = 22


    # TODO accept host only and get user & port from config, and auth file pointer
    
    # if 'host_connections' not in globals():
    #     connections_manager(logging.DEBUG)

    # try:
    #     connection_timeout = timevalue(globvars.config.getcfg('SSH_timeout', SSH_TIMEOUT)).seconds
    #     print ("Before asyncio.run(host_connections.get")
    #     host_conn =  asyncio.run(host_connections.get(user_host_port, connection_timeout=connection_timeout))
    #     print (f"host_conn:  {host_conn}")
    # except TimeoutError as e:       # Connection/SSH timeout
    #     error_msg = f"Host <{user_host_port}> connection failed:  {type(e).__name__}: {e}"
    #     logging.debug(error_msg)    # TODO close the connection
    #     return (RTN_WARNING, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_TIMEOUT, stdout='', stderr=error_msg))
    # except Exception as e:
    #     error_msg = f"Host <{user_host_port}> connection failed:  {type(e).__name__}: {e}"
    #     logging.debug(error_msg)
    #     return (RTN_FAIL, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg))

    error_msg = ''
    ntries = globvars.config.getcfg('nTries', NTRIES)
    # logging.getLogger('asynchssh').setLevel(logging.INFO)

    # async def runner(host_conn, cmd, timeout):
    #     result = await asyncio.wait_for(
    #         host_conn.run(cmd, check=False),
    #         timeout=timeout)
    #     return result

    if uhp not in host_connections.connections:
        try:
            host_connections.new_connection(uhp,
                    connection_timeout=connection_timeout,
                    ntries_connection=2,
                    btw_retries_sec=0.5,
                    max_consec_timeouts=4
                    )

        # except ConnectionError as e:
        #     error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
        #     run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_CONNECT_ERROR, stdout='', stderr=error_msg)
        #     logging.debug(f"cmd try {nTry+1} failed (exception):  {error_msg}")
        #     raise ConnectionError (f"Exception while connecting to {uhp}:  {error_msg}")
        #     return (RTN_WARNING, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_CONNECT_ERROR, stdout='', stderr=error_msg))

        except Exception as e:
            error_msg = f"Exception while connecting to {uhp}: {type(e).__name__} - "  + str(e).replace('\n',' ')
            # run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_CONNECT_ERROR, stdout='', stderr=error_msg)
            logging.debug(error_msg)
            return (RTN_WARNING, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_CONNECT_ERROR, stdout='', stderr=error_msg))

    # conn = host_connections[uhp]

    for nTry in range (ntries):
        try:
            # logging.debug(f"cmd try {nTry+1} on <{user_host_port}>:  <{cmd}>")
            logging.debug(f"cmd try {nTry+1} on <{uhp}>:  <{cmd}>")
            # if user_host_port == 'local':
            #     run_try = host_conn.local(cmd, hide=True, warn=True, timeout=cmd_timeout)
            # else:
            #     # run_try = run_with_timeout(host_conn.run, cmd, hide=True, warn=True, timeout=cmd_timeout, rwt_timeout=10)
            #     run_try = host_conn.run(cmd, hide=True, warn=True, timeout=cmd_timeout)
            # run_try = asyncio.run(runner(host_conn=host_conn, cmd=cmd, timeout=cmd_timeout))

            # user, host, port = split_user_host_port(user_host_port)
            
            # run_try = host_connections.run_command(
            #     command=cmd,
            #     host=host,
            #     username=user,
            #     port=port,      # TODO command_timeout
            #     connection_timeout=connection_timeout,
            #     env=env
            # )

            run_try = host_connections.Nrun_command(
                command=cmd,
                uhp= uhp,      # TODO command_timeout
                command_timeout=cmd_timeout,
                connection_timeout=connection_timeout,
                env=env
            )

            # logging.debug (run_try)
            # return
                    # TODO change to asyncssh.SSHCompletedProcess
            run_result = subprocess.CompletedProcess(args=cmd, returncode=run_try.exit_status, stdout=run_try.stdout.strip(), stderr=run_try.stderr.strip().replace('\n',' '))

            if run_result.returncode > 0:           # no exception, but non-passing result
                error_msg = run_result.stderr
                logging.debug(f"cmd try {nTry+1} failed:  <{error_msg}>")
            # logging.debug(f"cmd_check subprocess.run returned <{run_try}>")      # Uncomment for debug.  stdout can be huge.

        except TimeoutError as e:
            error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
            run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_TIMEOUT, stdout='', stderr=error_msg)
            logging.debug(f"cmd try {nTry+1} failed (exception):  {error_msg}")
            continue

        # except ConnectionError as e:
        #     # raise
        #     error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
        #     run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_TIMEOUT, stdout='', stderr=error_msg)
        #     logging.debug(f"cmd try {nTry+1} failed (exception):  {error_msg}")
        #     continue

        except Exception as e:
            error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
            run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg)
            logging.debug(f"cmd try {nTry+1} failed (exception):  {error_msg}")
            # logging.exception(f"cmd try {nTry+1} failed (exception):  {error_msg}")
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

        if nTry < ntries-1:
            time.sleep (timevalue(globvars.config.getcfg('RetryInterval', RETRY_INTERVAL)).seconds)

        # End of ntries loop

    return (RTN_FAIL, run_result)                               # Fail exit after ntries


# #=====================================================================================
# #=====================================================================================
# #  c o n n e c t i o n s _ m a n a g e r
# #=====================================================================================
# #=====================================================================================
# class connections_manager:
#     def __init__(self, logging_level=logging.WARNING): #, timeout=1):
#         global host_connections
#         logging.getLogger("fabric").setLevel(logging_level)       # TODO settable
#         logging.getLogger("invoke").setLevel(logging_level)
#         logging.getLogger("paramiko").setLevel(logging_level)
#         self.connections_dict = {}
#         self.connections_dict['local'] = Connection('localhost')
#         # self.connect_timeout = timeout
#         host_connections = self

#     def get(self, user_host_port, connection_timeout=1):
#         uhp = user_host_port.lower()
#         if uhp == 'local':
#             return self.connections_dict[uhp]
#         else:
#             if ':' not in uhp:
#                 uhp += ':22'

#             if uhp not in self.connections_dict  or  not self.connections_dict[uhp].is_connected:
#                 self._connect(uhp, connection_timeout)
#             _conn = self.connections_dict[uhp]
#             if _conn.is_connected:
#                 return _conn
#             else:
#                 return False

#     def _connect(self, uhp, timeout):
#         # Connection failure raises various exceptions including TimeoutError / AuthenticationException / NoValidConnectionsError
#         # which must be caught/handled in cmd_check()
#         user, host, port = split_user_host_port(uhp)
#         # _conn = Connection(host=host, user=user, port=port, connect_timeout=timeout) #self.connect_timeout)
#         _conn = Connection(host=host, user=user, port=port, connect_kwargs={'timeout': 10})
#         _conn.open()
#         _conn.transport.set_keepalive(30)
#         # _conn.transport.timeout
#         self.connections_dict[uhp] = _conn
#         logging.warning (f"Connection (re)established:  <{uhp}> - {self.connections_dict[uhp]}")
#         return

#     def __repr__(self):
#         # Return formatted list of current connections
#         xx = "Current connections:\n"
#         # print (self.connections_dict)
#         for key in self.connections_dict:
#             xx += f"  <{key:20}>:  {self.connections_dict[key]}\n"
#         return xx

#     def closeall(self):
#         for key in self.connections_dict:
#             if key != 'local':
#                 self.connections_dict[key].close()
#         self.connections_dict.clear()
#         self.connections_dict['local'] = Connection('localhost')



# #=====================================================================================
# #=====================================================================================
# #  c m d _ c h e c k
# #=====================================================================================
# #=====================================================================================
# def cmd_check(cmd, user_host_port, return_type, cmd_timeout, check_line_text=None, expected_text=None, not_text=None):
#     """
#     ## cmd_check (cmd, user_host_port, return_type, cmd_timeout, check_line_text=None, expected_text=None, not_text=None) - Runs the cmd and operates on the response based on return_type

#     The `cmd` is executed by a call to fabric.local() if `user_host_port` is `local`, or via an ssh connection by
#     fabric.run() if `user_host_port` is a remote host.
#     If there is no exception and the executed `cmd` returns an exit code = 0 then cmd_check checks the
#     run response (stdout) per the `return_type` selection.  Finally, a tuple of `(success_status, subprocess.CompletedProcess structure)`
#     is returned.  

#     The total execution time of a failing local cmd_check call can be as long as:

#         nTries*cmd_timeout + (nTries-1)*RetryInterval

#     For cmd_check calls on remote systems, the simple ssh access check can add this additional execution time:

#         nTries*SSH_timeout 

#     ### Args
#     `cmd`  (str or list)
#     - Command to be passed to fabric.run() or fabric.local() in list (eg: ['echo', 'hello']) or str (eg: 'echo hello') form
#     - The `cmd` may use `~` user home expansion and `?` and `*` wildcard expansion.
#     - The `cmd` may also use `|` pipes and `>` redirection
#     - The `cmd` execution must have a passing (0) exit code else it will be retried and result in a 
#       RTN_FAIL `success_status`.  An exception raised by the `cmd` run will also cause retries.

#     `user_host_port`  (str)
#     - Target machine to execute `cmd` on, eg: 'me@testhost2:2222'.  The port number is optional (default 22).
#     - `local` indicates run `cmd` on the local machine

#     `cmd_timeout`  (float, value in seconds)
#     - timeout value used when executing `cmd`

#     `return_type`  (str - either 'cmdrun' or 'check_string')
#     - If `return_type` = 'cmdrun' then RTN_PASS (`cmd` exit code = 0) or RTN_FAIL (`cmd` exit code > 0) and
#     the `CompletedProcess` structure is returned.
#     - If `return_type` = 'check_string':
#       - If the `cmd` run exit code = 0 then the following args are used to evaluate the `CompletedProcess.stdout` field.
#         `success_status` is set to RTN_PASS or RTN_FAIL per the string checks, and returned with the
#         `CompletedProcess` structure.  String check failures are noted in `CompletedProcess.stderr`.
#       - If the `cmd` run exit code > 0 then RTN_FAIL and the `CompletedProcess` structure is returned.
   
#     `check_line_text` (str, default None)
#     - A qualifier for which line of `CompletedProcess.stdout` to look for `expected_text` and/or `not_text`
#     - If provided, only the first line containing this text is checked.  If not provided then
#     all lines of the `CompletedProcess.stdout` are checked.

#     `expected_text` (str, default None)
#     - Text that must be found in the `check_line_text` (or all of `CompletedProcess.stdout`)

#     `not_text`  (str, default None)
#     - Text that must NOT be found in the `check_line_text` (or all of `CompletedProcess.stdout`)
    
#     ### cfg dictionary params
#     `nTries` (int, default 2)
#     - Total number of times to attempt to execute the `cmd` if it returns an exit code > 0 or raises an exception

#     `RetryInterval` (float, default 0.5s)
#     - Wait time between `cmd` nTries

#     `SSH_timeout` (int, default 1s)
#     - Timeout used for SSH connections to remote hosts.
#     - _The value must be an integer number of seconds. Not a float._

#     ### Returns
#     - 2-tuple of `(success_status, subprocess.CompletedProcess())`
#       - `success_status` values:
#         - `RTN_PASS` - the `cmd` run exited with exit code = 0.  If `return_type`='check_string' then checks pass.  Any `cmd` output is in `CompletedProcess.stdout`.
#         - `RTN_FAIL` - the `cmd` run exited with exit code > 0, or an exception was raised, or `return_type`='check_string' checks fail.
#         `CompletedProcess.stderr` contains the failure data.
#         - `RTN_WARNING` - only for execution on a remote host, indicates an SSH connection failure

#       - If `return_type` = 'check_string':  `success_status` = 'RTN_PASS' if the `cmd` stdout response contains `expected_text` and not `not_text` 
#       (response line qualified by `check_line_text`), else `success_status` = 'RTN_FAIL'.

#       - The returned `CompletedProcess` structure contains these fields:
#         - `args` - the command string executed
#         - `returncode` - integer command execution status
#             - 0:  `cmd` executed successfully
#             - \>0: `cmd`-specific error exit code
#             - RTNCODE_REMOTE_TIMEOUT (252): Connection timeout to a remote host
#             - RTNCODE_ERROR (253): General exception 
#             - RTNCODE_TIMEOUT (254): Timeout during `cmd` execution 
#         - `stdout` - holds any text from a passing `cmd` execution
#         - `stderr` - holds any info on `cmd` execution errors and exceptions.  '\\n's are replaced with ' '.

#     - A ValueError exception is raised if the call to cmd_check has errors, such as invalid `return_type` or `user_host_port`.

#     ### Behaviors and rules
#     - If an exception is raised when trying to execute the `cmd` then the `CompletedProcess.returncode` field is set to
#     RTNCODE_TIMEOUT (254), RTNCODE_ERROR (253), or RTNCODE_REMOTE_TIMEOUT (252), and the `CompletedProcess.stderr` field carries the details. 
#     If used, these codes should be imported from this module.
#     - When unable to connect to a known host (DNS resolves) the failure information can vary, perhaps based on the `SSH_timeout` setting, including:
#       - (RTN_WARNING, CompletedProcess(returncode=252, stderr='Host <me@testhostx> connection failed:  TimeoutError: timed out'))
#       - (RTN_WARNING, CompletedProcess(returncode=253, stderr='Host <me@testhostx> connection failed:  timeout: timed out'))
#       - (RTN_WARNING, CompletedProcess(returncode=253, stderr='Host <me@testhostx> connection failed:  NoValidConnectionsError: [Errno None] Unable to connect to port 22 on ...'))
#     """

#     global host_connections

#     if return_type not in ['check_string', 'cmdrun']:
#         _msg = f"Invalid return_type <{return_type}> passed to cmd_check"
#         logging.error (f"ERROR:  {_msg}")
#         raise ValueError (_msg)

#     if isinstance(cmd, list):
#         cmd = ' '.join(cmd)

#     # TODO accept host only and get user & port from config, and auth file pointer
    
#     if 'host_connections' not in globals():
#         connections_manager(logging.INFO)

#     try:
#         connection_timeout = timevalue(globvars.config.getcfg('SSH_timeout', SSH_TIMEOUT)).seconds
#         host_conn = host_connections.get(user_host_port, connection_timeout=connection_timeout)
#     except TimeoutError as e:       # Connection/SSH timeout
#         error_msg = f"Host <{user_host_port}> connection failed:  {type(e).__name__}: {e}"
#         logging.debug(error_msg)
#         return (RTN_WARNING, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_REMOTE_TIMEOUT, stdout='', stderr=error_msg))
#     except Exception as e:
#         error_msg = f"Host <{user_host_port}> connection failed:  {type(e).__name__}: {e}"
#         logging.debug(error_msg)
#         return (RTN_FAIL, subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg))


#     error_msg = ''
#     ntries = globvars.config.getcfg('nTries', NTRIES)
#     for nTry in range (ntries):
#         try:
#             logging.debug(f"cmd try {nTry+1} on <{user_host_port}>:  <{cmd}>")
#             if user_host_port == 'local':
#                 run_try = host_conn.local(cmd, hide=True, warn=True, timeout=cmd_timeout)
#             else:
#                 run_try = host_conn.run(cmd, hide=True, warn=True, timeout=cmd_timeout)

#             run_result = subprocess.CompletedProcess(args=cmd, returncode=run_try.exited, stdout=run_try.stdout, stderr=run_try.stderr.replace('\n',' '))

#             if run_result.returncode > 0:           # no exception, but non-passing result
#                 error_msg = run_result.stderr
#                 logging.debug(f"cmd try {nTry+1} failed:  <{error_msg}>")
#             # logging.debug(f"cmd_check subprocess.run returned <{run_try}>")      # Uncomment for debug.  stdout can be huge.

#         except CommandTimedOut as e:
#             error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
#             run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_TIMEOUT, stdout='', stderr=error_msg)
#             logging.debug(f"cmd try {nTry+1} failed (exception):  {error_msg}")
#             continue

#         except Exception as e:
#             error_msg = type(e).__name__ + ": " + str(e).replace('\n',' ')
#             run_result = subprocess.CompletedProcess(args=cmd, returncode=RTNCODE_ERROR, stdout='', stderr=error_msg)
#             logging.debug(f"cmd try {nTry+1} failed (exception):  {error_msg}")
#             continue

#         if return_type == 'check_string':

#             # Isolate text line to check
#             if check_line_text is None:
#                 text_to_check = run_result.stdout
#             else:
#                 text_to_check = ''
#                 for line in run_result.stdout.split('\n'):
#                     if check_line_text in line:
#                         text_to_check = line
#                         break
#             if text_to_check == '':
#                 _msg = "No text_to_check!"

#             else:
#                 # Check for expected text
#                 if expected_text is not None:
#                     if expected_text in text_to_check:
#                         if not_text is not None:
#                             # But not not_text
#                             if not_text not in text_to_check:
#                                 return (RTN_PASS, run_result)   # check_string expected_text and not_text Pass exit
#                             else:
#                                 _msg = f"not_text <{not_text}> found in text_to_check"
#                         return (RTN_PASS, run_result)           # check_string expected_text Pass exit
#                     else:
#                         _msg = f"expected_text <{expected_text}> not found in text_to_check"
#                 else:
#                     # Check for not_text without expected_text
#                     if not_text is not None:
#                         if not_text not in text_to_check:
#                             return (RTN_PASS, run_result)       # check_string not_text Pass exit
#                         else:
#                             _msg = f"not_text <{not_text}> found in text_to_check"
#                     else:
#                         raise ValueError("expected_text and non_text can't both be None")

#             run_result.returncode = 1
#             run_result.stderr = _msg

#         else:   # return_type == 'cmdrun':
#             if run_result.returncode == 0:
#                 return (RTN_PASS, run_result)                   # cmdrun Pass exit

#         if nTry < ntries-1:
#             time.sleep (timevalue(globvars.config.getcfg('RetryInterval', RETRY_INTERVAL)).seconds)

#         # End of ntries loop

#     return (RTN_FAIL, run_result)                               # Fail exit after ntries


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
        