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

   Config param | Default | Description
   --|--|--
   `ServiceLoopTime` | | sets how long between rechecks in service mode.  Set to a fraction (eg: 25%) of the shortest item check_interval.
   `nTries` | 2 |sets how many tries will be made to accomplish each monitored item.
   `RetryInterval` | 0.5s | sets the time between nTries.
   `Cmd_timeout` | 1.0s | sets the _default_ max time for completion of the command for each monitor item check.  Can be overridden for each monitor item definition.
   `SSH_timeout` | 1.0s | sets the max time for ssh connections to non-local hosts.
   `StartupDelay` | 0s | is a wait time (default 0 seconds) when starting in `--service mode` to allow everything to come up fully (or crash) at system boot before checking starts.
   `DailyRuntime` | | is the run time for monitored items that run at daily or longer check intervals (optional).  This setting allows for controlling what time-of-day the infrequent checks are run.  Set this to a few minutes before the `SummaryTime` so that summaries are current.  Generally, don't tag daily+ items as `critical` since this will cause critical renotifications but with infrequent rechecks to clear the item.  If not defined, daily+ items are checked at the time-of-day that lanmonitor was started.
   `Gateway` | | is any reliable host on your LAN (typically your router) that will be checked for access as a gate for any monitor items to be run from/on/via other hosts.  For example, the above `Process_tempmon` item will only run if the `Gateway` host can be accessed.  `Gateway` is optional - if not defined then remote-based checks are always run.
   `Gateway_timeout` | 1.0s | sets the max time for checking the Gateway for LAN access health
   `LogLevel` | 30/WARNING | controls what gets written to the log file.  At LogLevel 30 (the default if not specified), only warning/fail/critical events are logged.  LogLevel 20 logs passing events also.  For interactive use (non --service mode) the command line --verbose switch controls loglevel.
   `LogFile` | | specifies the log file in --service mode.  The path may be absolute or relative to the script's directory.  Interactive usage (non --service mode) logging goes to the console.

   `PrintLogLength`, `ConsoleLogFormat`, and `FileLogFormat` may also be customized.

   NOTE that the config file parser accepts either whitespace, '=', or ':' between the param name (the first token on the line) and its value (the remainder of the line).

<br/>

- Edit `lanmonitor.cfg` for the **Notification handler parameters**:

   Config param | Description
   --|--
  `Notif_handlers` | is a whitespace separated list of Python modules (without the .py extension) that will handle monitored item event tracking, notifications, and periodic summaries. `stock_notify.py` is provided, and has full functionality. An optional absolute or relative (to the lanmonitor modules directory) path may be specified for each notification handler, eg: `Notif_handlers  stock_notif  ~/my_lanmon_dir/my_notif_plugin`
  `CriticalReNotificationInterval` | sets how long between repeated notifications for any failing CRITICAL monitored items in service mode.  Set `ServiceLoopTime` less than `CriticalReNotificationInterval` so that resolved critical items are rechecked before the next renotification message.  (As implemented by the `stock_notif.py` notification handler.)
  `SummaryDays` | sets which days of the week for summaries to be emailed.  Monday =1, Tuesday =2, ... Saturday =6, Sunday = 7.  Multiple days may be selected.  Comment out `SummaryDays` to eliminate summaries.  (As implemented by the `stock_notif.py` notification handler.)
  `SummaryTime` | sets the time of day (local time) for summaries to be emailed.  24-clock format, for example, `13:00`.  (As implemented by the `stock_notif.py` notification handler.)
  `LogSummary` | if True, forces the content of the periodic summary to also be sent to the log file.  (As implemented by the `stock_notif.py` notification handler.)
  `EmailTo` | is a whitespace separated list of email addresses that summaries will be sent to.  Comment out EmailTo to disable emailing summaries.  (As implemented by the `stock_notif.py` notification handler.)
  `NotifList` | is a whitespace separated list of phone numbers (using your carrier's email-to-text bridge) to which event notifications will be sent.  Comment out NotifList to disable all notifications.  (As implemented by the `stock_notif.py` notification handler.)

<br/>

- Edit `lanmonitor.cfg`  and `creds_SMTP` for the **SMTP email parameters**.
  - Enter `NotifList`, and `EmailTo` addresses, and import your email credentials file (`import creds_SMTP`). Any, none, or all parameters may be moved to an imported config file. All of these SMTP-related params must be in the `[SMTP]` section.
  
            EmailServer       mail.mailserver.com
            EmailServerPort   P587TLS                 # One of: P465, P587, P587TLS, or P25   
            EmailUser	      yourusername@mailserver.com
            EmailPass	      yourpassword
            EmailFrom         yourfromaddress@mailserver.com

- See [below](#monitored-items-setup) for setting up items to be monitored.
- Run the tool with `lanmonitor --verbose`.  Make sure that the local machine and user (root?) has password-less ssh access to any remote machines.  `-v` enables INFO level logging of passing items.  `-vv` turns on DEBUG level logging.
- Install lanmonitor as a systemd service (google how).  An example `lanmonitor.service` file is provided in the config directory.  Note that the config file may be modified while the service is running, with changes taking effect on the next ServiceLoopTime.  Make sure that the user that the service runs under (typically root) has ssh password-less access to any remotes.
- stock_notif sends a text message for each monitored item that is in a FAIL or CRITICAL state.  CRITICAL items have a repeated text message sent after the `CriticalReNotificationInterval`.  Notifications are typically sent as text messages, but may be (also) directed to regular email addresses.
- stock_notif also sends a periodic summary report listing any current warnings/fails/criticals, or that all is well.  Summaries are typically sent as email messages.
- NOTE:  All timevalues in the config file may be entered with a `s` (seconds), `m` (minutes), `h` (hours), `d` (days), or `w` (weeks) suffix.  For example `6.5h` is 6.5 hours.  If no suffix is provided the time value is taken as seconds.
- NOTE:  You may wish to set static leases for hosts that you will be accessing by name, otherwise you may get HOST \<xxx> IS NOT KNOWN warnings until that host renews its IP address after a router (DHCP / DNS resolver) reboot.
- NOTE:  Some remote hosts may not have needed commands available for ssh login.  This is a known issue for the interface_plugin: the ifconfig command is not available on a Raspberry Pi via ssh.  To resolve this issue, add the missing command's path to /etc/ssh/sshd_config, eg:

      $ ssh user@host env
      ...
      PATH=/usr/local/bin:/usr/bin:/bin:/usr/games

      The path to ifconfig on the target host is /usr/sbin/ifconfig

      Add to the bottom of /etc/ssh/sshd_config
      SetEnv PATH=/usr/local/bin:/usr/bin:/bin:/usr/games:/usr/sbin

      $ sudo systemctl restart sshd


<br/>

<a id="monitored-items-setup"></a>

---

## Monitored items setup
Items to be monitored are defined in the `lanmonitor.cfg` file.  "Plugin" modules provide the logic for each monitored item type.  [Supplied plugins](#supplied-plugins) are described below. To activate a given plugin, a `MonType_` line is included in the configuration file using this format:

      MonType_<type>    <plugin_name>

      eg:
      Montype_Host  pinghost_plugin

1. Begins with the `MonType_` prefix
2. The `<type>` is used as the prefix on successive lines for monitor items of this type
3. The `<plugin_name>` is the Python module name (implied .py suffix). An optional absolute or relative (to the lanmonitor modules directory) path may specified, eg: `MonType_XYZ ~/my_lanmon_dir/myXYZ_plugin`.

<br/>

For monitored items, the _string-style_ format of a line is:

      <type>_<friendly_name>    <local or user@host[:port]>  [CRITICAL]  <check_interval>  <rest_of_line>

      eg:
      Host_testhost2    local  CRITICAL  5m  testhost2.lan

**This example definition executes the `pinghost_plugin` on the `local` machine, every `5 minutes`, checking for a response from `testhost2.lan`.  If testhost2.lan is not available a notification is sent to the config file `NotifList`.  The `CRITICAL` tag indicates that repeat notifications will be sent per the config file `CriticalReNotificationInterval` param.**

Breaking down the definition line syntax terms:

1. `<type>` matches the corresponding `MonType_<type>` line.
2. `<friendly_name>` is arbitrary and is used for notifications, logging, etc. `<type>_<friendly_name>` must be unique.
3. `<local or user@host[:port]>` specifies _on which machine the check will be executed from._  If not "`local`" then `user@host` specifies the ssh login on the remote machine.  For example, the `Host_Yahoo` line below specifies that `Yahoo.com` will be pinged from the `RPi2.mylan` host by doing an `ssh me@RPi2.mylan ping Yahoo.com`.  The default ssh port is 22, but may be specified via the optional `:port` field.
4. `CRITICAL` may optionally be specified.  CRITICAL tagged items are those that need immediate attention.  Renotifications are sent for these items when failing by the `stock_notif.py` notification handler based on the `CriticalReNotificationInterval` config parameter.  (For critical-tagged items their `check_interval` should be less than the `CriticalReNotificationInterval`.)
5. `<check_interval>` is the wait time between rechecks for this specific item.  Each item is checked at its own check_interval.
6. `<rest_of_line>` are the plugin-specific settings/content.

<br/>

As of version 3.3, an alternate monitored items setup format is supported in the form of a _Python dictionary_, eg:

      String-style item definition:
      Host_testhost2    local  CRITICAL  5m  testhost2.lan

      Equivalent dictionary-style definition:
      Host_testhost2    {'u@h:p':'local', 'critical':True, 'timeout':'1s', 'recheck':'5m', 'rol':'testhost2.lan'}

      Same definition while utilizing the defaults:
      Host_testhost2    {'critical':True, 'recheck':'5m', 'rol':'testhost2.lan'}

- The dictionary format supports setting the `Cmd_timeout` setting for each individual monitor item by specifying the `'timeout':<value>`.  This setting is not available in the string-style format.
- The dictionary format is parsed directly by Python, and thus follows all of the formatting rules, notably:
  - Key:Value terms are separated by `:`, and Key:Value pairs are separated by `,`.  Keys are quoted.  String values are quoted, while boolean, integer, and float values are unquoted.  The order of key:value pairs is flexible (versus fixed in the string-sytle format).  lanmonitor also supports default values for several of the terms
- Notable aspects of each Key:Value pair:

   Key | String-style term name | Default | Notes
   -- | -- | -- |--
   `u@h:p` | `local or user@host[:port]` | `local` | 
   `critical` | `CRITICAL` | `False` | Boolean True or False (unquoted)
   `timeout` | NA | `Cmd_timeout` value in the config file | Not supported using the string-style format
   `recheck` | `check_interval` | Required | timevalue string (eg: '5m'), or integer or float seconds
   `rol` | `rest_of_line` | Required | Plugin-specific settings/content

