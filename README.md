# lanmonitor

lanmonitor tracks the state of SELinux, hosts, services, web pages, processes, and local filesystem age on machines (hosts/VMs/servers...) on the local area network.  
A text message notification is sent for any/each monitored _item_ that's out of sorts (not running, not responding, ...).  Periodic re-notifications are sent for
critical items, such as firewalld being down, and summary reports are generated up to daily.

## Usage
```
$ ./lanmonitor -h
usage: lanmonitor [-h] [-1] [-v] [--config-file CONFIG_FILE]
                  [--log-file LOG_FILE] [--smtp-creds-file SMTP_CREDS_FILE]
                  [-V]

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
V0.6 210415

optional arguments:
  -h, --help            show this help message and exit
  -1, --once            Single run mode.  Logging is to console rather than file.
  -v, --verbose         Display OK items in --once mode. (Set by LoggingLevel in config file for non --once mode.)
  --config-file CONFIG_FILE
                        Path to config file (default </mnt/share/dev/python/lanmonitor/github/lanmonitor.cfg>).
  --log-file LOG_FILE   Path to log file (default </mnt/share/dev/python/lanmonitor/github/log_lanmonitor.txt>).
  --smtp-creds-file SMTP_CREDS_FILE
                        Path to SMTP credentials file (default </home/<user>/creds_SMTP>).
  -V, --version         Return version number and exit.
```

## Example output
```
$ ./lanmonitor --once --verbose
SELinux_local  OK - local - enforcing
Host_RPi2_TempMon    OK - local - rpi2.lan
Host_Printer_Server  OK - local - 192.168.1.44
FAIL: Host_RPi3_from_RPi1 - rpi1.lan - HOST RPi3.lan IS NOT RESPONDING
Service_routermonitor    OK - local    - routermonitor
Service_wanstatus        OK - local    - wanstatus
Service_plexmediaserver  OK - local    - plexmediaserver
Service_firewalld        OK - local    - firewalld
CRITICAL: Service_xxx - local - SERVICE xxx IS NOT RUNNING
Page_WeeWX         OK - local - http://192.168.33.72/weewx/
Page_xBrowserSync  OK - rpi2  - https://www.xbrowsersync.org/
FAIL: Page_xxx - local - WEBPAGE http://localhost/xxx/ NOT FOUND
Process_x11vnc   OK - local    - /usr/bin/x11vnc
Process_tempmon  OK - RPi2.lan - python TempMon.py
WARNING: Process_xxxPi3 - RPi3.lan - HOST CANNOT BE REACHED
Activity_Win1_Image       OK - local -    5.8 days  (   6 days  max)  /mnt/share/backups/Win1/Image/
FAIL: Activity_Win2_Image  STALE FILES - local -    6.7 days  (   6 days  max)  /mnt/share/backups/Win2/Image/
Activity_CentOS_backupsd  OK - local -    0.7 days  (   8 days  max)  /mnt/share/backups/Shop2/
WARNING: Activity_xxx - local - COULD NOT GET ls OF PATH </mnt/share/backups/xxx/>
Activity_TiBuScrape       OK - local -    3.9 days  (   4 days  max)  /mnt/share/backups/TiBuScrapeArchive/
Activity_RPi2_log.csv     OK - rpi2  -    0.8 mins  (   5 mins  max)  /mnt/RAMDRIVE/log.csv
```

## Setup and Usage notes
- Supported on Python3.6+ only.  Developed on Centos 7.9 with Python 3.6.8.
- Place the files in a directory on your server.
- Create an SMTP/email credentials file at `~/creds_SMTP`.  Change the file protections to mode `600`.  Set this up for root as well if you will be running lanmonitor as a service.

      EmailUser	    yourlogin@mailserver.com
      EmailPass	    yourpassword

- Edit the config info in the `lanmonitor.cfg` file.  Enter your mail server address/port and notification/email addresses.  See below for item settings.
  - `nRetries` sets how many tries will be made to accomplish each monitored item.
  - `RetryInterval` sets the time between nRetries.
  - `StartupDelay` is a wait time when starting in service mode to allow everything to come up fully at system boot before checking items.
  - `RecheckInterval` sets how long between rechecks in service mode.
  - `CriticalReNotificationInterval` sets how long between repeated notifications for any failing CRITICAL monitored items in service mode.
  - `SummaryDays` sets the days of the week for summaries to be emailed.  Sunday =0, Monday =1, ... Saturday =6.  Multiple days may be selected.
  - `SummaryTime` sets the time of day for summaries to be emailed.  24-clock format, for example, `13:00`.
- Run the tool with `<path to>lanmonitor --once --verbose`.  Make sure that the local machine and user has ssh access to any remote machines.  (`-vv` turns on debug logging.)
- Install lanmonitor as a systemd service (google how).  An example `lanmonitor.service` file is provided.  Note that the config file may be modified while the service is running, with changes taking effect on the next RecheckInterval or Summary.  Make sure that the user (typically root) that the service runs under has ssh access to any remotes.
- A text message is sent for each monitored item that is in a FAIL or CRITICAL state.  CRITICAL items have a repeated text message sent after the `CriticalReNotificationInterval`.
- NOTE:  All time values in the config file may be entered with a `s` (seconds), `m` (minutes), `h` (hours), `d` (days), or `w` (weeks) suffix.  For example `6h` is 6 hours.  If no suffix is provided the time value is taken as seconds.


## Monitored items setup
Items to be monitored are defined in the lanmonitor.cfg file.  "Plugin" modules provide the logic for each monitored item type.  Six plugins are initially provided, below.
To activate a given plugin, a `MonType_` line is included in the configuration file using this format:

      MonType_<type>    <plugin_name>

1. Begins with the `MonType_` prefix
2. The `<type>` is used as the prefix on successive lines for this type
3. The `<plugin_name>` is the Python module name (implied .py suffix)


For monitored items, the general format of a line is

      <type>_<friendly_name>  <local or user@host>  [CRITICAL (optional)]  <rest_of_line>

1. `<type>` matches the corresponding `MonType_<type>` line.
2. `<friendly_name>` must be unique and is used for notifications, logging, etc.  This text is arbitrary - need not match any other info.
3. `<local or user@host>` specifies on which machine the check will be executed from.  If not local, then `user@host` specifies the ssh login on the remote machine.
4.  `CRITICAL` may optionally be specified.  CRITICAL tagged items are those that need immediate attention.  Renotifications are sent for these when failing.  (All non-passing items are listed in the periodically emailed summary.)
5. `<rest_of_line>` are the monitored type-specific settings.

### Supplied plugin specifics

- **SELinux** checks that the sestatus _Current mode:_ value matches the config file value.

      MonType_SELinux		selinux_plugin
      SELinux_<friendly_name>  <local or user@host>  [CRITICAL]  <enforcing or permissive>
      SELinux_localhost     local             enforcing


- **Hosts** to be monitored are listed on separate lines as below.  Each host is pinged.  The `friendly_name` is user defined (not the real hostname).  `<IP address or hostname>` may be internal (local LAN) or external.

      MonType_Host		pinghost_plugin
      Host_<friendly_name>  <local or user@host>  [CRITICAL]  <IP address or hostname>
      Host_RPi1_HP1018    local    CRITICAL 192.168.1.44
      Host_Yahoo          me@RPi2.mylan    Yahoo.com

- **Services** to be monitored are listed on separate lines as below.  Each service name is checked with a `systemctl status <service name>` (for systemd) or `service <service_name> status` (for init), checking for the active/running response.

      MonType_Service		service_plugin
      Service_<friendly_name>  <local or user@host>  [CRITICAL]  <service name>
      Service_firewalld       local			CRITICAL  firewalld
      Service_RPi1_HP1018     me@RPi1.mylan     cups

- **Web pages** to be monitored are listed on separate lines as below.  Each URL is read and checked for the `<expected text>`, which starts at the first non-white-space character after the URL and up to the end of the line or a `#` comment character.  Leading and trailing white-space is trimmed off.  The url may be on a remote server.

      MonType_Page		webpage_plugin
      Page_<friendly_name>  <local or user@host>  [CRITICAL]  <url>  <expected text>
      Page_WeeWX              local             http://localhost/weewx/             Current Conditions
      Page_xBrowserSync       me@RPi2.mylan     https://www.xbrowsersync.org/       Browser syncing as it should be: secure, anonymous and free! # Check it out!

- **Processes** to be monitored are listed on separate lines as below.  Each process is checked by seeing if the `<executable path>` occurs in the output of a `ps -Af` call.  

      MonType_Process		process_plugin
      Process_<friendly_name>  <local or user@host>  [CRITICAL]  <executable path>
      Process_x11vnc		local       CRITICAL  /usr/bin/x11vnc


- **Filesystem activities** to be monitored are listed on separate lines as below.  The age of files at the `<path to directory or file>` is checked for at least one file being more recent than `<age>` ago.  Age values are the allowed time values (see note up above).  Note that sub-directories are not recursed - only the listed top-level directory is checked for the newest file.

      MonType_Activity	fsactivity_plugin
      Activity_<friendly_name>  <local or user@host>  [CRITICAL]  <age>  <path to directory or file>
      Activity_MyServer_backups     local       8d    /mnt/share/MyServerBackups
      Activity_RPi2_log.csv         rpi2.mylan  CRITICAL  5m    /mnt/RAMDRIVE/log.csv


## Writing Plugins

New plugins may be added easily.  The core lanmonitor code provides a complete framework for configuration logging, notifications, summaries, command retries, and parsing components.  The general process for creating a new plugin is:

- Copy an existing plugin, such as the webpage_plug.py
- Adjust the module comment block to have your new plugin name
- Within the `# Construct item type specifics and check validity` section
  - Adjust the `rest_of_line` parsing, creating new vars as needed
  - Add any checker code to validate these new values
  - Within the `# Process the item` section
    - Adjust the `cmd` for your needed subprocess call command
    - The call to `lanmonfuncs.cmd_check` can check the returncode or return text.  It also returns the full subprocess call response.  Uncomment the `# print (rslt)` line to see what's available for building response checker code.
    - Adjust the `if rslt[0] == True: … return` lines for the PASS, FAIL, and CRITICAL return codes.
  - Adjust the tests at the bottom to exercise all possible good, bad, and invalid conditions.
  - Add the `MonType_` line and specific monitor items to your config file.

### Additional plugin writing notes
1. Your plugin will be called by the core system, passing a dictionary of data parsed from the config file.  Various provided dictionary keys are intended to help keep the plugin code relatively clean:

        """ Primary function for checking the status of this item type.
        Passed in item dictionary keys:
            key             Full 'itemtype_tag' key value from config file line
            keylen          string length of longest key of this item type
            tag             'tag' portion only from 'itemtype_tag' from config file line
            user_host       'local' or 'user@hostname' from config file line
            host            'local' or 'hostname' from config file line
            hostlen         string length of longest host of this item type
            critical        True if 'CRITICAL' is in the config file line
            rest_of_line    Remainder of line after the 'user_host' from the config file line

2. Your plugin needs to return a dictionary with 3 keys:

        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details

3. Parsing out item type specifics

        # Construct item type specifics and check validity
        key = item["key"]
        key_padded = key.ljust(item["keylen"])
        host = item["host"]
        host_padded = host.ljust(item["hostlen"])           # This and lines above generally don't need edits
        xx = item["rest_of_line"].split(maxsplit=1)         # Modify these lines to break out the rest_of_line specifics
        url = xx[0]
        match_text = xx[1]

4. If the check is to be run on a remote host, this section checks that the host can be accessed (with a ping, and returns RTN_WARNING if fails) before attempting to run the plugin specific checks.  This code needs no edits.

        # Check for remote access if non-local
        if host != "local":
            pingrslt = lanmonfuncs.cmd_check(["ping", host, "-c", "1"], user_host="local", return_type="cmdrun")
            if not pingrslt[0]:
                return {"rslt":RTN_WARNING, "notif_key":key, "message":f"WARNING: {key} - {host} - HOST CANNOT BE REACHED"}

5. The call to `lanmonfuncs.cmd_check` provides a nice wrapper for error traps, retries, and convenient status return.  See the lanmonfuncs module for more details.

        # Process the item
        cmd = ["curl", url, "--connect-timeout", "10", "--max-time", "10"]
        rslt = lanmonfuncs.cmd_check(cmd, user_host=item["user_host"], return_type="check_string", expected_text=match_text)
        # print (rslt)        # Uncomment this to see what-all is returned


6. The `rslt` is a tuple with the boolean first item indicating pass/fail of the cmd_check call, which may be sufficient for making your check pass/fail decision.  The second tuple item is the complete subprocess return structure which may be picked at by your code. The `keylen` and `hostlen` items from above are used for creating space-padded text for the passing result message, making the final output much more readable.  Fail messages don't use the padding, and by design are quite noticeable in the output.

        if rslt[0] == True:             # Pass condition
            return {"rslt":RTN_PASS, "notif_key":key, "message":f"{key_padded}  OK - {host_padded} - {url}"}
        else:
            if item["critical"]:
                return {"rslt":RTN_CRITICAL, "notif_key":key, "message":f"CRITICAL: {key} - {host} - WEBPAGE {url} NOT AS EXPECTED"}
            else:
                return {"rslt":RTN_FAIL, "notif_key":key, "message":f"FAIL: {key} - {host} - WEBPAGE {url} NOT AS EXPECTED"}

7. The plugin module may be tested standalone by running it directly on the command line.  Some items are needed from the config file (such as nRetries), thus the `--config-file` switch.

        if __name__ == '__main__':
            import argparse
            from funcs3 import loadconfig

            CONFIG_FILE = "lanmonitor.cfg"

            parser = argparse.ArgumentParser(description=__doc__ + __version__, formatter_class=argparse.RawTextHelpFormatter)
            parser.add_argument('--config-file', default=CONFIG_FILE,
                                    help=f"Path to config file (default <{CONFIG_FILE}>).")
            parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__,
                                    help="Return version number and exit.")

            lanmonfuncs.args = parser.parse_args()
            loadconfig(cfgfile=lanmonfuncs.args.config_file)

            inst = monitor()
            
            test = {"key":"Page_WeeWX", "keylen":20, "tag":"WeeWX","host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"http://localhost/weewx/ Current Conditions"}
            print(f"{test}\n  {inst.eval_status(test)}\n")
            test = {"key":"Page_WeeWX-X", "keylen":20, "tag":"WeeWX-X","host":"local", "user_host":"local", "hostlen":10, "critical":False, "rest_of_line":"http://localhost/weewx/ XCurrent Conditions"}
            print(f"{test}\n  {inst.eval_status(test)}\n")
            test = {"key":"Page_Bogus", "keylen":20, "tag":"Bogus","host":"local", "user_host":"local", "hostlen":10, "critical":True, "rest_of_line":"http://localhost/bogus/ whatever"}
            print(f"{test}\n  {inst.eval_status(test)}\n")
            test = {"key":"Page_xBrowserSync", "keylen":20, "tag":"xBrowserSync","host":"rpi1.lan", "user_host":"pi@rpi1.lan", "hostlen":10, "critical":False, "rest_of_line":"https://www.xbrowsersync.org/ Browser syncing as it should be: secure, anonymous and free!"}
            print(f"{test}\n  {inst.eval_status(test)}\n")
            test = {"key":"Page_WeeWX_from_badhost", "keylen":20, "tag":"WeeWX_from_badhost","host":"nonhost.lan", "user_host":"jack@nonhost.lan", "hostlen":10, "critical":False, "rest_of_line":"http://localhost/weewx/ Current Conditions"}
            print(f"{test}\n  {inst.eval_status(test)}\n")

            sys.exit()

## Known issues:
- none

## Version history
- V0.6 200415  Refactored to checker plugin model, many other changes
- V0.5 200312  Added checks on other hosts via ssh.
- V0.4 200304  Added StartupDelay for service mode.  Added SELinux check.
- V0.3 200226  Bug fix for files mod time vs. create time
- V0.2 210207  Added age info to Activity log
- V0.1 210129  New