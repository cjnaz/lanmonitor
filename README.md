# lanmonitor

lanmonitor tracks the state of services, processes, web pages, and local directories in your server and local area network.  
A text message notification is sent for any/each monitored _item_ that's out of sorts (not running, not responding, ...).

## Usage
```
$ ./lanmonitor -h
usage: lanmonitor [-h] [-1] [-V]

LAN monitor
V0.1 210129

optional arguments:
  -h, --help     show this help message and exit
  -1, --once     Single run mode.  Logging is to console rather than file.
  -V, --version  Return version number and exit.
```

## Example output
```
$ ./lanmonitor -1
Host OK:  Printer_Server    at 192.168.1.44
Service OK:  plexmediaserver
Service <weewx> is NOT running
Service OK:  httpd
Service OK:  firewalld
Service OK:  smb
Service OK:  sshd
Page OK:  WeeWX
Process OK:  x11vnc
STALE FILES at Activity <MyServer_backups> (/mnt/share/MyServerBackups/*)
```
## Setup and Usage notes
- Supported on Python3 only.  Developed on Centos 7.8 with Python 3.6.8.
- Place the files in a directory on your server.
- Install the Python requests library - used for Page checks.
- Edit the config info in the `lanmonitor.cfg` file.  Enter your mail server credentials and notification address.  See below for item settings.
  - `RecheckInterval` sets how long between rechecks.
  - `ReNotificationInterval` sets how long between repeated notifications for each monitored item.  
- Install lanmonitor as a systemd service (google how).  An example `lanmonitor.service` file is provided.  Note that the config file may be modified while the service is running, with changes taking effect immediately.
- A text message is sent for each monitored item that is not in a good state.  A repeated text message will be sent after the `ReNotificationInterval`.


## Monitored items setup
Items to be monitored are defined in the lanmonitor.cfg file.  
- **Services** specifies a list of systemd service names to be checked.  Only one `Services` line is allowed.  Each service name is checked with a `systemctl status <service name>`, checking for the response `active (running)`.

      Services			plexmediaserver weewx firewalld smb sshd

- **Hosts** to be monitored are listed on separate lines as below.  Each host is pinged.  The `friendly_host_name` is user defined (not the real hostname).  `<IP address or hostname>` may be internal (local LAN) or external.

      Host_<friendly_host_name>    <IP address or hostname>
      Host_RPi1_HP1018    192.168.1.44
      Host_Yahoo          Yahoo.com

- **Web pages** to be monitored are listed on separate lines as below.  Each URL is read and checked for the `<expected text>`, which starts at the first non-white-space character after the URL and up to the end of the line or a `#` comment character.  Leading and trailing white-space is trimmed off.  The url may be on a remote server.

      Page_<friendly_page_name>    <url>    <expected text>
      Page_WeeWX    http://localhost/weewx/    Current Conditions
      Page_xBrowserSync    https://www.xbrowsersync.org/    Browser syncing as it should be: secure, anonymous and free! # Check it out!


- **Processes** to be monitored are listed on separate lines as below.  Each process is checked by seeing if the `<executable path>` occurs in the output of a `ps -Af` call.  

      Process_<friendly_process_name>    <executable path>
      Process_x11vnc		/usr/bin/x11vnc

- **Filesystem activities** to be monitored are listed on separate lines as below.  The age of files at the `<path to directory or file>` is checked for at least one file being more recent than `<days>` ago.

      Activity_<friendly_path_name>    <days>    <path to directory or file>
      Activity_MyServer_backups  8 /mnt/share/MyServerBackups


## Known issues:
- none

## Version history
- 210129 v0.1  New