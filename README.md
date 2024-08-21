# lanmonitor - Keeping watch on the health of your network resources

lanmonitor keeps tabs on key resources in your LAN environment (not actually limited to your LAN).  A text message notification (and/or email) is sent for any monitored _item_ that's out of sorts (not running, not responding, too old, ...).  Periodic re-notifications are sent for
critical items, such as firewalld being down, and summary reports are generated up to daily.

- lanmonitor uses a plug-in architecture, and is easily extensible for new items to monitor and new reporting/notification needs.
- A configuration file is used for all setups - no coding required for use.  The config file may be modified on-th-fly while lanmonitor is running as a service.
- Checks may be executed from the local machine, or from any remote host (with ssh access).  For example, you can check the health of a service running on another machine, or check that a webpage is accessible from another machine.

Supports Python 3.7+.

<br/>

---

## Several plugins are provided in the distribution (more details [below](#supplied-plugins)):

| Monitor plugin | Description |
|-----|-----|
apt_upgrade_history_plugin | Checks that the most recent apt upgrade operation was more recent than a given age
dd_wrt_age_plugin | Checks that the dd-wrt version on the target router is more recent than a given age
freemem_plugin | Checks that available RAM memory and swap space are at safe levels
freespace_plugin | Checks that the filesystem of the given path has a minimum of free space
fsactivity_plugin | Checks that a target file or directory has at least one file newer than a given age
interface_plugin | Checks that a given network interface (i.e., eth2) is up and running
pinghost_plugin | Checks that a given host can be pinged, as an indicator that the machine is alive on your network
process_plugin | Checks that a given process is alive on a target host
selinux_plugin | Checks that selinux reports the expected 'enforcing' or 'permissive'
service_plugin | Checks that the given init.d or systemd service reports that it's up and running
webpage_plugin | Checks that the given URL responds with an expected string of text, as an indicator that that the web page is alive
yum_update_history_plugin | Checks that the most recent yum update operation was more recent than a given age

If you need other plug-ins, or wish to contribute, please open an issue on the github repo to discuss. 
See [Writing_New_Plugins](https://github.com/cjnaz/lanmonitor/blob/main/Writing_New_Plugins.md) 
for plugin implementation details.


<br/>

---

## Notable changes since prior release
- V3.3
  - New freemem_plugin
  - Support dictionary-style monitor item definitions, which adds support for cmd_timeout per monitored item
  - Tolerate temporarily missing config file

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
3.3

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
 WARNING:  ========== lanmonitor 3.3, pid 26032 ==========
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
   `SSH_timeout` | 1.0s | sets the max time for ssh connections to non-local hosts. **
   `StartupDelay` | 0s | is a wait time (default 0 seconds) when starting in `--service mode` to allow everything to come up fully (or crash) at system boot before checking starts.
   `DailyRuntime` | | is the run time for monitored items that run at daily or longer check intervals (optional).  This setting allows for controlling what time-of-day the infrequent checks are run.  Set this to a few minutes before the `SummaryTime` so that summaries are current.  Generally, don't tag daily+ items as `critical` since this will cause critical renotifications but with infrequent rechecks to clear the item.  If not defined, daily+ items are checked at the time-of-day that lanmonitor was started.
   `Gateway` | | is any reliable host on your LAN (typically your router) that will be checked for access as a gate for any monitor items to be run from/on/via other hosts.  For example, the above `Process_tempmon` item will only run if the `Gateway` host can be accessed.  `Gateway` is optional - if not defined then remote-based checks are always run.
   `Gateway_timeout` | 1.0s | sets the max time for checking the Gateway for LAN access health
   `LogLevel` | 30/WARNING | controls what gets written to the log file.  At LogLevel 30 (the default if not specified), only warning/fail/critical events are logged.  LogLevel 20 logs passing events also.  For interactive use (non --service mode) the command line --verbose switch controls loglevel.
   `LogFile` | | specifies the log file in --service mode.  The path may be absolute or relative to the script's directory.  Interactive usage (non --service mode) logging goes to the console.

   `PrintLogLength`, `ConsoleLogFormat`, and `FileLogFormat` may also be customized.

   NOTE that the config file parser accepts either whitespace, '=', or ':' between the param name (the first token on the line) and its value (the remainder of the line).
   
   NOTE **: An SSH access failure message to a remote host can vary based on the `SSH_timeout` setting.  Shorter times (<2s) can 
   return "timed out after X seconds", while longer times will return "ssh: connect to host \<hostname> port 22: No route to host".  Both return a warning level result.

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
- **NOTE timevalues:**  All timevalues in the config file may be entered with a `s` (seconds), `m` (minutes), `h` (hours), `d` (days), or `w` (weeks) suffix.  For example `6.5h` is 6.5 hours.  If no suffix is provided the time value is taken as seconds.
- **NOTE static leases:**  You may wish to set static leases for hosts that you will be accessing by name, otherwise you may get HOST \<xxx> IS NOT KNOWN warnings until that host renews its IP address after a router (DHCP / DNS resolver) reboot.
- **NOTE remote commands missing:**  Some remote hosts may not have needed commands available for ssh login.  This is a known issue for the interface_plugin: the ifconfig command is not available on a Raspberry Pi via ssh.  To resolve this issue, add the missing command's path to /etc/ssh/sshd_config, eg:

      $ ssh user@host env
      ...
      PATH=/usr/local/bin:/usr/bin:/bin:/usr/games

      The path to ifconfig on the target host is /usr/sbin/ifconfig

      Add to the bottom of /etc/ssh/sshd_config
      SetEnv PATH=/usr/local/bin:/usr/bin:/bin:/usr/games:/usr/sbin

      $ sudo systemctl restart sshd

- **NOTE remote ssh access:** For whatever local user the service is run under (suggested root on the local machine), that local user needs its ssh public key pushed to the target remote user's `/home/<user>/.ssh/authorized_keys` file.  Also, on first access to the remote host the user will be prompted to confirm the identity of the remote host, which places an entry in the local machine's `/home/<user>/.ssh/known_hosts` file.
Suggest testing if you have ssh access set up correctly by running the script as the service's local user:  `sudo -u root /<path_to>/lanmonitor --verbose`.  _There must be no prompts for remote users' login password or acceptance of the the remote host id key when running lanmonitor._

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
      Host_Yahoo        me@testhost2     1h  yahoo.com

**The `Host_testhost2` example definition executes the `pinghost_plugin` on the `local` machine, every `5 minutes`, checking for a response from `testhost2.lan`.  If testhost2.lan is not available a notification is sent to the config file `NotifList`.  The `CRITICAL` tag indicates that repeat notifications will be sent per the config file `CriticalReNotificationInterval` param.**

Breaking down the definition line syntax terms:

1. `<type>` matches the corresponding `MonType_<type>` line.
2. `<friendly_name>` is arbitrary and is used for notifications, logging, etc. `<type>_<friendly_name>` must be unique.
3. `<local or user@host[:port]>` specifies _on which machine the check will be executed from._  If not "`local`" then `user@host` specifies the ssh login on the remote machine.  For example, the `Host_Yahoo` line above specifies that `Yahoo.com` will be pinged from the `testhost2` host by doing an `ssh me@testhost2 ping Yahoo.com`.  The default ssh port is 22, but may be specified via the optional `:port` field.
4. `CRITICAL` may optionally be specified.  CRITICAL tagged items are those that need immediate attention.  Renotifications are sent for these items when failing by the `stock_notif.py` notification handler based on the `CriticalReNotificationInterval` config parameter.  (For critical-tagged items their `check_interval` should be less than the `CriticalReNotificationInterval`.)
5. `<check_interval>` is the wait time between rechecks for this specific item.  Each monitored item is checked at its own check_interval.
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



<br/>

<a id="supplied-plugins"></a>

---

## Supplied plugins

### apt_upgrade_history_plugin

apt history files at /var/log/apt/* are checked for the specific `apt_command` text and the date is extracted from
the most recent occurrence of this text, then compared to the `age` limit.  May require root access in order to read apt history.

**Typical string and dictionary-style config file lines:**

    MonType_AptUpgrade           =  apt_upgrade_history_plugin
    # AptUpgrade_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>    <age>  <apt_command>
    AptUpgrade_testhost          =  local  1d  30d  apt full-upgrade
    AptUpgrade_testhost2         =  {'u@h:p':'me@testhost2', 'recheck':'1d', 'rol':'30d  apt full-upgrade'}

**Plugin-specific _rest-of-line_ params:**

`age` (timevalue, or int/float seconds)
- Max time allowed since last execution of the apt_command

`apt_command` (str)
- The apt history is scanned for this specific string

Note: The apt history file formatting may be locale specific.  This plugin is currently hardcoded to US locale.

<br/>

---

### dd_wrt_age_plugin

The dd-wrt router is checked for the age of the currently installed dd-wrt version by reading the
/Info.htm page for the date on the top right of the page, eg: <DD-WRT v3.0-r46885 std (06/05/21)>.

**Typical string and dictionary-style config file lines:**

    MonType_DD-wrt_age           =  dd_wrt_age_plugin
    # DD-wrt_age_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <routerIP>
    DD-wrt_age_Router            =  local  CRITICAL  1d  30d  192.168.1.1
    DD-wrt_age_Router2           =  {'recheck':'1d', 'rol':'30d  192.168.1.1'}

**Plugin-specific _rest-of-line_ params:**

`age` (timevalue, or int/float seconds)
- Max time allowed since last dd-wrt software upgrade

`routerIP` (str)
- IP address or hostname of the router

Note:  I no longer have a dd-wrt router for testing this plugin.

<br/>

---

### freemem_plugin

System memory on the target system is checked for a minimum amount of 'available' RAM memory and swap space,
as shown by the `free` command.
The limits may be specified as either a minimum percentage free or a minimum number of Ki/Mi/Gi/Ti bytes free.

**Typical string and dictionary-style config file lines:**

    MonType_Freemem           =  freemem_plugin
    # Freemem_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <free_mem> [<free_swap>]
    Freemem_testhost2         =  me@testhost2    CRITICAL   5m   20% 50%
    Freemem_root              =  {'recheck':'5m', 'rol':'100Mi 30%'}

**Plugin-specific _rest-of-line_ params:**

`free_mem` (str, absolute or percentage)
- Minimum required free RAM

`free_swap` (Optional, str, absolute or percentage)
- Minimum required free swap space, if specified

For both:
- The percentage minimum limit is specified with a `%` suffix, eg `20%`
- The absolute minimum limit is specified with a `Ki`/`Mi`/`Gi`/`Ti` suffix (case insensitive), eg `5Gi`
- If absolute minimum limits are used for both `free_mem` and `free_swap`, then they both must have the same suffix, eg `5Gi, 1Gi`.
One may be an absolute limit while the other is a percentage limit, eg `5Gi 20%`.
- No whitespace between value and suffix

<br/>

---

### freespace_plugin

The free space on the file system that holds the specified `path` on the specified `u@h:p` is checked. 
Expected free space may be an absolute value or a percentage. If the path does not exist, setup() will
pass but eval_status() will return RTN_WARNING and retry on each check_interval. This allows for 
intermittently missing paths.

**Typical string and dictionary-style config file lines:**

    MonType_Free		   =  freespace_plugin
    # Free_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <free_amount>  <path>
    Free_testhost2         =  me@testhost2    CRITICAL   5m   20%         /home/me
    Free_root              =  {'u@h:p':'local',  'recheck':'1d', 'rol':'10000000  /'}

**Plugin-specific _rest-of-line_ params:**

`free_amount` (integer or percentage)
- Minimum free number of 1K-blocks or percentage

`path` (str)
- Directory path on the specified `u@h:p` host

<br/>

---

### fsactivity_plugin

The age of files in a directory is checked for at least one file being more recent than `age` ago.
Note that sub-directories are not recursed - only the specified top-level directory is checked for the newest file.
Alternately, the age of a specific individual file may be checked.

**Typical string and dictionary-style config file lines:**

    MonType_Activity	       =  fsactivity_plugin
    # Activity_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <path>
    Activity_RAMDRIVE          =  local                    1h   15m  /mnt/RAMDRIVE/
    Activity_testhost2_log.csv =  {'u@h:p':'me@testhost2', 'critical':True, 'recheck':'30m', 'rol':'5m  /mnt/RAMDRIVE/log.csv'}

**Plugin-specific _rest-of-line_ params:**

`age` (timevalue, or int/float seconds)
- Max age of the path (newest file in the path directory or specific file)

`path` (str)
- A path to a directory is specified by ending the path with a `/`, else the path is taken as an individual file.

<br/>

---

### interface_plugin

The specified interface is queried with `ifconfig <interface_name>`, checking for 'UP' and 'RUNNING'.

**Typical string and dictionary-style config file lines:**

    MonType_Interface           =  interface_plugin
    # Interface_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <interface_name>
    Interface_testhost2_wlan0   =  me@testhost2  CRITICAL  1m  wlan0
    Interface_local_lo          =  {'recheck':'5m', 'rol':'lo'}

**Plugin-specific _rest-of-line_ params:**

`interface_name` (str)
- Name of the interface to be checked

Note: See README note regarding adding the ifconfig command path to the ssh session path environment.

<br/>

---

### pinghost_plugin

Ping the specified host. The `IPaddress_or_hostname` may be on the local LAN or external.

**Typical string and dictionary-style config file lines:**

    MonType_Host		        =  pinghost_plugin
    # Host_<friendly_name>      =  <local or user@host>  [CRITICAL]  <check_interval>  <IPaddress_or_hostname>
    Host_local_to_testhost2     =  local    CRITICAL   1h   testhost2
    Host_testhost2_to_yahoo.com =  {'u@h:p':'me@testhost2', 'recheck':'10m', 'rol':'yahoo.com'}

**Plugin-specific _rest-of-line_ params:**

`IPaddress_or_hostname` (str)

**Plugin-specific fail response:**

- If the ping of the `IPaddress_or_hostname` times out (subprocess.run() timeout) then 'Cannot contact target host' is the fail message.

<br/>

---

### process_plugin

Check that the specified process is alive by searching for the `executable_path` is in the output of a `ps -Af` call.

**Typical string and dictionary-style config file lines:**

    MonType_Process		      =  process_plugin
    # Process_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <executable_path>
    Process_x11vnc            =  local       CRITICAL  5m  /usr/bin/x11vnc
    Process_cups              =  {'u@h:p':'me@testhost2', 'recheck':'1h', 'rol':'/usr/sbin/cupsd'}

**Plugin-specific _rest-of-line_ params:**

`executable_path` (str)
- Full process path as shown in `ps`

<br/>

---

### selinux_plugin

Checks that the `sestatus` _Current mode:_ value matches the `expected_mode`.

**Typical string and dictionary-style config file lines:**

    MonType_SELinux		      =  selinux_plugin
    # SELinux_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <expected_mode>
    SELinux_localhost         =  local      5m       enforcing
    SELinux_localhost2        =  {'critical':True, 'recheck':'5m', 'rol':'enforcing'}

**Plugin-specific _rest-of-line_ params:**

`expected_mode` (str)
- 'enforcing' or 'permissive'

Note: If selinux is not installed on the target host, then this plugin reports "NOT IN EXPECTED STATE...".

<br/>

---

### service_plugin

Check that the specified service is active and running. Checking is done via `systemctl status 
<service name>` (for systemd) or `service <service_name> status` (for init).

**Typical string and dictionary-style config file lines:**

    MonType_Service           =  service_plugin
    # Service_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <service_name>
    Service_firewalld         =  local  CRITICAL  1m  firewalld
    Service_sshd              =  {'u@h:p':'me@testhost2', 'recheck':'10m', 'rol':'sshd'}

**Plugin-specific _rest-of-line_ params:**

`service_name` (str)
- Service name to be checked

<br/>

---

### webpage_plugin

The specified web page `url` is retrieved and checked that it contains the `expected_text`. 
The `url` may be on a local or remote server.

**Typical string and dictionary-style config file lines:**

    MonType_Page           =  webpage_plugin
    # Page_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <url>  <expected_text>
    Page_WeeWX             =  local  15m  http://localhost/weewx/  Current Conditions
    Page_xBrowserSync      =  {'u@h:p':'me@testhost2', 'recheck':'1h', 'rol':'https://www.xbrowsersync.org/  Browser syncing as it should be: secure, anonymous and free'}

**Plugin-specific _rest-of-line_ params:**

`url` (str)
- The local or remote url to be fetched

`expected_text` (str)
- Pass if the fetched url contains/includes the expected_text
- All text after the url is taken as the expected_text
- Leading and trailing whitespace is trimmed before the compare

Note: If the `url` or `expected_text` contains a `#` character then use the dictionary-style definition syntax to avoid the config file parser taking the # as the start of a comment.

<br/>

---

### yum_update_history_plugin

yum history output is searched for the specific `yum_command` text and the date is extracted from 
the first occurrence of this line, then compared to the `age` limit. May require root access in 
order to read yum history.

This plugin works equally well with newer Fedora-based systems (eg, RHEL 8+) that use the `dnf` command.  These
systems save the history in the yum database, and `dnf history` and `yum history` output the same content.                 

**Typical string and dictionary-style config file lines:**

    MonType_YumUpdate           =  yum_update_history_plugin
    # YumUpdate_<friendly_name> =  <local or user@host>  [CRITICAL]  <check_interval>  <age>  <yum_command>
    YumUpdate_MyHost            =  local  CRITICAL  1d  15d  update --skip-broken
    YumUpdate_MyHost2           =  {'recheck':'1d', 'rol':'30d  update'}

**Plugin-specific _rest-of-line_ params:**

`age` (timevalue, or int/float seconds)
- Max time allowed since last execution of the apt_command

`yum_command` (str)
- The yum history is scanned for this specific string
- Internal whitespace must match exactly.  Leading and trailing whitespace is trimmed off.

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