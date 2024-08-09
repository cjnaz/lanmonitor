# Writing new lanmonitor plugins

## Writing Monitor Plugins

New plugins may be added easily.  The core lanmonitor code provides a framework for configuration, logging, command retries, and parsing components.  The general process for creating a new plugin is:

- Copy an existing plugin, such as the `lanmonitor/src/lanmonitor/webpage_plug.py` to a working directory as `mynewitem_plugin.py`.
  - If the new plugin name is the same as a plugin in the lanmonitor distribution then the distribution version will
  be used and your new version will ignored.
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
            cmd_timeout     Max time in seconds allowed for the subprocess.run call in cmd_check()
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
      - In addition to the `Gateway` access check, if a monitor item is to be executed on a remote host (not `local`) and the results are not passing, then `cmd_check` double checks that ssh-based access to the target host is working.  `cmd_check` returns RTN_WARNING if there is an ssh access issue, versus RTN_PASS/RTN_FAIL for the specific checked item.  Your plugin should distinguish between ssh access vs. real failures.

3. The plugin module may be tested by running the companion `..._test.py` script.  Add tests to exercise your checking logic for both local and remote hosts, and for any warning/error traps.  (Note that the checking interval scheduling is handled in the lanmonitor core, so in the `dotest()` calls just set `'check_interval':1` as a placeholder.)

        dotest (1, "SELinux local - OK",
                {'key':'SELinux_local', 'tag':'local', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'  enforcing  '})

        dotest (2, "SELinux remote not running - ERROR",
                {'key':'SELinux_remote', 'tag':'remote', 'host':'testhost', 'user_host_port':'me@testhost', 'critical':False, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'enforcing'})

        dotest (3, "SELinux remote not running - CRITICAL",
                {'key':'SELinux_remote_CRIT', 'tag':'remote_CRIT', 'host':'testhost', 'user_host_port':'me@testhost', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'enforcing'})

        dotest (4, "SELinux expected badmode - setup ERROR",
                {'key':'SELinux_badmode', 'tag':'badmode', 'host':'local', 'user_host_port':'local', 'critical':True, 'cmd_timeout':2, 'check_interval':1, 'rest_of_line':'enforcingX'})

        dotest (5, "No such host - WARNING",
                {'key':'SELinux_Unknown', 'tag':'Unknown', 'host':'nosuchhost', 'user_host_port':'me@nosuchhost', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'enforcing'})

        dotest (6, "Known host, unavailable - WARNING",
                {'key':'SELinux_Unavailable', 'tag':'Unavailable', 'host':'testhostX', 'user_host_port':'me@testhostX', 'critical':True, 'cmd_timeout':4, 'check_interval':1, 'rest_of_line':'enforcing'})


<br/>

---

## Writing Notification Handler Plugins

One or more notification handlers may be specified in the configuration file line, such as:

      Notif_handlers		stock_notif   my_notif	# Whitespace separated list of notification handlers

The following functions within each listed notification handler are called.  The functionality as provided by `stock_notif` is describe here.  NOTE that the stock_notif handler module need not be used.

- `log_event()` - Called after every monitored item, passing the dictionary returned by eval_status() (see above) onto log_event().  The stock_notif handler sends notifications on new FAIL and CRITICAL items, and clears any fail history of now-passing items.
- `each_loop()` - Called on every lanmonitor core _service loop_ (per ServiceLoopTime).  Place any general code here that needs to be executed on every iteration.  Unused by stock_notif.
- `renotif()` - Called on every lanmonitor core _service loop_ (per ServiceLoopTime).  Place any code here related to sending additional notifications for items that remain broken.  stock_notif sends repeat notification messages for any critical items on every `CriticalReNotificationInterval` period.  All still-broken critical items are bundled into a single message so as to minimize text messages being sent.
- `summary()` - Called on every lanmonitor core _service loop_ (per ServiceLoopTime).  Place any code here related to scheduling and producing a periodic report.  The lanmonfuncs.py module provides `next_summary_timestring()`, which uses `SummaryTime` and `SummaryDays` in the config file, for summary scheduling.  stock_notif's summary simply emails a list of any current WARNING, FAIL, or CRITICAL items, or an "All is well" message to provide a periodic _lanmonitor-is-alive_ message.
