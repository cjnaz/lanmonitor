#!/usr/bin/env python3
"""LAN monitor

Monitor status of network resources, such as services, hosts, file system age, system update age, etc.
See README.md for descriptions of available plugins.

Operates interactively or as a service (loop forever and controlled via systemd or other).

CLI (interactive) modes
   - No Items positional arg:  Run all monitor items once
   - Given Items positional arg "xyz host":  Run all monitor items containing either 'xyz' or 'host' substrings (case insensitive)
     in the monitor item name or the u@h:p field

In service mode
    kill -SIGUSR1 <pid>   outputs a summary to the log file
    kill -SIGUSR2 <pid>   outputs monitored items current status to the log file
"""

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
#==========================================================

import sys
import argparse
import time
import datetime
import os.path
import signal
import collections

try:
    import importlib.metadata
    __version__ = importlib.metadata.version(__package__ or __name__)
except:
    import importlib_metadata
    __version__ = importlib_metadata.version(__package__ or __name__)

from cjnfuncs.core import logging, set_toolname, set_logging_level, periodic_log
from cjnfuncs.configman import config_item
from cjnfuncs.timevalue import timevalue
from cjnfuncs.mungePath import mungePath
from cjnfuncs.deployfiles import deploy_files
import cjnfuncs.core as core

import lanmonitor.globvars as globvars
from   lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_DISREGARD, RTN_FAIL, check_LAN_access, split_user_host_port, host_connections

sys.path.append (os.path.join(os.path.dirname(os.path.abspath(__file__))))      # Supplied plugins are in same folder


# Configs / Constants
TOOLNAME =                      'lanmonitor'
CONFIG_FILE_DEFAULT =           'lanmonitor.cfg'
PRINT_LOG_LENGTH_DEFAULT =      40
LOOP_INTERVAL_DEFAULT =         '30s'
STARTUP_DELAY_DEFAULT =         '0s'
SERVICE_LOOPTIME_DEFAULT =      '10s'
DISREGARD_LOGLEVEL_DEFAULT=     30
DISREGARD_LOG_INTERVAL_DEFAULT= '1h'


#=====================================================================================
#=====================================================================================
#   m a i n
#=====================================================================================
#=====================================================================================

def main():
    global inst_dict
    global checked_have_LAN_access, have_LAN_access

    set_logging_level ({1:logging.INFO, 2:logging.DEBUG}.get(globvars.args.verbose, logging.INFO), save=False)
    inst_dict = {}
    setup_notif_handlers()                                              # Refresh the notifications handlers
    set_print_lengths()                                                 # Set pretty print field widths

    # Build list of all possible monitor items
        # Given in config file:
        # MonType_Freemem         freemem_plugin
        # Freemem_host3 =         {'u@h:p':'local', 'recheck':'30m', 'rol':'20%'} # 20%'}
    monitor_items_list = []
    for key in globvars.config.cfg:
        if key.startswith('MonType_'):                                  # 'MonType_Freemem'
            montype_tag = key.split('_')[1] + '_'                       # 'Freemem_'
            for key2 in globvars.config.cfg:
                if key2.startswith(montype_tag):
                    monitor_items_list.append(key2)


    # Run monitor items that have matches in the item name or u@h:p field (dict or str format)
    checked_have_LAN_access = have_LAN_access = False                   # Checked run_item()

    while 1:
        for item in globvars.args.Items:                                # Given CLI Items:  [ 'apt', 'host3' ]
            item = item.lower()

            for mon_item in monitor_items_list:
                runit = False

                if item in mon_item.lower():
                    runit = True
                elif isinstance(globvars.config.cfg[mon_item], dict):   # dict format
                    uhp = globvars.config.cfg[mon_item].get('u@h:p', ''.lower())
                    if item in uhp:
                        runit = True
                else:                                                   # str format
                    uhp = globvars.config.cfg[mon_item].split(maxsplit=1)[0].lower()
                    if item in uhp:
                        runit = True
        
                if runit:
                    logging.debug ("")
                    run_item(mon_item)
        
        if not globvars.args.loop:
            break
        else:
            inst_dict = {}
            time.sleep (timevalue(globvars.args.loop).seconds)
            print (f'\n{datetime.datetime.now().replace(microsecond=0)}')

    cleanup()
    return 0


#=====================================================================================
#=====================================================================================
#   s e r v i c e
#=====================================================================================
#=====================================================================================

def service():
    global inst_dict
    global checked_have_LAN_access, have_LAN_access
    global disregard_loglevel, disregard_log_interval

    first = True
    inst_dict = {}
    missing_config_file = False


    while True:
        try:
            # This code allows the config file to disappear (ie, network dropped) without
            # aborting.  Unhandled side effect:  If an _imported_ config file is not available then
            # the cfg will have been flushed and only partially reloaded, likely leading to a crash.
            reloaded = globvars.config.loadconfig(flush_on_reload=True,
                                         tolerate_missing=True,
                                         call_logfile_wins=call_logfile_override) #, ldcfg_ll=10)
            if reloaded == -1:      # config file not found
                if not missing_config_file:
                    missing_config_file = True
                    logging.warning(f"Can't find or load the config file <{globvars.config.config_full_path}> - skipping reload check")
            else:                   # config file found
                if missing_config_file:
                    missing_config_file = False
                    logging.warning(f"Config file <{globvars.config.config_full_path}> found again")
        except Exception as e:
            logging.error(f"Error when loading config file.  Aborting.\n  {type(e).__name__}: {e}")
            cleanup()
            return (1)

        if globvars.args.verbose is not None:
            set_logging_level ({1:logging.INFO, 2:logging.DEBUG}.get(globvars.args.verbose, logging.WARNING), save=False)


        if first:
            if globvars.args.service:
                time.sleep (timevalue(globvars.config.getcfg('StartupDelay', STARTUP_DELAY_DEFAULT)).seconds)
            reloaded = 1                            # Force calc of key and host padding lengths


        if reloaded == 1:
            if not first:
                logging.warning(f"The config file has been reloaded")
                cleanup()

            setup_notif_handlers()                  # Refresh the notifications handlers
            inst_dict.clear()                       # Clear out all current instances, forcing re-setup
            set_print_lengths()                     # Set pretty print field widths

            # Set control vars
            disregard_loglevel =                  globvars.config.getcfg('Disregard_LogLevel',     DISREGARD_LOGLEVEL_DEFAULT)
            disregard_log_interval =    timevalue(globvars.config.getcfg('Disregard_log_interval', DISREGARD_LOG_INTERVAL_DEFAULT)).seconds


        # --------------- TOP OF CHECK LOOP (NON-FIRST/RELOAD) ---------------

        # Process each monitor type and item
        monitor_items_list = []                             # Refresh this list on every iteration since some monitor items may have had setup warnings
        for key in globvars.config.cfg:
            if key.startswith('MonType_'):                  # 'MonType_Freemem'
                montype_tag = key.split('_')[1] + '_'       # 'Freemem_'
                for key2 in globvars.config.cfg:
                    if key2.startswith(montype_tag):
                        monitor_items_list.append(key2)

        checked_have_LAN_access = have_LAN_access = False
        for mon_item in monitor_items_list:
            run_item(mon_item)


        for notif_handler in notif_handlers_list:
            notif_handler.each_loop()

        for notif_handler in notif_handlers_list:
            notif_handler.renotif()

        for notif_handler in notif_handlers_list:
            notif_handler.summary()

        if not globvars.args.service:                       # interactive mode run all exit
            cleanup()
            return 0

        first = False
        time.sleep (timevalue(globvars.config.getcfg('ServiceLoopTime', SERVICE_LOOPTIME_DEFAULT)).seconds)


#=====================================================================================
#=====================================================================================
#   s e t u p _ n o t i f _ h a n d l e r s
#=====================================================================================
#=====================================================================================

def setup_notif_handlers():
    global notif_handlers_list

    notif_handlers_list = []
    notif_handlers = globvars.config.getcfg('Notif_handlers', None)

    try:
        if notif_handlers is not None:
            for handler in notif_handlers.split():              # Spaces not allowed in notif handler filename or path
                montype_plugin_mp = mungePath(handler)          # Allow for abs path or rel to lanmonitor dir
                montype_plugin_parent = str(montype_plugin_mp.parent)
                if montype_plugin_parent != '.'  and  montype_plugin_parent not in sys.path:
                    sys.path.append(montype_plugin_parent)
                notif_plugin = __import__(montype_plugin_mp.name)
                logging.debug (f"Imported notification plugin <{montype_plugin_mp.full_path}>, version <{notif_plugin.__version__}>")

                notif_inst = notif_plugin.notif_class()
                notif_handlers_list.extend([notif_inst])
    except Exception as e:
        logging.error (f"Unable to load notification handler <{handler}>.  Aborting.\n  {type(e).__name__}: {e}")
        cleanup()
        sys.exit(1)


#=====================================================================================
#=====================================================================================
#   s e t _ p r i n t _ l e n g t h s
#=====================================================================================
#=====================================================================================

def set_print_lengths():
    # Get keylen and hostlen field widths across all monitored items for pretty printing
    globvars.keylen = 0
    globvars.hostlen = 0

    for key in globvars.config.cfg:
        if key.startswith('MonType_'):
            montype_tag = key.split('_')[1] + '_'

            for key2 in globvars.config.cfg:
                try:
                    if key2.startswith(montype_tag):

                        # Capture max length of monitor item names
                        if (xx := len(key2)) > globvars.keylen:
                            globvars.keylen = xx

                        # Capture max length of host portion of uhp
                        item_def = globvars.config.cfg[key2]
                        if isinstance(item_def, dict):
                            uhp = item_def.get('u@h:p', '')     # dict format
                        else:
                            uhp = item_def.split(maxsplit=1)[0] # str format

                        if '@' in uhp:                          # not reference to host section
                            _, uhp, _ = split_user_host_port(uhp)

                        if (xx := len(uhp)) > globvars.hostlen:
                            globvars.hostlen = xx

                except Exception as e:
                    pass    # Issue will be caught and logged in the following setup code


#=====================================================================================
#=====================================================================================
#   r u n _ i t e m
#=====================================================================================
#=====================================================================================

def run_item(item_key):                                                     # Given item_key:  'Host_hostxyz'
        global notif_handlers_list
        global inst_dict
        global checked_have_LAN_access, have_LAN_access

        # Do one-time setup related stuff
        did_setup = False
        if item_key not in inst_dict:
            did_setup = True

            # Import monitor plugin if not already imported
            plugin_name = 'MonType_' + item_key.split('_', maxsplit=1)[0]   # 'MonType_Host'
            try:
                montype_plugin = globvars.config.getcfg(plugin_name)        # 'pinghost_plugin'
                plugin = sys.modules.get(montype_plugin)
                if not plugin:
                    montype_plugin_mp = mungePath(montype_plugin)           # Allow for abs or rel path to lanmonitor dir
                    montype_plugin_parent = str(montype_plugin_mp.parent)   # montype_plugin_parent == '.' if no path specified
                    if montype_plugin_parent != '.'  and  montype_plugin_parent not in sys.path:
                        sys.path.append(montype_plugin_parent)
                    plugin = __import__(montype_plugin_mp.name)
                    logging.debug (f"Imported <{plugin_name}> monitor plugin <{montype_plugin_mp.full_path}>, version <{plugin.__version__}>")
            except Exception as e:
                logging.error (f"Could not find monitor plugin <{plugin_name}>.  Aborting.\n  {type(e).__name__}: {e}")
                cleanup()
                sys.exit(1)


            # Instantiate the monitor item and call setup()
            monline = {}
            monline['key'] = item_key                                       # 'Host_hostxyz'
            monline['tag'] = item_key.split('_', maxsplit=1)[1]             # 'hostxyz'
            item_def = globvars.config.cfg[item_key]

            try:
                if isinstance(item_def, dict):
                    # Monitor item dict format
                        # Host_testhostY   {'u@h:p': 'local', 'critical':False, 'timeout':'1s', 'recheck':'1m', 'rol':'testhostY.cjn.lan'}
                    
                    # Required settings
                    monline['check_interval'] =     timevalue(item_def['recheck']).seconds
                    monline['rest_of_line'] =       item_def['rol']

                    # Default settings
                    monline['user_host_port'] =     monline['host'] = 'local'
                    monline['critical'] =           False
                    monline['cmd_timeout'] =        None

                    # Optional settings
                    for line_key in item_def:
                        if line_key.lower() == 'u@h:p':
                            uhp = item_def[line_key]
                            monline['user_host_port'] =     monline['host'] =  uhp
                            if '@' in uhp:
                                _, monline['host'], _ =     split_user_host_port(uhp)
                        elif line_key.lower() == 'critical':
                            monline['critical'] =           item_def[line_key]
                        elif line_key.lower() == 'timeout':
                            monline['cmd_timeout'] =        timevalue(item_def[line_key]).seconds
                        elif line_key.lower() in ['recheck', 'rol']:
                            pass
                        else:
                            raise ValueError (f"Error in line <{item_key}>:  Unknown key <{line_key}>")

                else:
                    # Monitor item str format
                        #   montype_xyz   pi@rpi3:80 CRITICAL  5m  xyz config specific
                        #   ^^^^^^^^^^^  key
                        #           ^^^  tagcmd_timeout
                        #                 ^^^^^^^^^^ user_host_port
                        #                    ^^^^      host
                        #                            ^^^^^^^^  critical  (optional, case insensitive, saved as boolean)
                        #                                      ^^  check_interval (converted to sec)
                        #                                          ^^^^^^^^^^^^^^^^^^^  rest_of_line (parsed by plugin)

                    item_def = globvars.config.cfg[item_key].split(maxsplit=1)
                    uhp = item_def[0]
                    monline['user_host_port'] =     monline['host'] =  uhp
                    if '@' in uhp:
                        _, monline['host'], _ =     split_user_host_port(uhp)
                    monline['critical'] =           False
                    yy = item_def[1]
                    if yy.lower().startswith('critical'):
                        monline['critical'] =       True
                        yy = yy.split(maxsplit=1)[1]
                    monline['cmd_timeout'] =        None
                    monline['check_interval'] =     timevalue(yy.split(maxsplit=1)[0]).seconds
                    monline['rest_of_line'] =       yy.split(maxsplit=1)[1]


                # Call setup()
                item_inst = plugin.monitor()
                setup_result = item_inst.setup(monline)
                logging.debug (f"{item_key} - setup() returned:  {setup_result}")
                    # setup successful returns RTN_PASS - remembered in inst_dict as instance pointer
                    # setup hard fail  returns RTN_FAIL - remembered in inst_dict as False
                    # Some plugins may need to interrogate the target host during setup.
                    #   If the interrogation fails (i.e., can't access), then the plugin.setup should return
                    #   RTN_WARNING.  The warning is logged, but no entry in the inst_dict is made 
                    #   so that setup is retried on each iteration.
                    # setup may return RTN_DISREGARD which causes this code to periodic_log the event but ignore the 
                    # call result and retry on the next iteration.  Effectively this is the same as RTN_WARNING
                    # but not sent to the notification handlers.  DISREGARD_LOGLEVEL_DEFAULT= 30 and 
                    # DISREGARD_LOG_INTERVAL_DEFAULT = '1h' may be overridden in the config file.


                if setup_result == RTN_FAIL:
                    _msg = f"MONITOR SETUP FOR <{item_key}> FAILED.  THIS RESOURCE IS NOT MONITORED."
                    for notif_handler in notif_handlers_list:
                        notif_handler.log_event({'rslt':RTN_WARNING, 'notif_key':item_key,
                                    'message':f"  WARNING: {item_key} - {monline['host']} - {_msg}"})
                    inst_dict[item_key] = False
                    return

                elif setup_result == RTN_WARNING:
                    _msg = f"MONITOR SETUP FOR <{item_key}> FAILED.  WILL RETRY."
                    for notif_handler in notif_handlers_list:
                        notif_handler.log_event({'rslt':RTN_WARNING, 'notif_key':item_key,
                                    'message':f"  WARNING: {item_key} - {monline['host']} - {_msg}"})
                    return

                elif setup_result == RTN_DISREGARD:
                    _msg = f"MONITOR SETUP FOR <{item_key}> DISREGARDED.  WILL RETRY."
                    _cat = item_key + 'setup_disregarded'
                    periodic_log (_msg, category=_cat, log_interval=disregard_log_interval, log_level=disregard_loglevel)
                    return

                elif setup_result == RTN_PASS:
                    inst_dict[item_key] = item_inst

                else:
                    logging.error (f"Setup for <{item_key}> returned illegal value {setup_result}.  Aborting.")
                    cleanup()
                    sys.exit(1)

            except Exception as e:
                logging.exception (f"Malformed monitor item <{item_key}>.  Skipped.\n  {type(e).__name__}: {e}")
                inst_dict[item_key] = False
                return


        # Check monitor item status - call eval_status()
        item_inst = inst_dict.get(item_key, False)
        if item_inst is not False:                      # See above setup() call notes for RTN_FAIL
            if datetime.datetime.now() < item_inst.next_run:
                logging.debug (f"{item_key} - Not due, skipped")
            else:
                item_inst.prior_run = datetime.datetime.now().replace(microsecond=0)
                item_inst.next_run += datetime.timedelta(seconds=item_inst.check_interval)
                # inst.next_run += datetime.timedelta(seconds=60)  # for debug

                # For items that run >= daily, set next_run to the daily run time, if defined (Needs to only be done once.)
                if did_setup  and  globvars.config.getcfg('DailyRuntime', False)  and  (item_inst.check_interval >= 86400):
                    try:
                        target_hour   = int(globvars.config.getcfg('DailyRuntime').split(':')[0])
                        target_minute = int(globvars.config.getcfg('DailyRuntime').split(':')[1])
                        item_inst.next_run = item_inst.next_run.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
                    except Exception as e:
                        logging.error (f"Cannot parse <DailyRuntime> in config:  {globvars.config.getcfg('DailyRuntime')}.  Aborting.\n  {type(e).__name__}: {e}")
                        cleanup()
                        sys.exit(1)
                logging.debug(f"{item_key} - Next runtime: {item_inst.next_run}")

                # For checks to be run on remote hosts, ensure LAN access by pinging the config Gateway host, if defined.  Do only once per serviceloop.
                if item_inst.host != 'local'  and  not checked_have_LAN_access:
                    checked_have_LAN_access = True
                    have_LAN_access = check_LAN_access()
                    if not have_LAN_access:
                        logging.warning(f"WARNING:  NO ACCESS TO LAN ({globvars.config.getcfg('Gateway')}) - Checks run on remote hosts are skipped for this iteration.")
                    else:
                        logging.debug(f"LAN access confirmed - proceeding with checks run on remote hosts")

                # Call eval_status()
                    # Plugin eval_status returns dictionary with these keys:
                    #     rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_DISREGARD, RTN_FAIL, RTN_CRITICAL
                    #     notif_key       Unique handle for tracking active notifications in the notification handler
                    #     message         String with status and context details
                if item_inst.host == 'local' or have_LAN_access: 
                    eval_result = item_inst.eval_status()
                    logging.debug (f"{item_key} - eval_status() returned:  {eval_result}")

                    if eval_result['rslt'] == RTN_DISREGARD:
                        _msg = f"MONITOR EVAL_STATUS() CALL FOR <{item_key}> DISREGARDED:  <{eval_result}>"
                        _cat = item_key + 'eval_status_disregarded'
                        periodic_log (_msg, category=_cat, log_interval=disregard_log_interval, log_level=disregard_loglevel)
                    else:
                        for notif_handler in notif_handlers_list:
                            notif_handler.log_event(eval_result)



#=====================================================================================
#=====================================================================================
#   c l e a n u p
#=====================================================================================
#=====================================================================================

def cleanup():
    host_connections.close('all')


#=====================================================================================
#=====================================================================================
#   tool script infrastructure stuff
#=====================================================================================
#=====================================================================================

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
        cleanup()
        sys.exit(1)

signal.signal(signal.SIGINT,  int_handler)      # Ctrl-C  (2)
signal.signal(signal.SIGTERM, int_handler)      # kill    (9)
signal.signal(signal.SIGUSR1, int_handler)      # User 1  (10)
signal.signal(signal.SIGUSR2, int_handler)      # User 2  (12)


def cli():
    global call_logfile_override
    set_toolname (TOOLNAME)

    parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('Items', nargs='*',
                        help=f"Run the individual check item(s) or MonTypes")
    parser.add_argument('--print-log', '-p', nargs='?', const=PRINT_LOG_LENGTH_DEFAULT, type=int,
                        help=f"Print the tail end of the log file, eg --print-log 100 (default last {PRINT_LOG_LENGTH_DEFAULT} lines).")
    parser.add_argument('--verbose', '-v', action='count',
                        help="Display OK items in non-service mode. (-vv for debug logging)")
    parser.add_argument('--loop', nargs='?', const=LOOP_INTERVAL_DEFAULT, type=str,
                        help=f"Loop on Items indefinately (default interval {LOOP_INTERVAL_DEFAULT}).")
    parser.add_argument('--config-file', '-c', type=str, default=CONFIG_FILE_DEFAULT,
                        help=f"Path to the config file (Default <{CONFIG_FILE_DEFAULT})> in user/site config directory.")
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
            { 'source': CONFIG_FILE_DEFAULT,  'target_dir': 'USER_CONFIG_DIR', 'file_stat': 0o644, 'dir_stat': 0o755},
            { 'source': 'creds_SMTP',         'target_dir': 'USER_CONFIG_DIR', 'file_stat': 0o600},
            { 'source': 'lanmonitor.service', 'target_dir': 'USER_CONFIG_DIR', 'file_stat': 0o644},
            ])
        return 0

    if globvars.args.setup_site:
        deploy_files([
            { 'source': CONFIG_FILE_DEFAULT,  'target_dir': 'SITE_CONFIG_DIR', 'file_stat': 0o644, 'dir_stat': 0o755},
            { 'source': 'creds_SMTP',         'target_dir': 'SITE_CONFIG_DIR', 'file_stat': 0o600},
            { 'source': 'lanmonitor.service', 'target_dir': 'SITE_CONFIG_DIR', 'file_stat': 0o644},
            ])
        return 0


    # Load config file and setup logging
    call_logfile_override = True  if not globvars.args.service  else False
    try:
        globvars.config = config_item(globvars.args.config_file)
        globvars.config.loadconfig(call_logfile_wins=call_logfile_override) #, ldcfg_ll=10)
    except Exception as e:
        logging.error(f"Failed loading config file <{globvars.args.config_file}>. \
\n  Run with  '--setup-user' or '--setup-site' to install starter files.  Aborting.\n  {type(e).__name__}: {e}")
        return 1


    logging.warning (f"========== {core.tool.toolname} {__version__}, pid {os.getpid()} ==========")
    logging.warning (f"Config file <{globvars.config.config_full_path}>")


    # Print log
    if globvars.args.print_log:
        try:
            _lf = mungePath(globvars.config.getcfg('LogFile'), core.tool.log_dir_base).full_path
            print (f"Tail of  <{_lf}>:")
            _xx = collections.deque(_lf.open(), globvars.args.print_log)
            for line in _xx:
                print (line, end='')
        except Exception as e:
            print (f"Couldn't print the log file.  LogFile defined in the config file?\n  {type(e).__name__}: {e}")
        return 0


    # Run in service or interactive modes
    if globvars.args.service:
        return service()

    if len(globvars.args.Items) == 0:           # Interactive mode run all
        if globvars.args.verbose is None:
            globvars.args.verbose = 1
        return service()
    else:
        if globvars.args.loop:                  # Disable notifications when looping
            globvars.config.cfg['SMTP']['DontEmail'] = True
        return main()                           # Interactive mode for specified items

    
if __name__ == '__main__':
    sys.exit(cli())