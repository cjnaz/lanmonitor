#!/usr/bin/env python3 
"""LAN monitor stock notifications handler
"""

__version__ = "3.1"

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.1 230320 - Debug mode status dump 
# 3.0 230301 - Packaged
# V2.0  221130  Dropped --once, added --service.  Added on-demand summary.
# V1.4  221120  Summaries optional if SummaryDays is not defined.
# V1.3  220420  Incorporated funcs3 timevalue and retime
# V1.2  220217  Allow logging of repeat warnings when the log level is INFO or DEBUG.  Catch snd_notif/snd_email fails.
# V1.1c 220101  Bug fix - clear prior events on config file reload (re-init of notification handlers)
# V1.1b 210604  Logging fix for logging fails in service mode and LoggingLevel 20
# V1.1a 210529  Notification and logging fix along with funcs3 V0.7a
# V1.1  210523  Added LogSummary switch
# V1.0  210507  New
#
# Changes pending
#   
#==========================================================

import datetime
import __main__
from cjnfuncs.core import logging
from cjnfuncs.timevalue import timevalue
from cjnfuncs.SMTP import snd_email, snd_notif


import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import next_summary_timestring, RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
from lanmonitor.lanmonitor import inst_dict

# Configs / Constants
HANDLER_NAME = "stock_notif"
NOTIF_SUBJ = "LAN Monitor"


class notif_class:

    events = {}
    next_summary = None
    next_renotif = None

    def __init__(self):
        logging.debug (f"Notif handler <{__name__}> initialized")
        self.next_summary = next_summary_timestring()
        if not globvars.args.service:
            self.next_summary = datetime.datetime.now()     # force summary in interactive debug level logging 
        self.next_renotif = datetime.datetime.now().replace(microsecond=0)  # forcing int seconds keeps logging value prettier
        self.events.clear()

    def are_criticals (self):
        """ Returns True if there are any critical events in the events dictionary.
        """
        for event in self.events:
            if self.events[event]["criticality"] == RTN_CRITICAL:
                return True
        return False

    def log_event (self, dict):
        """ Handle any logging for each event status type
        Passed in dict keys:
            notif_key   - Corresponds to the monitortype_key in the config file
            rslt
                RTN_PASS     - Clears any prior logged WARNING / FAIL / CRITICAL events
                RTN_WARNING  - Logged and included in summary, but no notification.
                RTN_FAIL     - Logged & notified
                RTN_CRITICAL - Logged & notified, with periodic renotification
            message     - Message text from the monitor plugin
        All notifications are disabled if config NotifList is not defined.
        """

        if dict["rslt"] == RTN_PASS:
            logging.info(dict["message"])
            if dict["notif_key"] in self.events:
                del self.events[dict["notif_key"]]
                logging.warning(f"  Event {dict['notif_key']} now passing.  Removed from events log.")
            return

        if dict["rslt"] == RTN_WARNING:                 # Normally log a warning only once so as to not flood the log
            if dict["notif_key"] not in self.events  or  logging.getLogger().level < logging.WARNING:
                logging.warning(dict["message"])

        else:       # RTN_FAIL and RTN_CRITICAL cases
            if dict["rslt"] == RTN_CRITICAL:
                # if there are no prior active criticals, then set renotif time to now + renotif value
                if self.next_renotif < datetime.datetime.now()  and  not self.are_criticals():
                    self.next_renotif += datetime.timedelta(seconds=timevalue(globvars.config.getcfg("CriticalReNotificationInterval")).seconds)
                    if globvars.args.service:
                        logging.debug(f"Next critical renotification:  {self.next_renotif}")
            if globvars.args.service:
                if dict["notif_key"] not in self.events:
                    if globvars.config.getcfg("NotifList", False, section='SMTP'):
                        try:
                            snd_notif (subj=NOTIF_SUBJ, msg=dict["message"], log=True, smtp_config=globvars.config)
                        except Exception as e:
                            logging.warning(f"snd_notif failed.  Email server down?:\n        {dict['message']}\n        {e}")
                    else:
                        logging.warning(dict["message"])
            else:   # non-service mode
                logging.warning(dict["message"])

        self.events[dict["notif_key"]] = {"message": dict["message"], "criticality": dict["rslt"]}


    def each_loop(self):
        """ Status dump enabled either by:
            Signal SIGUSR2
            Debug level logging (args verbose == 2) and non-service mode
        """
        logging.debug (f"Entering: {HANDLER_NAME}.each_loop()")

        if not globvars.sig_status  and  not (not globvars.args.service  and  globvars.args.verbose == 2):
            return
        globvars.sig_status = False

        status_log = f"  {'Monitor item'.ljust(globvars.keylen)}  Prior run time       Next run time          Last check status\n"
        for key in inst_dict:
            if key in self.events:
                status = self.events[key]['message']
            else:
                status = "  OK"
            status_log += f"  {key.ljust(globvars.keylen)}  {inst_dict[key].prior_run}  {inst_dict[key].next_run}  {status}\n"
            # NOTE - prior_run vars are not defined until after first run.  each_loop() isn't called until after check items have been run, so _shouldn't_ crash.

        logging.warning(f"On-demand status dump:\n{status_log}")


    def renotif(self):
        """ Periodically send a consolidated notification with all current critical events.
        if renotif time passed then
            if there are active criticals then
                send consolidated renotif message
            else
                set renotif time = now, which allows next critical to be notified immediately
        All notifications are disabled if config NotifList is not defined.
        """
        logging.debug (f"Entering: {HANDLER_NAME}.renotif()")

        if not globvars.config.getcfg("NotifList", False, section='SMTP'):
            return
        
        if (self.next_renotif < datetime.datetime.now()):
            if self.are_criticals():
                criticals = ""
                for event in self.events:
                    if self.events[event]["criticality"] == RTN_CRITICAL:
                        criticals += f"\n  {self.events[event]['message']}"
                try:
                    snd_notif (subj=NOTIF_SUBJ, msg=criticals, log=True, smtp_config=globvars.config)
                except Exception as e:
                    logging.warning(f"snd_notif failed.  Email server down?:\n        {criticals}\n        {e}")

                self.next_renotif += datetime.timedelta(seconds=timevalue(globvars.config.getcfg("CriticalReNotificationInterval")).seconds)
                logging.debug(f"Next critical renotification:  {self.next_renotif}")
            else:
                self.next_renotif = datetime.datetime.now().replace(microsecond=0)


    def summary(self):
        """ Periodically produce a summary and email it and print it in the log file.

        Config file params
            SummaryDays, SummaryTime - processed by lanmonfuncs.next_summary_timestring().
                Comment out SummaryDays to disable periodic summaries.
            EmailTo - Whitespace separated list of email addresses.
                Comment out EmailTo to disable emailing of summaries.
            LogSummary - Cause the summary to be printed to the log file.
        
        Summary debug feature:  The summary will be printed when running in non-service 
        mode and debug level logging.

        On-demand summary feature:  In service mode, a summary may be forced by placing a 
        file named "summary" in the program directory.  The file will be deleted and the 
        summary will be printed to the log file.
        """

        logging.debug (f"Entering: {HANDLER_NAME}.summary()")

        if globvars.sig_summary:
            globvars.sig_summary = False
            sum = ""
            if len(self.events) == 0:
                sum += "  No current events.  All is well."
            else:
                for event in self.events:
                    sum += f"{self.events[event]['message']}\n"
            logging.warning(f"On-demand summary:\n{sum}")

        if self.next_summary:       # Will be None if SummaryDays is not defined.
            if (self.next_summary < datetime.datetime.now())  or  not globvars.args.service:
                sum = ""
                if len(self.events) == 0:
                    sum += "  No current events.  All is well."
                else:
                    for event in self.events:
                        sum += f"{self.events[event]['message']}\n"

                if not globvars.args.service:
                    logging.debug(f"lanmonitor status summary:\n{sum}")
                    return

                if globvars.config.getcfg("EmailTo", False, section='SMTP'):
                    try:
                        snd_email(subj="lanmonitor status summary", body=sum, 
                                  to=globvars.config.getcfg("EmailTo", section='SMTP'), 
                                  log=True, smtp_config=globvars.config)
                    except Exception as e:
                        logging.warning(f"snd_summary failed.  Email server down?:\n        {e}")

                if globvars.config.getcfg("LogSummary", False):
                    logging.warning(f"Summary:\n{sum}")

                self.next_summary = next_summary_timestring()