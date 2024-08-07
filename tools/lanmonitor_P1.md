# lanmonitor - Keeping watch on the health of your network resources

lanmonitor keeps tabs on key resources in your LAN environment (not actually limited to your LAN).  A text message notification (and/or email) is sent for any monitored _item_ that's out of sorts (not running, not responding, too old, ...).  Periodic re-notifications are sent for
critical items, such as firewalld being down, and summary reports are generated up to daily.

- lanmonitor uses a plug-in architecture, and is easily extensible for new items to monitor and new reporting/notification needs.
- A configuration file is used for all setups - no coding required for use.  The config file may be modified on-th-fly while lanmonitor is running as a service.
- Checks may be executed from the local machine, or from any remote host (with ssh access).  For example, you can check the health of a service running on another machine, or check that a webpage is accessible from another machine.

Supports Python 3.7+.
