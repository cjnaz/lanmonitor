## Debug features:
- lanmonitor dynamically reloads the config file when it senses that the config file has been changed.  When reloaded, all monitored items are reinitialized per the current content of the config file, and all prior monitored items and their history are discarded.  All setting may be changed, such as the core tool parameters, notification handler parameters, and setups on monitored items.
- Setting LogLevel to 10 in the config file enables debug level logging to the log file while running in service mode.
- Running interactively with `-vv` enables debug level logging to the console.  A summary report is also produced, which allows checking summary report operations and content.
- Sending a SIGUSR1 signal to lanmonitor when running in service mode causes a summary to be generated to the log file.
- Sending a SIGUSR2 signal to lanmonitor when running in service mode causes a dump of the current status of all monitored items, including prior runtime, next runtime, and any alert messages.  
- To send signals to a running lanmonitor service process use the `kill -<signal> <pid>` command (eg, `$ kill -SIGUSR1 7829`).  The process pid is printed in the startup banner to the log, or may be found using `ps`.
- Monitor item plugins have companion test case files.  Copy a plugin and its test file from the repo to a working directory, then run the test file (eg, `$ ./fsactivity_plugin_test.py`).

<br/>

---

## Known issues:
- none

<br/>

---

## Version history
- 3.3 240805 - Tolerate temporarily missing config file, support dictionary-style monitor item definitions, support cmd_timeout per monitored item, extract plugin descriptions from plugin docstring, New freemem_plugin.
- 3.2.2 240526 - yum_update_history_plugin command match bug fixes.
- 3.2 240105 - Adjusted for cjnfuncs V2.1. fsactivity plugin supports missing file. yum_update_history_plugin now requires full command match.
- 3.1 230320 - Plugins now distinguish between ssh access issues and real failures when checking on remote hosts.  
Added cfg param ssh_timeout, fixed cmd_check command fail retry bug, added pinghost_plugin_timeout.
  cmd_check returns RTN_PASS, RTN_FAIL, RTN_WARNING (for remote ssh access issues)
- 3.0.2 230226 - Converted to package format, updated to cjnfuncs 2.0.
- V2.0  221130 - Changed to check_interval per item.  Added `freespace` and `apt_upgrade_history` plugins.  Removed --once switch, replaced with --service switch.  Removed config RecheckInterval, replaced with ServiceLoopTime.  - Added `--print-log` switch.  Tuned up debug logging for plugin development.  Fixed summaries disable bug.
- V1.5  221120 - Added apt_upgrade_history plugin, Added `--print-log` switch, Fixed summaries disable bug.
- V1.4  220420 - Updated for funcs3.py V1.1 - Log file setup now in config file, timevalue & retime moved to funcs3.  SummaryDays bug and doc fix.  A couple corner case bug fixes.
- V1.2  210605 - Reworked have_access check to check_LAN_access logic.
- V1.1  210523 - Added loadconfig flush_on_reload (funcs3.py V0.7) to purge any deleted cfg keys.  Error formatting tweaks.  Cmd timeout tweaks
- V1.0  210507 - Major refactor
- V0.1  210129 - New