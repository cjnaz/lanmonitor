# lanmonitor

lanmonitor tracks the state of SELinux, hosts, services, web pages, processes, and local filesystem age on machines (hosts/VMs/servers...) local area network.  
A text message notification is sent for any/each monitored _item_ that's out of sorts (not running, not responding, ...).

## Usage
```
$ ./lanmonitor -h
usage: lanmonitor [-h] [-1] [-v] [-V]

LAN monitor

Monitor these local network items, and send notification when something doesn't look right:
    SELinux status
    Hosts ping response
    Systemd services active and running
    Web pages responding with expected text
    Processes existing
    Filesystem age

Operates as a systemd service, or interactively with --once switch.
V0.5 210312

optional arguments:
  -h, --help     show this help message and exit
  -1, --once     Single run mode.  Logging is to console rather than file.
  -v, --verbose  Display OK items in --once mode.
  -V, --version  Return version number and exit.
```

## Example output
```
$ ./lanmonitor --once --verbose
SELinux OK:  local - enforcing
Host OK:  local - RPi2_TempMon   at RPi7.mylan
Host OK:  local - Printer_Server    at 192.168.1.44
HOST SYSTEM <rpi1 - RPi3_from_RPi1> AT RPi3 IS NOT RESPONDING
Service OK:  local - wanstatus
SERVICE <local - xxx> IS NOT RUNNING
Service OK:  local - httpd
Service OK:  local - routermonitor
Service OK:  RPi2.mylan - sshd
SERVICE <RPi2.mylan - httpd> IS NOT RUNNING
PAGE <local - xxx> IS NOT RUNNING
Page OK:  local - WeeWX
Page OK:  local - xBrowserSync
Process OK:  local - x11vnc
PROCESS <local - xxx> IS NOT RUNNING
Process OK:  RPi2.mylan - tempmon
File activity OK:         local - Win1_Backups           0.4 days  (   2 days  max)  /mnt/share/backups/Win1
STALE FILES AT ACTIVITY:  local - Win2_Backups           6.4 days  (   2 days  max)  /mnt/share/backups/Win2
File activity OK:         rpi2.mylan - RPi2_log.csv           0.8 mins  (   5 mins  max)  /mnt/RAMDRIVE/log.csv
```

## Setup and Usage notes
- Supported on Python3 only.  Developed on Centos 7.8 with Python 3.6.8.
- Place the files in a directory on your server.
- Edit the config info in the `lanmonitor.cfg` file.  Enter your mail server credentials and notification address.  See below for item settings.
  - `StartupDelay` is a wait time in seconds when starting in service mode to allow everything to come up fully at system boot before checking items.
  - `RecheckInterval` sets how long between rechecks in service mode.
  - `ReNotificationInterval` sets how long between repeated notifications for each monitored item in service mode.
- Run the tool with `<path to>lanmonitor --once --verbose`.  Make sure that the local machine and user has ssh access to any remote machines.
- Install lanmonitor as a systemd service (google how).  An example `lanmonitor.service` file is provided.  Note that the config file may be modified while the service is running, with changes taking effect immediately.  Make sure that the user (typically root) that the service runs under has ssh access to any remotes.
- A text message is sent for each monitored item that is not in a good state.  A repeated text message will be sent after the `ReNotificationInterval`.


## Monitored items setup
Items to be monitored are defined in the lanmonitor.cfg file.  

The general format of a line is

1. The monitor type keyword (SELinux_, Host_, Services_, Page_, Process_, or Activity_), with an attached _friendly_name_ used in results logging.
2. The machine to be checked - either the keyword _local_ or a user_name@machine_name pair.
3. Type specific info.

- **SELinux** checks that the sestatus _Current mode:_ value matches the config file value

      SELinux_<friendly_name>    <local or user@host>     <enforcing or permissive>
      SELinux_local     local             enforcing


- **Hosts** to be monitored are listed on separate lines as below.  Each host is pinged.  The `friendly_name` is user defined (not the real hostname).  `<IP address or hostname>` may be internal (local LAN) or external.

      Host_<friendly_name>    <local or user@host>    <IP address or hostname>
      Host_RPi1_HP1018    local    192.168.1.44
      Host_Yahoo          me@RPi2.mylan    Yahoo.com

- **Services** specifies a list of systemd service names to be checked on the target machine.  Each service name is checked with a `systemctl status <service name>`, checking for the response `active (running)`.

      Services_<friendly_name>    <local or user@host>    <space separated list of service names>
      Services_local          local			plexmediaserver weewx firewalld smb sshd
      Services_RPi1_HP1018    me@RPi1.mylan     cups

- **Web pages** to be monitored are listed on separate lines as below.  Each URL is read and checked for the `<expected text>`, which starts at the first non-white-space character after the URL and up to the end of the line or a `#` comment character.  Leading and trailing white-space is trimmed off.  The url may be on a remote server.

      Page_<friendly_name>    <local or user@host>    <url>    <expected text>
      Page_WeeWX              local             http://localhost/weewx/             Current Conditions
      Page_xBrowserSync       me@RPi2.mylan     https://www.xbrowsersync.org/       Browser syncing as it should be: secure, anonymous and free! # Check it out!


- **Processes** to be monitored are listed on separate lines as below.  Each process is checked by seeing if the `<executable path>` occurs in the output of a `ps -Af` call.  

      Process_<friendly_name>    <local or user@host>    <executable path>
      Process_x11vnc		local       /usr/bin/x11vnc


- **Filesystem activities** to be monitored are listed on separate lines as below.  The age of files at the `<path to directory or file>` is checked for at least one file being more recent than `<age>` ago.  Age values are a numeric value followed by `m`, `h`, or `d` for minutes, hours, or days.  Note that sub-directories are not recursed - only the listed top-level directory is checked for the newest file.

      Activity_<friendly_name>    <local or user@host>    <age>    <path to directory or file>
      Activity_MyServer_backups     local       8d    /mnt/share/MyServerBackups
      Activity_RPi2_log.csv         rpi2.mylan  5m    /mnt/RAMDRIVE/log.csv


## Known issues:
- none

## Version history
- V0.5 200312  Added checks on other hosts via ssh.
- V0.4 200304  Added StartupDelay for service mode.  Added SELinux check.
- V0.3 200226  Bug fix for files mod time vs. create time
- V0.2 210207  Added age info to Activity log
- V0.1 210129  New