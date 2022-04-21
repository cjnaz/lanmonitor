# lanmonitor - Keeping watch on the health of your network resources

lanmonitor tracks the state of SELinux, hosts, services, web pages, processes, and local filesystem age on machines (hosts/VMs/servers...) on the local area network (and beyond).  
A text message notification (and/or email) is sent for any/each monitored _item_ that's out of sorts (not running, not responding, ...).  Periodic re-notifications are sent for
critical items, such as firewalld being down, and summary reports are generated up to daily.

` `
## Notable changes since prior release
- `LoggingLevel` in the config file has been changed to `LogLevel`
- The `--log-file` command line switch has been removed.  Now, specify `LogFile` in the config file.

` `  
## Usage
```
$ ./lanmonitor -h
usage: lanmonitor [-h] [-1] [-v] [--config-file CONFIG_FILE] [-V]

LAN monitor

Monitor status of items on the local network, such as services, hosts, file system age, etc.
Plugins are provided for these items, and additional plugins may easily be added:
    SELinux status
    Hosts ping response
    Systemd services active and running
    Web pages responding with expected text
    Processes existing
    Filesystem age

Operates interactively with --once switch, or as a service (loop forever and controlled via systemd or other).
V1.4 220420

optional arguments:
  -h, --help            show this help message and exit
  -1, --once            Single run mode.  Logging is to console rather than file.
  -v, --verbose         Display OK items in --once mode. (-vv for debug logging)
  --config-file CONFIG_FILE
                        Path to config file (default </mnt/share/dev/python/lanmonitor/github/lanmonitor.cfg>).
  -V, --version         Return version number and exit.
```

` `  
## Example output
```
$ ./lanmonitor --once --verbose
SELinux_local             OK - local    - enforcing
Host_RPi2_TempMon         OK - local    - rpi2.lan
Host_Printer_Server       OK - local    - 192.168.1.44
FAIL: Host_RPi3_from_RPi1 - rpi1.lan    - HOST RPi3.lan IS NOT RESPONDING
Service_routermonitor     OK - local    - routermonitor
Service_wanstatus         OK - local    - wanstatus
Service_plexmediaserver   OK - local    - plexmediaserver
Service_firewalld         OK - local    - firewalld
CRITICAL: Service_xxx - local - SERVICE xxx IS NOT RUNNING
Page_WeeWX                OK - local    - http://192.168.33.72/weewx/
Page_xBrowserSync         OK - rpi2     - https://www.xbrowsersync.org/
FAIL: Page_xxx - local - WEBPAGE http://localhost/xxx/ NOT FOUND
Process_x11vnc            OK - local    - /usr/bin/x11vnc
Process_tempmon           OK - RPi2.lan - python TempMon.py
WARNING: Process_xxxPi3 - RPi3.lan - HOST CANNOT BE REACHED
Activity_Win1_Image       OK - local    -    5.8 days  (   6 days  max)  /mnt/share/backups/Win1/Image/
FAIL: Activity_Win2_Image  STALE FILES - local -    6.7 days  (   6 days  max)  /mnt/share/backups/Win2/Image/
Activity_CentOS_backupsd  OK - local    -    0.7 days  (   8 days  max)  /mnt/share/backups/Shop2/
WARNING: Activity_xxx - local - COULD NOT GET ls OF PATH </mnt/share/backups/xxx/>
Activity_TiBuScrape       OK - local    -    3.9 days  (   4 days  max)  /mnt/share/backups/TiBuScrapeArchive/
Activity_RPi2_log.csv     OK - rpi2     -    0.8 mins  (   5 mins  max)  /mnt/RAMDRIVE/log.csv
```

` `  
## Setup and Usage notes
- Supported on Python3.6+ only.  Developed on Centos 7.9 with Python 3.6.8 / 3.7.
- Place the files in a directory on your server.

- Edit the config info in the `lanmonitor.cfg` file for the **Core tool parameters**:
  - `nRetries` sets how many tries will be made to accomplish each monitored item.
  - `RetryInterval` sets the time between nRetries.
  - `StartupDelay` is a wait time when starting in service mode to allow everything to come up fully (or crash) at system boot before checking items.
  - `RecheckInterval` sets how long between rechecks in service mode.
  - `Gateway` is any reliable host on your LAN (typically your router) that will be checked for access as a gate for any monitor items to be run from other hosts.  For example, the above `Process_tempmon` item will only run if the `Gateway` host can be accessed.
  - `LogLevel` controls what gets written to the log file.  At LogLevel 30 (the default if not specified), only warning/fail/critical events are logged.  LogLevel 20 logs passing events also.
  - `LogFile` specifies the log file.  The path may be absolute or relative to the script's directory.

- Edit the config info in the `lanmonitor.cfg` file for the **notification handler parameters**:
  - `Notif_handlers` is a whitespace separated list of Python modules (without the .py extension) that will handle monitored item event tracking, notifications, and periodic summaries.  `stock_notify.py` is provided, and has full functionality.  See Notification Handlers, below.
  - `CriticalReNotificationInterval` sets how long between repeated notifications for any failing CRITICAL monitored items in service mode.  (Used by the `stock_notif.py` notification handler.)
  - `SummaryDays` sets which days of the week for summaries to be emailed.  Monday =1, Tuesday =2, ... Saturday =6, Sunday = 7.  Multiple days may be selected.  Comment out `SummaryDays` to eliminate summaries.  (Used by the `stock_notif.py` notification handler.)
  - `SummaryTime` sets the time of day (local time) for summaries to be emailed.  24-clock format, for example, `13:00`.  (Used by the `stock_notif.py` notification handler.)
  - `LogSummary`, if True, forces the content of the periodic summary to be sent to the log file.  (Used by the `stock_notif.py` notification handler.)

- Edit the config info in the `lanmonitor.cfg` file for the **SMTP email parameters**.
  - Enter your mail `EmailFrom` and `NotifList`, and `EmailTo` addresses, and import your email credentials file:  `import /home/<user>/creds_SMTP`. (Any, none, or all parameters may be moved to an imported config file.)
  - Create an SMTP/email credentials file such as `/home/<user>/creds_SMTP` in your home directory and set the file protections to mode `600`, containing:

            EmailServer       mail.mailserver.com
            EmailServerPort   P587TLS                 # One of: P465, P587, P587TLS, or P25   
            EmailUser	      yourusername@mailserver.com
            EmailPass	      yourpassword
  

- See below for monitored item settings.
- Run the tool with `<path to>lanmonitor --once --verbose`.  Make sure that the local machine and user has password-less ssh access to any remote machines.  (`-vv` turns on debug logging.)
- Install lanmonitor as a systemd service (google how).  An example `lanmonitor.service` file is provided.  Note that the config file may be modified while the service is running, with changes taking effect on the next RecheckInterval.  Make sure that the user that the service runs under (typically root) has ssh password-less access to any remotes.
- stock_notif sends a text message for each monitored item that is in a FAIL or CRITICAL state.  CRITICAL items have a repeated text message sent after the `CriticalReNotificationInterval`.  Notifications are typically sent as text messages, but may be (also) directed to regular email addresses.
- stock_notif also sends a periodic summary report listing any current warnings/fails/criticals, or that all is well.  Summaries are typically sent as email messages.
- NOTE:  All time values in the config file may be entered with a `s` (seconds), `m` (minutes), `h` (hours), `d` (days), or `w` (weeks) suffix.  For example `6h` is 6 hours.  If no suffix is provided the time value is taken as seconds.

` `  
## Monitored items setup
Items to be monitored are defined in the `lanmonitor.cfg` file.  "Plugin" modules provide the logic for each monitored item type.  Several plugins are described below.  See the module description at the top of each module for functional and configuration specifics.
To activate a given plugin, a `MonType_` line is included in the configuration file using this format:

      MonType_<type>    <plugin_name>

1. Begins with the `MonType_` prefix
2. The `<type>` is used as the prefix on successive lines for monitor items of this type
3. The `<plugin_name>` is the Python module name (implied .py suffix)


For monitored items, the general format of a line is

      <type>_<friendly_name>  <local or user@host[:port]>  [CRITICAL (optional)]  <rest_of_line>

1. `<type>` matches the corresponding `MonType_<type>` line.
2. `<friendly_name>` is arbitrary and is used for notifications, logging, etc. `<type>_<friendly_name>` must be unique.
3. `<local or user@host[:port]>` specifies _on which machine the check will be executed from._  If not `local`, then `user@host` specifies the ssh login on the remote machine.  For example, the `Host_Yahoo` line below specifies that `Yahoo.com` will be pinged from the `RPi2.mylan` host by doing an `ssh me@RPi2.mylan ping Yahoo.com`.  The default ssh port is 22, but may be specified via the optional `:port` field.
4.  `CRITICAL` may optionally be specified.  CRITICAL tagged items are those that need immediate attention.  Renotifications are sent for these when failing by the `stock_notif.py` notification handler.
5. `<rest_of_line>` are the monitored type-specific settings.

` `  
### Supplied plugins

See the documentation header in each plugin for its functionality and configuration specifics.  Not all plugins are listed here.

- **SELinux** checks that the sestatus _Current mode:_ value matches the config file value.

      MonType_SELinux		selinux_plugin
      SELinux_<friendly_name>  <local or user@host>  [CRITICAL]  <enforcing or permissive>
      SELinux_localhost     local             enforcing


- **Hosts** to be monitored are listed on separate lines, as below.  Each host is pinged.  The `friendly_name` is user defined (not the real hostname).  `<IP address or hostname>` may be internal (local LAN) or external.

      MonType_Host		pinghost_plugin
      Host_<friendly_name>  <local or user@host>  [CRITICAL]  <IP address or hostname>
      Host_RPi1_HP1018    local    CRITICAL 192.168.1.44
      Host_Yahoo          me@RPi2.mylan    Yahoo.com

- **Services** to be monitored are listed on separate lines, as below.  Each service name is checked with a `systemctl status <service name>` (for systemd) or `service <service_name> status` (for init), checking for the active/running response.

      MonType_Service		service_plugin
      Service_<friendly_name>  <local or user@host>  [CRITICAL]  <service name>
      Service_firewalld       local			CRITICAL  firewalld
      Service_RPi1_HP1018     me@RPi1.mylan     cups

- **Web pages** to be monitored are listed on separate lines, as below.  Each URL is read and checked for the `<expected text>`, which starts at the first non-white-space character after the URL and up to the end of the line or a `#` comment character.  Leading and trailing white-space is trimmed off.  The url may be on a remote server.

      MonType_Page		webpage_plugin
      Page_<friendly_name>  <local or user@host>  [CRITICAL]  <url>  <expected text>
      Page_WeeWX              local             http://localhost/weewx/             Current Conditions
      Page_xBrowserSync       me@RPi2.mylan     https://www.xbrowsersync.org/       Browser syncing as it should be: secure, anonymous and free! # Check it out!

- **Processes** to be monitored are listed on separate lines, as below.  Each process is checked by seeing if the `<executable path>` occurs in the output of a `ps -Af` call.  

      MonType_Process		process_plugin
      Process_<friendly_name>  <local or user@host>  [CRITICAL]  <executable path>
      Process_x11vnc		local       CRITICAL  /usr/bin/x11vnc


- **Filesystem activities** to be monitored are listed on separate lines, as below.  The age of files at the `<path to directory or file>` is checked for at least one file being more recent than `<age>` ago.  Age values are the allowed time values (see note up above).  Note that sub-directories are not recursed - only the listed top-level directory is checked for the newest file.

      MonType_Activity	fsactivity_plugin
      Activity_<friendly_name>  <local or user@host>  [CRITICAL]  <age>  <path to directory or file>
      Activity_MyServer_backups     local       8d    /mnt/share/MyServerBackups
      Activity_RPi2_log.csv         rpi2.mylan  CRITICAL  5m    /mnt/RAMDRIVE/log.csv

- **Network interfaces** to be monitored are listed on separate lines, as below.  Each interface is checked with a `ifconfig <interface name>`, checking for 'UP' and 'RUNNING'.

      MonType_Interface         interface_plugin
      Interface_<friendly_name>  <local or user@host>  [CRITICAL]  <interface name>
      Interface_router_vlan0  local       CRITICAL  vlan0

- **Yum update age** on your various hosts to be monitored is listed on separate lines, as below.
yum history output is checked for the specific <yum_command> text and the date is extracted from
the first occurrence this line.  May require root access in order to read yum history.

      MonType_YumUpdate  yum_update_history_plugin
      YumUpdate_<friendly_name>  <local or user@host>  [CRITICAL]  <age>  <yum_command>
      YumUpdate_MyHost        local       CRITICAL  15d  update --skip-broken

- **dd-wrt age** on your various routers to be monitored is listed on separate lines, as below.
routerIP may be an IP address or hostname.  The dd-wrt hostname or IP /Info.htm page is checked for the date on the top right of the page.

      MonType_DD-wrt_age  dd-wrt_age_plugin
      DD-wrt_age_<friendly_name>  <local or user@host>  [CRITICAL]  <age>  <routerIP>
      DD-wrt_age_Router       local       CRITICAL  30d  192.168.1.1

` `  
## Writing Monitor Plugins

New plugins may be added easily.  The core lanmonitor code provides a framework for configuration, logging, command retries, and parsing components.  The general process for creating a new plugin is:

- Copy an existing plugin, such as the webpage_plug.py
- Adjust the module comment block to describe the functionality and config file details
- Within the `setup()` function
  - Adjust the `rest_of_line` parsing, creating new vars as needed
  - Add any checker code to validate these new values.  
- Within the `eval_status()` function
  - Adjust the `cmd` for your needed subprocess call command
  - The `cmd_check()` function can check the returncode or return text.  It also returns the full subprocess call response.  _See the cmd_check function within the lanmonfuncs.py module for built-in checking features._  Uncomment the `# print (rslt)` line to see what's available for building response checker code.
  - Adjust the `if rslt[0] == True: … return` lines for the PASS, FAIL/CRITICAL return text.  The `key_padded` and `host_padded` vars are used on the PASSing line for pretty printing.
- Adjust the tests at the bottom to exercise all possible good, bad, and invalid conditions.
- Add the `MonType_<your_monitor_type> <your_plugin_name>` line and specific monitor items to your config file.

` `  
### Additional plugin writing notes
1. The `setup()` function of your module will be called for each `<type>_<friendly_name>` line in the config file.  Setup is called only once at initial startup and after any on-the-fly edits to the configuration file.  Setup is supplied a dictionary:

        """ Set up instance vars and check item values.
        Passed in item dictionary keys:
            key             Full 'itemtype_tag' key value from config file line
            tag             'tag' portion only from 'itemtype_tag' from config file line
            user_host_port  'local' or 'user@hostname[:port]' from config file line
            host            'local' or 'hostname' from config file line
            critical        True if 'CRITICAL' is in the config file line
            rest_of_line    Remainder of line after the 'user_host' from the config file line

    - Setup must return RTN_PASS, RTN_WARNING, or RTN_FAIL.  If RTN_FAIL the setup failure is permanent and the item will not be monitored (but will be retried again after a config file edit).  If RTN_WARNING the setup will be retried on the next checking iteration, thus allowing for intermittent issues during setup.  Warnings and Fails are logged.
    - Within setup, commands may optionally be executed on the target machine for determining setup specifics (see the `Service_plugin` for an example).  NOTE that `check_LAN_access` (see next section) is NOT called before the setup calls, so setup failures might be due to no network access, or due to ssh access issues to the target machine.

2. The `eval_status()` function is called on each checking iteration.  Your plugin needs to return a dictionary with 3 keys:

        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details

      - `cmd_check()` in lanmonfuncs provides checking features such as command execution with retries, ssh for remote hosts, and check strings in the command response.  The raw command output is also returned so that your code can construct specific checks. Uncomment the `# print (rslt)` line to see the available response data. See the lanmonfuncs module for cmd_check feature details and the return structure.
      - If the host is not `local` then the lanmonitor core will check that the local machine has access to the LAN by pinging the the `Gateway` host defined in the config file.  This `check_LAN_access` check is performed only once per check iteration.  Thus, your eval_status code can assume that the LAN is accessible.  It is recommended that you include a `Host_<myhost>` check prior in the config file to limit fail ambiguity.

3. The plugin module may be tested standalone by running it directly on the command line.  Add tests to exercise your checking logic for both local and remote hosts, and for any warning/error traps.

            dotest ({"key":"SELinux_local", "tag":"local", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"enforcing"})

            dotest ({"key":"SELinux_RPiX", "tag":"RPiX", "host":"RPiX", "user_host_port":"pi@rpiX", "critical":True, "rest_of_line":"enforcing"})

            dotest ({"key":"SELinux_RPi2", "tag":"RPi2", "host":"rpi2.lan", "user_host_port":"pi@rpi2.lan", "critical":False, "rest_of_line":"enforcing"})

            dotest ({"key":"SELinux_badmode", "tag":"Shop2", "host":"local", "user_host_port":"local", "critical":True, "rest_of_line":"enforcingX"})

            dotest ({"key":"SELinux_RPi2_CRIT", "tag":"RPi2_CRIT", "host":"rpi2.lan", "user_host_port":"pi@rpi2.lan", "critical":True, "rest_of_line":"enforcing"})

` `  
## Writing Notification Handler Plugins

One or more notification handlers may be specified in the configuration file line, such as:

      Notif_handlers		stock_notif   my_notif	# Space separated list of notification handlers

The following functions within each listed notification handler are called.  The functionality as provided by `stock_notif` is describe here.  NOTE that the stock_notif handler module need not be used.

- `log_event()` - Called after every monitored item, passing the dictionary returned by eval_status (see above) onto log_event.  The stock_notif handler sends notifications on new FAIL and CRITICAL items, and clears any fail history of now-passing items.  All current WARNING, FAIL, and CRITICAL results are logged on each checking iteration.
- `each_loop()` - Called on every lanmonitor core _service loop_ (every 10 seconds).  Place any general code here that needs to be executed on every iteration.  Unused by stock_notif.
- `renotif()` - Called on every lanmonitor core _service loop_ (every 10 seconds).  Place any code here related to sending additional notifications for items that remain broken.  stock_notif sends repeat notification messages for any critical items on every `CriticalReNotificationInterval` period.  All still-broken critical items are bundled into a single message so as to minimize text messages being sent.
- `summary()` - Called on every lanmonitor core _service loop_ (every 10 seconds).  Place any code here related to scheduling and producing a periodic report.  lanmonfuncs provides `next_summary_timestring()`, which uses `SummaryTime` and `SummaryDays` in the config file, for summary scheduling.  stock_notif's summary simply emails a list of any current WARNING, FAIL, or CRITICAL items, or an "All is well" message to provide a daily lanmonitor-is-alive update.

` `  
## Known issues:
- none

` `  
## Version history
- V1.4  220420  Updated for funcs3.py V1.1 - Log file setup now in config file, timevalue & retime moved to funcs3.  SummaryDays bug and doc fix.  A couple corner case bug fixes.
- V1.2  210605  Reworked have_access check to check_LAN_access logic.
- V1.1  210523  Added loadconfig flush_on_reload (funcs3.py V0.7) to purge any deleted cfg keys.  Error formatting tweaks.  Cmd timeout tweaks
- V1.0  210507  Major refactor
- V0.1  210129  New