#!/usr/bin/env python3
"""LAN monitor

Monitor status of network resources, such as services, hosts, file system age, system update age, etc.
See README.md for descriptions of available plugins.

Operates interactively or as a service (loop forever and controlled via systemd or other).

In service mode
    kill -SIGUSR1 <pid>   outputs a summary to the log file
    kill -SIGUSR2 <pid>   outputs monitored items current status to the log file
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
#==========================================================

import sys
import argparse
import time
import datetime
import os.path
import signal
import collections

try:        # running as script not supported, so no default __version__ assignment
    import importlib.metadata
    __version__ = importlib.metadata.version(__package__ or __name__)
    # print ("Using importlib.metadata for __version__ assignment")
except:
    import importlib_metadata
    __version__ = importlib_metadata.version(__package__ or __name__)
    # print ("Using importlib_metadata for __version__ assignment")

from cjnfuncs.core import logging, set_toolname
from cjnfuncs.configman import config_item
from cjnfuncs.timevalue import timevalue
from cjnfuncs.mungePath import mungePath
from cjnfuncs.deployfiles import deploy_files
import cjnfuncs.core as core

import lanmonitor.globvars as globvars
import lanmonitor.lanmonfuncs as lanmonfuncs

sys.path.append (os.path.join(os.path.dirname(os.path.abspath(__file__))))      # Supplied plugins are in same folder


# Configs / Constants
TOOLNAME        = "lanmonitor"
CONFIG_FILE     = "lanmonitor.cfg"
PRINTLOGLENGTH  = 40


def main():
    global inst_dict
    # global config
    first = True
    inst_dict = {}
    notif_handlers_list = []
    monline = {}


    while 1:
        reloaded = globvars.config.loadconfig(flush_on_reload=True, call_logfile=None, call_logfile_wins=logfile_override)

        if not globvars.args.service:               # In service mode, logging level is set from config file
            if globvars.args.verbose == 1:
                logging.getLogger().setLevel(logging.INFO)
            elif globvars.args.verbose == 2:
                logging.getLogger().setLevel(logging.DEBUG)
            else:
                logging.getLogger().setLevel(logging.WARNING)

        if first:
            if globvars.args.service:
                time.sleep (timevalue(globvars.config.getcfg('StartupDelay', 0)).seconds)
            reloaded = True                         # Force calc of key and host padding lengths


        if reloaded:
            if not first:
                logging.warning(f"NOTE - The config file has been reloaded.")
            
            # Refresh the notifications handlers
            notif_handlers_list.clear()
            notif_handlers = globvars.config.getcfg("Notif_handlers", None)

            try:
                if notif_handlers is not None:
                    for handler in notif_handlers.split():      # Spaces not allowed in notif handler filename or path
                        xx = mungePath(handler)                 # Allow for abs path or rel to lanmonitor dir
                        xx_parent = str(xx.parent)
                        if xx_parent != '.'  and  xx_parent not in sys.path:
                            sys.path.append(xx_parent)
                        notif_plugin = __import__(xx.name)
                        logging.debug (f"Imported notification plugin <{xx.full_path}>, version <{notif_plugin.__version__}>")

                        notif_inst = notif_plugin.notif_class()
                        notif_handlers_list.extend([notif_inst])
            except Exception as e:
                logging.error (f"Unable to load notification handler <{handler}> - Aborting.\n  {e}")
                sys.exit(1)


            # Clear out all current instances, forcing re-setup
            inst_dict.clear()
            globvars.keylen = 0
            globvars.hostlen = 0
            for key in globvars.config.cfg:                 # Get keylen and hostlen field widths across all monitored items for pretty printing
                if key.startswith("MonType_"):
                    montype_tag = key.split("_")[1]
                    for line in globvars.config.cfg:
                        try:
                            if line.startswith(montype_tag + "_"):
                                if len(line) > globvars.keylen:
                                    globvars.keylen = len(line)
                                host = lanmonfuncs.split_user_host_port(globvars.config.cfg[line].split(maxsplit=1)[0])[1]
                                if len(host) > globvars.hostlen:
                                    globvars.hostlen = len(host)
                        except Exception as e:
                            pass    # Issue will be caught and logged in the following setup code


        # Process each monitor type and item
        checked_have_LAN_access = False
        for line in globvars.config.cfg:
            if line.startswith("MonType_"):
                montype_tag = line.split("_", maxsplit=1)[1]
                montype_plugin = globvars.config.cfg[line]
                xx = mungePath(montype_plugin)          # Allow for abs path or rel to lanmonitor dir
                xx_parent = str(xx.parent)              # xx.parent == "." if no path specified
                if xx_parent != '.'  and  xx_parent not in sys.path:
                    sys.path.append(xx_parent)
                plugin = __import__(xx.name)
                logging.debug (f"Imported monitor plugin <{xx.full_path}>, version <{plugin.__version__}>")

                # Process all items in cfg of this MonType
                for key in globvars.config.cfg:
                    if key.startswith(montype_tag + "_"):
                        # Instantiate the monitor item and call setup
                        # Line parsing (monline dict keys):
                        #   montype_xyz   pi@rpi3:80 CRITICAL  5m  xyz config specific
                        #   ^^^^^^^^^^^  key
                        #           ^^^  tag
                        #                 ^^^^^^^^^^ user_host_port
                        #                    ^^^^      host
                        #                            ^^^^^^^^  critical  (optional, case insensitive, saved as boolean)
                        #                                      ^^  check_interval (converted to sec)
                        #                                          ^^^^^^^^^^^^^^^^^^^  rest_of_line (parsed by plugin)

                        if key not in inst_dict:
                            # Set up the monitor item instance
                            try:
                                logging.debug("")
                                monline.clear()
                                monline["key"] = key
                                monline["tag"] = key.split("_", maxsplit=1)[1]
                                xx = globvars.config.cfg[key].split(maxsplit=1)
                                u_h_p = xx[0]
                                monline["user_host_port"] = u_h_p
                                _, host, _ = lanmonfuncs.split_user_host_port(u_h_p)
                                monline["host"] = host
                                monline["critical"] = False
                                yy = xx[1]
                                if yy.lower().startswith("critical"):
                                    monline["critical"] = True
                                    yy = yy.split(maxsplit=1)[1]
                                monline["check_interval"] = timevalue(yy.split(maxsplit=1)[0]).seconds
                                monline["rest_of_line"] = yy.split(maxsplit=1)[1]

                                inst = plugin.monitor()
                                rslt = inst.setup(monline)          # SETUP() CALL
                                    # setup successful returns RTN_PASS - remembered in inst_dict as instance pointer
                                    # setup hard fail  returns RTN_FAIL - remembered in inst_dict as False
                                    # Some plugins may need to interrogate the target host during setup.
                                    #   If the interrogation fails (i.e., can't access), then the plugin.setup should return
                                    #   RTN_WARNING.  The warning is logged, but no entry in the inst_dict is made 
                                    #   so that setup is retried on each iteration.
                                logging.debug (f"{key} - setup() returned:  {rslt}")
                                if rslt == lanmonfuncs.RTN_FAIL:
                                    _msg = f"MONITOR SETUP FOR <{key}> FAILED.  THIS RESOURCE IS NOT MONITORED."
                                    for notif_handler in notif_handlers_list:
                                        notif_handler.log_event({"rslt":lanmonfuncs.RTN_WARNING, "notif_key":key,
                                                    "message":f"  WARNING: {key} - {host} - {_msg}"})
                                    inst_dict[key] = False
                                elif rslt == lanmonfuncs.RTN_WARNING:
                                    _msg = f"MONITOR SETUP FOR <{key}> FAILED.  WILL RETRY."
                                    for notif_handler in notif_handlers_list:
                                        notif_handler.log_event({"rslt":lanmonfuncs.RTN_WARNING, "notif_key":key,
                                                    "message":f"  WARNING: {key} - {host} - {_msg}"})
                                elif rslt == lanmonfuncs.RTN_PASS:
                                    inst_dict[key] = inst
                                else:
                                    logging.critical (f"Setup for <{key}> returned illegal value {rslt} - Aborting.")
                                    sys.exit(1)
                            except Exception as e:
                                logging.warning (f"Malformed monitor item <{key}> - skipped:\n  {e}")
                                inst_dict[key] = False
                                continue


                        # Execute eval_status() for the item
                        inst = False
                        if key in inst_dict:
                            inst = inst_dict[key]
                        if inst is not False:       # See above setup() call notes
                            if inst.next_run > datetime.datetime.now():
                                logging.debug (f"{key} - Not due, skipped")
                            else:
                                inst.prior_run = datetime.datetime.now().replace(microsecond=0)
                                inst.next_run += datetime.timedelta(seconds=inst.check_interval)
                                # inst.next_run += datetime.timedelta(seconds=60)  # for debug

                                # For items that run >= daily, set the daily run time, if defined
                                if (first or reloaded)  and  globvars.config.getcfg("DailyRuntime", False)  and  (inst.check_interval >= 86400):
                                    try:
                                        target_hour   = int(globvars.config.getcfg("DailyRuntime").split(":")[0])
                                        target_minute = int(globvars.config.getcfg("DailyRuntime").split(":")[1])
                                        inst.next_run = inst.next_run.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                                    except Exception as e:
                                        logging.error (f"Cannot parse <DailyRuntime> in config:  {globvars.config.getcfg('DailyRuntime')} - Aborting")
                                        sys.exit(1)

                                logging.debug(f"{key} - Next runtime: {inst.next_run}")

                                # For checks to be run on remote hosts, ensure LAN access by pinging the config Gateway host, if defined.  Do only once per active serviceloop.
                                if (first or reloaded)  and  globvars.config.getcfg("Gateway", False) == False:
                                    checked_have_LAN_access = True
                                    have_LAN_access = True
                                if inst.host != "local"  and  not checked_have_LAN_access:
                                    checked_have_LAN_access = True
                                    have_LAN_access = lanmonfuncs.check_LAN_access()
                                    if not have_LAN_access:
                                        logging.warning(f"WARNING:  NO ACCESS TO LAN ({globvars.config.getcfg('Gateway')}) - Checks run on remote hosts are skipped for this iteration.")
                                    else:
                                        logging.debug(f"LAN access confirmed.  Proceeding with checks run on remote hosts.")

                                if inst.host == "local" or have_LAN_access: 
                                    rslt = inst.eval_status()                               # EVAL_STATUS() CALL
                                    logging.debug (f"{key} - eval_status() returned:  {rslt}")

                                    for notif_handler in notif_handlers_list:
                                        notif_handler.log_event(rslt)
        

        for notif_handler in notif_handlers_list:
            notif_handler.each_loop()

        for notif_handler in notif_handlers_list:
            notif_handler.renotif()

        for notif_handler in notif_handlers_list:
            notif_handler.summary()

        if not globvars.args.service:
            sys.exit(0)

        first = False
        time.sleep (timevalue(globvars.config.getcfg("ServiceLoopTime")).seconds)


globvars.sig_summary = False
globvars.sig_status  = False

def int_handler(sig, frame):
    logging.debug(f"Signal {sig} received.")
    if sig == signal.SIGUSR1:
        globvars.sig_summary = True
        return
    elif sig == signal.SIGUSR2:
        globvars.sig_status = True
        return
    else:
        sys.exit(1)

signal.signal(signal.SIGINT,  int_handler)      # Ctrl-C  (2)
signal.signal(signal.SIGTERM, int_handler)      # kill    (9)
signal.signal(signal.SIGUSR1, int_handler)      # User 1  (10)
signal.signal(signal.SIGUSR2, int_handler)      # User 2  (12)


def cli():
    global logfile_override
    set_toolname (TOOLNAME)

    parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--print-log', '-p', action='store_true',
                        help=f"Print the tail end of the log file (default last {PRINTLOGLENGTH} lines).")
    parser.add_argument('--verbose', '-v', action='count',
                        help="Display OK items in non-service mode. (-vv for debug logging)")
    parser.add_argument('--config-file', '-c', type=str, default=CONFIG_FILE,
                        help=f"Path to the config file (Default <{CONFIG_FILE})> in user/site config directory.")
    parser.add_argument('--service', action='store_true',
                        help="Enter endless loop for use as a systemd service.")
    parser.add_argument('--setup-user', action='store_true',
                        help=f"Install starter files in user space.")
    parser.add_argument('--setup-site', action='store_true',
                        help=f"Install starter files in system-wide space. Run with root prev.")
    parser.add_argument('-V', '--version', action='version', version=f"{core.tool.toolname} {__version__}",
                        help="Return version number and exit.")
    globvars.args = parser.parse_args()


    # Deploy template files
    if globvars.args.setup_user:
        deploy_files([
            { "source": CONFIG_FILE,          "target_dir": "USER_CONFIG_DIR", "file_stat": 0o644, "dir_stat": 0o755},
            { "source": "creds_SMTP",         "target_dir": "USER_CONFIG_DIR", "file_stat": 0o600},
            { "source": "lanmonitor.service", "target_dir": "USER_CONFIG_DIR", "file_stat": 0o644},
            ])
        sys.exit()

    if globvars.args.setup_site:
        deploy_files([
            { "source": CONFIG_FILE,          "target_dir": "SITE_CONFIG_DIR", "file_stat": 0o644, "dir_stat": 0o755},
            { "source": "creds_SMTP",         "target_dir": "SITE_CONFIG_DIR", "file_stat": 0o600},
            { "source": "lanmonitor.service", "target_dir": "SITE_CONFIG_DIR", "file_stat": 0o644},
            ])
        sys.exit()


    # Load config file and setup logging
    logfile_override = True  if not globvars.args.service  else False
    try:
        globvars.config = config_item(globvars.args.config_file)
        globvars.config.loadconfig(call_logfile_wins=logfile_override)
    except Exception as e:
        logging.error(f"Failed loading config file <{globvars.args.config_file}>. \
\n  Run with  '--setup-user' or '--setup-site' to install starter files.\n  {e}\n  Aborting.")
        sys.exit(1)


    logging.warning (f"========== {core.tool.toolname} {__version__}, pid {os.getpid()} ==========")
    logging.warning (f"Config file <{globvars.config.config_full_path}>")


    # Print log
    if globvars.args.print_log:
        try:
            _lf = mungePath(globvars.config.getcfg("LogFile"), core.tool.log_dir_base).full_path
            print (f"Tail of  <{_lf}>:")
            _xx = collections.deque(_lf.open(), globvars.config.getcfg("PrintLogLength", PRINTLOGLENGTH))
            for line in _xx:
                print (line, end="")
        except Exception as e:
            print (f"Couldn't print the log file.  LogFile defined in the config file?\n  {e}")
        sys.exit()


    sys.exit(main())
