# lanmonitor - Keeping watch on the health of your network resources

lanmonitor keeps tabs on key resources in your LAN environment (not actually limited to your LAN).  A text message notification (and/or email) is sent for any monitored _item_ that's out of sorts (not running, not responding, too old, ...).  Periodic re-notifications are sent for
critical items, such as firewalld being down, and summary reports are generated up to daily.

- lanmonitor uses a plug-in architecture, and is easily extensible for new items to monitor and new reporting/notification needs.
- A configuration file is used for all setups - no coding required for use.  The config file may be modified on-th-fly while lanmonitor is running as a service.
- Checks may be executed from the local machine, or from any remote host (with ssh access).  For example, you can check the health of a service running on another machine, or check that a webpage is accessible from another machine.

**NOTE:**  Due to as-of-yet unsolved problems with Python 3.6 and import_resources, the `--setup-user` and `--setup-site` switches are not working on Py 3.6.  Manually grab the files from the [github](https://github.com/cjnaz/lanmonitor) `src/deployment_files` directory and place them in the `~\.config\lanmonitor` directory.  These command line switches work correctly on Python 3.7+.

<br/>

---

## Several plug-ins are provided in the distribution (more details [below](#supplied-plugins)):

| Monitor plugin | Description |
|-----|-----|
| apt_upgrade_history | Checks that the most recent apt upgrade operation was more recent than a given age |
| dd-wrt_age | Checks that the dd-wrt version on the target router is more recent than a given age |
| freespace | Checks that the filesystem of the given path has a minimum of free space |
| fsactivity | Checks that a target file or directory has at least one file newer than a given age |
| interface | Checks that a given network interface (i.e., eth2) is up and running
| pinghost | Checks that a given host can be pinged, as an indicator that the machine is alive on your network |
| process | Checks that a given process is alive on a target host |
| selinux | Checks that selinux reports the expected 'enforcing' or 'permissive' |
| service | Checks that the given init.d or systemd service reports that it's up and running |
| webpage | Checks that the given URL responds with an expected string of text, as an indicator that that the web page is alive |
| yum_update_history | Checks that the most recent yum update operation was more recent than a given age |

If you need other plug-ins, or wish to contribute, please open an issue on the github repo to discuss.

<br/>

---

## Notable changes since prior release
- V3.2
  - Adjusted for cjnfuncs V2.1 (module partitioning).
  - SMTP params must be in the [SMTP] config file section.
  - fsactivity plugin supports missing file.
  - yum_update_history_plugin now requires full command match.


<br/>

---

## Usage
```
$ lanmonitor -h
usage: lanmonitor [-h] [--print-log] [--verbose] [--config-file CONFIG_FILE] [--service] [--setup-user] [--setup-site] [-V]

LAN monitor

Monitor status of network resources, such as services, hosts, file system age, system update age, etc.
See README.md for descriptions of available plugins.

Operates interactively or as a service (loop forever and controlled via systemd or other).

In service mode
    kill -SIGUSR1 <pid>   outputs a summary to the log file
    kill -SIGUSR2 <pid>   outputs monitored items current status to the log file
3.2

options:
  -h, --help            show this help message and exit
  --print-log, -p       Print the tail end of the log file (default last 40 lines).
  --verbose, -v         Display OK items in non-service mode. (-vv for debug logging)
  --config-file CONFIG_FILE, -c CONFIG_FILE
                        Path to the config file (Default <lanmonitor.cfg)> in user/site config directory.
  --service             Enter endless loop for use as a systemd service.
  --setup-user          Install starter files in user space.
  --setup-site          Install starter files in system-wide space. Run with root prev.
  -V, --version         Return version number and exit.
```

<br/>

---

## Example output
```
$ lanmonitor --verbose
 WARNING:  ========== lanmonitor 3.2, pid 26032 ==========
    INFO:  SELinux_local             OK - local    - enforcing
    INFO:  YumUpdate_camero          OK - local    -    7.9 days  (  35 days  max)
    INFO:  AptUpgrade_rpi3           OK - RPi3.lan -   15.5 days  (  35 days  max)
    INFO:  Host_RPi2_TempMon         OK - local    - rpi2.lan (192.168.1.23 / 3.07 ms)
    INFO:  Host_Printer_Server       OK - local    - 192.168.1.44 (192.168.1.44 / 0.874 ms)
 WARNING:    FAIL: Host_RPi3_from_RPi1 - rpi1.lan - HOST RPi3.lan IS NOT RESPONDING
    INFO:  Service_routermonitor     OK - local    - routermonitor
    INFO:  Service_wanstatus         OK - local    - wanstatus
    INFO:  Service_plexmediaserver   OK - local    - plexmediaserver
    INFO:  Service_firewalld         OK - local    - firewalld
 WARNING:    CRITICAL: Service_xxx - local - SERVICE xxx IS NOT RUNNING
    INFO:  Page_WeeWX                OK - local    - http://192.168.33.72/weewx/
    INFO:  Page_xBrowserSync         OK - rpi2.lan - https://www.xbrowsersync.org/
 WARNING:    FAIL: Page_xxx - local - WEBPAGE http://localhost/xxx/ NOT FOUND
    INFO:  Free_Share                OK - local    - free 36%  (minfree 20%)  /mnt/share
    INFO:  Process_x11vnc            OK - local    - /usr/bin/x11vnc
    INFO:  Process_tempmon           OK - RPi2.lan - python TempMon.py
 WARNING:    WARNING: Process_xxxPi3 - RPi3.lan - HOST CANNOT BE REACHED
    INFO:  Activity_Win1_Image       OK - local    -    5.8 days  (   6 days  max)  /mnt/share/backups/Win1/Image/
 WARNING:    FAIL: Activity_Win2_Image  STALE FILES - local -    6.7 days  (   6 days  max)  /mnt/share/backups/Win2/Image/
    INFO:  Activity_CentOS_backups   OK - local    -    0.7 days  (   8 days  max)  /mnt/share/backups/harvey/
 WARNING:    WARNING: Activity_xxx - local - COULD NOT GET ls OF PATH </mnt/share/backups/xxx/>
    INFO:  Activity_TiBuScrape       OK - local    -    3.9 days  (   4 days  max)  /mnt/share/backups/TiBuScrapeArchive/
    INFO:  Activity_RPi2_log.csv     OK - rpi2.lan -    0.8 mins  (   5 mins  max)  /mnt/RAMDRIVE/log.csv
```

<br/>

---

## Setup and Usage notes
- Install lanmonitor from PyPI (`pip install lanmonitor`).
- Install the initial configuration files (`lanmonitor --setup-user` places files at `~/.config/lanmonitor`).

- Edit `lanmonitor.cfg` for the **Core tool parameters**:
  - `ServiceLoopTime` sets how long between rechecks in service mode.  Set to a fraction (eg: 25%) of the shortest item check_interval.
  - `nRetries` sets how many tries will be made to accomplish each monitored item.
  - `RetryInterval` sets the time between nRetries.
  - `ssh_timeout` sets the max time for ssh connections to non-local hosts (default 1s if not specified).
  - `StartupDelay` is a wait time (default 0 seconds) when starting in `--service mode` to allow everything to come up fully (or crash) at system boot before checking starts.
  - `DailyRuntime` is the run time for monitored items that run at daily or longer check intervals (optional).  This setting allows for controlling what time-of-day the infrequent checks are run.  Set this to a few minutes before the `SummaryTime` so that summaries are current.  Generally, don't tag daily+ items as `critical` since this will cause critical renotifications but with infrequent rechecks to clear the item.  If not defined, daily+ items are checked at the time-of-day that lanmonitor was started.
  - `Gateway` is any reliable host on your LAN (typically your router) that will be checked for access as a gate for any monitor items to be run from/on/via other hosts.  For example, the above `Process_tempmon` item will only run if the `Gateway` host can be accessed.  `Gateway` is optional - if not defined then remote-based checks are always run.
  - `LogLevel` controls what gets written to the log file.  At LogLevel 30 (the default if not specified), only warning/fail/critical events are logged.  LogLevel 20 logs passing events also.  For interactive use (non --service mode) the command line --verbose switch controls loglevel.
  - `LogFile` specifies the log file in --service mode.  The path may be absolute or relative to the script's directory.  Interactive usage (non --service mode) logging goes to the console.
  - `PrintLogLength`, `ConsoleLogFormat`, and `FileLogFormat` may also be customized.

- Edit `lanmonitor.cfg` for the **Notification handler parameters**:
  - `Notif_handlers` is a whitespace separated list of Python modules (without the .py extension) that will handle monitored item event tracking, notifications, and periodic summaries. `stock_notify.py` is provided, and has full functionality.  See [Writing Notification Handler Plugins](#writing-notification-handler-plugins), below. An optional absolute or relative (to the lanmonitor modules directory) path may be specified for each notification handler, eg:
  
            Notif_handlers  stock_notif  ~/my_lanmon_dir/my_notif_plugin
    
  - `CriticalReNotificationInterval` sets how long between repeated notifications for any failing CRITICAL monitored items in service mode.  Set `ServiceLoopTime` less than `CriticalReNotificationInterval` so that resolved critical items are rechecked before the next renotification message.  (As implemented by the `stock_notif.py` notification handler.)
  - `SummaryDays` sets which days of the week for summaries to be emailed.  Monday =1, Tuesday =2, ... Saturday =6, Sunday = 7.  Multiple days may be selected.  Comment out `SummaryDays` to eliminate summaries.  (As implemented by the `stock_notif.py` notification handler.)
  - `SummaryTime` sets the time of day (local time) for summaries to be emailed.  24-clock format, for example, `13:00`.  (As implemented by the `stock_notif.py` notification handler.)
  - `LogSummary`, if True, forces the content of the periodic summary to also be sent to the log file.  (As implemented by the `stock_notif.py` notification handler.)
  - `EmailTo` is a whitespace separated list of email addresses that summaries will be sent to.  Comment out EmailTo to disable emailing summaries.  (As implemented by the `stock_notif.py` notification handler.)
  - `NotifList` is a whitespace separated list of phone numbers (using your carrier's email-to-text bridge) to which event notifications will be sent.  Comment out NotifList to disable all notifications.  (As implemented by the `stock_notif.py` notification handler.)

- Edit `lanmonitor.cfg`  and `creds_SMTP` for the **SMTP email parameters**.
  - Enter `NotifList`, and `EmailTo` addresses, and import your email credentials file (`import creds_SMTP`). Any, none, or all parameters may be moved to an imported config file. All of these SMTP-related params must be in the `[SMTP]` section.
  
            EmailServer       mail.mailserver.com
            EmailServerPort   P587TLS                 # One of: P465, P587, P587TLS, or P25   
            EmailUser	      yourusername@mailserver.com
            EmailPass	      yourpassword
            EmailFrom         yourfromaddress@mailserver.com

- See [below](#monitored-items-setup) for setting up items to be monitored.
- Run the tool with `lanmonitor --verbose`.  Make sure that the local machine and user (root?) has password-less ssh access to any remote machines.  `-v` enables INFO level logging of passing itmes.  `-vv` turns on DEGUG level logging.
- Install lanmonitor as a systemd service (google how).  An example `lanmonitor.service` file is provided in the config directory.  Note that the config file may be modified while the service is running, with changes taking effect on the next ServiceLoopTime.  Make sure that the user that the service runs under (typically root) has ssh password-less access to any remotes.
- stock_notif sends a text message for each monitored item that is in a FAIL or CRITICAL state.  CRITICAL items have a repeated text message sent after the `CriticalReNotificationInterval`.  Notifications are typically sent as text messages, but may be (also) directed to regular email addresses.
- stock_notif also sends a periodic summary report listing any current warnings/fails/criticals, or that all is well.  Summaries are typically sent as email messages.
- NOTE:  All timevalues in the config file may be entered with a `s` (seconds), `m` (minutes), `h` (hours), `d` (days), or `w` (weeks) suffix.  For example `6h` is 6 hours.  If no suffix is provided the time value is taken as seconds.
- NOTE:  You may wish to set static leases for hosts that you will be accessing by name, otherwise you may get HOST \<xxx> IS NOT KNOWN warnings until that host renews its IP address after a router (DHCP / DNS resolver) reboot.
- NOTE:  Some remote hosts may not have needed commands available for ssh login.  This is a known issue for the interface_plugin: the ifconfig command is not available on a Raspberry Pi via ssh.  To resolve this issue, add the missing command's path to /etc/ssh/sshd_config:

      $ ssh user@host env
      ...
      PATH=/usr/local/bin:/usr/bin:/bin:/usr/games

      The path to ifconfig on the target host is /usr/sbin/ifconfig

      Add to the bottom of /etc/ssh/sshd_config
      SetEnv PATH=/usr/local/bin:/usr/bin:/bin:/usr/games:/usr/sbin

      $ sudo systemctl restart sshd
- Supported on Python3.6+ on Linux.

<br/>

<a id="monitored-items-setup"></a>

---

## Monitored items setup
Items to be monitored are defined in the `lanmonitor.cfg` file.  "Plugin" modules provide the logic for each monitored item type.  [Supplied plugins](#supplied-plugins) are described below.  See the description at the top of each plugin module for additional notes.
To activate a given plugin, a `MonType_` line is included in the configuration file using this format:

      MonType_<type>    <plugin_name>

1. Begins with the `MonType_` prefix
2. The `<type>` is used as the prefix on successive lines for monitor items of this type
3. The `<plugin_name>` is the Python module name (implied .py suffix). An optional absolute or relative (to the lanmonitor modules directory) path may specified, eg: `MonType_XYZ ~/my_lanmon_dir/myXYZ_plugin`.

For monitored items, the general format of a line is

      <type>_<friendly_name>  <local or user@host[:port]>  [CRITICAL]  <check_interval>  <rest_of_line>

1. `<type>` matches the corresponding `MonType_<type>` line.
2. `<friendly_name>` is arbitrary and is used for notifications, logging, etc. `<type>_<friendly_name>` must be unique.
3. `<local or user@host[:port]>` specifies _on which machine the check will be executed from._  If not "`local`" then `user@host` specifies the ssh login on the remote machine.  For example, the `Host_Yahoo` line below specifies that `Yahoo.com` will be pinged from the `RPi2.mylan` host by doing an `ssh me@RPi2.mylan ping Yahoo.com`.  The default ssh port is 22, but may be specified via the optional `:port` field.
4. `CRITICAL` may optionally be specified.  CRITICAL tagged items are those that need immediate attention.  Renotifications are sent for these items when failing by the `stock_notif.py` notification handler based on the `CriticalReNotificationInterval` config parameter.  (For critical-tagged items their `check_interval` should be less than the `CriticalReNotificationInterval`.)
5. `<check_interval>` is the wait time between rechecks for this specific item.  Each item is checked at its own check_interval.
6. `<rest_of_line>` are the monitored type-specific settings.

<br/>

<a id="supplied-plugins"></a>

---

## Supplied plugins

See the documentation header in each plugin for additional functionality and configuration specifics.

- **apt_upgrade_history_plugin:**  apt history files at /var/log/apt/* are checked for the specified `<apt_command>` text and the date is extracted from
the most recent occurrence of this text, then compared to the `<age>` limit.  May require root access in order to read apt history.

      MonType_AptUpgrade     apt_upgrade_history_plugin
      AptUpgrade_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <apt_command>
      AptUpgrade_MyHost          local          CRITICAL  1d   15d  apt full-upgrade

- **dd-wrt_age_plugin:**  Check a dd-wrt router for system software no older than `<age>`.  The `<routerIP>` may be an IP address or hostname.  The dd-wrt router's /Info.htm page is checked for the date on the top right of the page.

      MonType_DD-wrt_age  dd-wrt_age_plugin
      DD-wrt_age_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <routerIP>
      DD-wrt_age_Router          local          CRITICAL  1d   30d  192.168.1.1

- **freespace_plugin:**  The free space on the file system that holds the  specified `<path>` is checked.  Expected free space may be an absolute value or a percentage. If the path does not exist, setup() will pass but eval_status() will return RTN_WARNING and retry on each
check_interval.  This allows for intermittently missing paths.

      MonType_Free		freespace_plugin
      Free_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <free_amount>  <path>
      Free_RPi1                  pi@RPi3        CRITICAL  5m   20%         /home/pi
      Free_share                 local                    1d   1000000000  /mnt/share

- **fsactivity_plugin:**  The age of files in a directory is checked for at least one file being more recent than `<age>` ago.
Note that sub-directories are not recursed - only the specified top-level directory is checked for the newest file.
Alternately, the age of a specific individual file may be checked.
A path to a directory is specified by ending the path with a `/`, else the path is taken as an individual file.

      MonType_Activity	fsactivity_plugin
      Activity_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <path to directory or file>
      Activity_MyServer_backups  local                    1h   8d  /mnt/share/MyServerBackups/
      Activity_RPi2_log.csv      me@rpi2.mylan  CRITICAL  30s  5m  /mnt/RAMDRIVE/log.csv

- **interface_plugin:**  The specified interface is checked with a `ifconfig <interface name>`, checking for 'UP' and 'RUNNING'.

      MonType_Interface         interface_plugin
      Interface_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <interface name>
      Interface_router_vlan0     local          CRITICAL  3m   vlan0

- **pinghost_plugin:**  Ping the specified host.  The `<IP address or hostname>` may be on the local LAN or external.

      MonType_Host		pinghost_plugin
      Host_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <IP address or hostname>
      Host_RPi1_HP1018           local          CRITICAL  5m   192.168.1.44
      Host_Yahoo                 me@RPi2.mylan            20m  Yahoo.com

  The default timeout for ping commands is 1 seconds.  pinghost_plugin_timeout may be set in the config file to override the default, eg: `pinghost_plugin_timeout 5s`

- **process_plugin:**  Check that the specified process is alive.  A process is checked by seeing if the `<executable path>` occurs in the output of a `ps -Af` call.  

      MonType_Process		process_plugin
      Process_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <executable path>
      Process_x11vnc             local          CRITICAL  5m   /usr/bin/x11vnc

- **selinux_plugin:** Checks that the sestatus _Current mode:_ field matches the specified value.

      MonType_SELinux		selinux_plugin
      SELinux_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <enforcing or permissive>
      SELinux_localhost          local          CRITICAL  30s  enforcing

- **service_plugin:**  Check that the specified service is active and running.  Checking is done via `systemctl status <service name>` (for systemd) or `service <service_name> status` (for init).

      MonType_Service		service_plugin
      Service_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <service name>
      Service_firewalld          local          CRITICAL  30s  firewalld
      Service_RPi1_HP1018        me@RPi1.mylan            5m   cups

- **webpage_plugin:**  The specified web page `<url>` is retrieved and checked that it contains the `<expected text>`.  The url may be on a local or remote server.

      MonType_Page		webpage_plugin
      Page_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <url>  <expected text>
      Page_WeeWX                 local                    5m   http://localhost/weewx/   Current Conditions
      Page_xBrowserSync          me@RPi2.mylan            5m   https://www.xbrowsersync.org/   Browser syncing as it should be: secure, anonymous and free! # Check it out!

- **yum_update_history_plugin:**  yum history output is checked for the specific `<yum_command>` text and the date is extracted from
the first occurrence this line, then compared to the `<age>` limit.  May require root access in order to read yum history.

      MonType_YumUpdate      yum_update_history_plugin
      YumUpdate_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <yum_command>
      YumUpdate_MyHost           local          CRITICAL  2h   15d  update --skip-broken

<br/>

---

## Writing Monitor Plugins

New plugins may be added easily.  The core lanmonitor code provides a framework for configuration, logging, command retries, and parsing components.  The general process for creating a new plugin is:

- Copy an existing plugin, such as the `lanmonitor/src/lanmonitor/webpage_plug.py` to a working directory as `mynewitem_plugin.py`.
- Adjust the \<newitem> comment block to describe the functionality and config file details.
- Within the `setup()` function:
  - Adjust the `rest_of_line` parsing, creating new vars as needed.
  - Add any checker code to validate these new values.
- Within the `eval_status()` function:
  - Adjust the `cmd` for your needed subprocess call command.
  - The `cmd_check()` function can check the returncode or return text.  It also returns the full subprocess call response.  _See the cmd_check function within the lanmonfuncs.py module for built-in checking features._  Uncomment the `# logging.debug (f"cmd_check response:  {rslt}")` line to see what's available for building response checker code.
  - Adjust the `if rslt[0] == RTN_PASS: … return` lines for the PASS, FAIL/CRITICAL return text.  The `key_padded` and `host_padded` vars are used on the PASSing line for pretty printing.
- Create a companion `mynewitem_plugin_test.py` by copying from the lanmonitor/tests directory, and create `dotest()` calls to exercise all possible good, bad, and invalid conditions.
- Debug and validate the new plugin module by running standalone (`./mynewitem_plugin_test.py`).
- Add the `MonType_<your_monitor_type> <abs_path_to>/mynewitem_plugin>` line and specific monitor items to your config file.
  - New plugins are welcome for bundling into the lanmonitor distribution.  Open a github issue.

<br/>

### Additional plugin writing notes
1. The `setup()` function of your module will be called for each related `<type>_<friendly_name>` line in the config file.  setup() is called only once at initial startup and after any on-the-fly edits to the configuration file.  setup() is supplied a dictionary:

        Monitor item dictionary keys passed to setup():
            key             Full 'itemtype_tag' key value from config file line
            tag             'tag' portion only from 'itemtype_tag' from config file line
            user_host_port  'local' or 'user@hostname[:port]' from config file line
            host            'local' or 'hostname' from config file line
            critical        True if 'CRITICAL' is in the config file line
            check_interval  Time in seconds between rechecks
            rest_of_line    Remainder of line (plugin specific formatting)

    - setup() must return RTN_PASS, RTN_WARNING, or RTN_FAIL.  If RTN_FAIL the setup failure is permanent and the item will not be monitored (but setup() will be retried again after a config file edit).  If RTN_WARNING the setup will be retried on the next checking iteration, thus allowing for intermittent issues during setup.  Warnings and Fails are logged.
    - Within setup(), commands may optionally be executed on the target machine for determining setup specifics (see `service_plugin.py` for an example).  NOTE that `check_LAN_access` (see next section) is NOT called before the setup() calls, so setup() failures might be due to no network access, or due to ssh access issues to the target machine.

2. The `eval_status()` function is called on each checking iteration.  The plugin needs to return a dictionary with 3 keys:

        eval_status() returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details

      - `cmd_check()` in `lanmonfuncs.py` provides checking features such as command execution with retries, ssh for remote hosts, and check strings in the command response.  The raw command output is also returned so that your code can construct specific checks. Uncomment the `logging.debug()` call after the cmd_check() call and run with debugging logging (`lanmonitor -vv`, or run the plugin's `..._test.py` script)
      to see the available cmd_check() response data. See `lanmonfuncs.py` for cmd_check feature details and the return structure.
      - If the host is not `local` then the lanmonitor core will check that the local machine has access to the LAN by pinging the the `Gateway` host defined in the config file.  This `check_LAN_access()` check is performed only once per check iteration.  Thus, your eval_status() code can assume that the LAN is accessible.  It is recommended that you include a `Host_<myhost>` check (using the pinghost plugin) earlier in the config file to limit fail ambiguity.
      - In addition to the `Gateway` access check, if a monitor item is to be executed on a remote host (not `local`) and the results are not passing, then `cmd_check` with double checks that ssh-based access to the target host is working.  `cmd_check` returns RTN_WARNING if there is an ssh access issue, versus RTN_PASS/RTN_FAIL for the specific checked item.  Your plugin should distinguish between ssh vs. real failures.

3. The plugin module may be tested by running the companion `..._test.py` script.  Add tests to exercise your checking logic for both local and remote hosts, and for any warning/error traps.  (Note that the checking interval scheduling is handled in the lanmonitor core, so in the `dotest()` calls just set `"check_interval":1` as a placeholder.)

            dotest ({"key":"SELinux_local", "tag":"local", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"enforcing"})

            dotest ({"key":"SELinux_RPi3", "tag":"RPi3", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":False, "check_interval":1, "rest_of_line":"enforcing"})

            dotest ({"key":"SELinux_RPi3_CRIT", "tag":"RPi3_CRIT", "host":"rpi3", "user_host_port":"pi@rpi3", "critical":True, "check_interval":1, "rest_of_line":"enforcing"})

            dotest ({"key":"SELinux_badmode", "tag":"Shop2", "host":"local", "user_host_port":"local", "critical":True, "check_interval":1, "rest_of_line":"enforcingX"})

            dotest ({"key":"SELinux_Unknown", "tag":"Unknown", "host":"RPiX", "user_host_port":"pi@rpiX", "critical":True, "check_interval":1, "rest_of_line":"enforcing"})

            dotest ({"key":"SELinux_Unavailable", "tag":"Unavailable", "host":"shopcam", "user_host_port":"me@shopcam", "critical":True, "check_interval":1, "rest_of_line":"enforcing"})


<br/>

<a id="writing-notification-handler-plugins"></a>

---

## Writing Notification Handler Plugins

One or more notification handlers may be specified in the configuration file line, such as:

      Notif_handlers		stock_notif   my_notif	# Whitespace separated list of notification handlers

The following functions within each listed notification handler are called.  The functionality as provided by `stock_notif` is describe here.  NOTE that the stock_notif handler module need not be used.

- `log_event()` - Called after every monitored item, passing the dictionary returned by eval_status() (see above) onto log_event().  The stock_notif handler sends notifications on new FAIL and CRITICAL items, and clears any fail history of now-passing items.
- `each_loop()` - Called on every lanmonitor core _service loop_ (per ServiceLoopTime).  Place any general code here that needs to be executed on every iteration.  Unused by stock_notif.
- `renotif()` - Called on every lanmonitor core _service loop_ (per ServiceLoopTime).  Place any code here related to sending additional notifications for items that remain broken.  stock_notif sends repeat notification messages for any critical items on every `CriticalReNotificationInterval` period.  All still-broken critical items are bundled into a single message so as to minimize text messages being sent.
- `summary()` - Called on every lanmonitor core _service loop_ (per ServiceLoopTime).  Place any code here related to scheduling and producing a periodic report.  The lanmonfuncs.py module provides `next_summary_timestring()`, which uses `SummaryTime` and `SummaryDays` in the config file, for summary scheduling.  stock_notif's summary simply emails a list of any current WARNING, FAIL, or CRITICAL items, or an "All is well" message to provide a periodic _lanmonitor-is-alive_ message.

<br/>

---

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