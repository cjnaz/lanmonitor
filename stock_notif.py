#!/usr/bin/env python3
"""LAN monitor notifications handler
"""

__version__ = "V1.1a 210529"

#==========================================================
#
#  Chris Nelson, 2021
#
# V1.1a 210529  Notification and logging fix along with funcs3 V0.7a
# V1.1  210523  Added LogSummary switch
# V1.0  210507  New
#
# Changes pending
#   
#==========================================================

import sys
import os.path
import datetime
import globvars
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../funcs3/'))
from funcs3 import getcfg, snd_email, snd_notif, logging
from lanmonfuncs import next_summary_timestring, convert_time, RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL

# Configs / Constants
HANDLER_NAME = "stock_notif"
NOTIF_SUBJ = "LAN Monitor"


class notif_class:

    events = {}
    next_summary = None
    next_renotif = None

    def __init__(self):
        self.next_summary = next_summary_timestring()
        self.next_renotif = datetime.datetime.now().replace(microsecond=0)
        pass

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
        """

        if dict["rslt"] == RTN_PASS:
            logging.info(dict["message"])
            if dict["notif_key"] in self.events:
                del self.events[dict["notif_key"]]
                logging.warning(f"  Event {dict['notif_key']} now passing.  Removed from events log.")
            return

        if dict["rslt"] == RTN_WARNING:
            if dict["notif_key"] not in self.events:
                logging.warning(dict["message"])

        else:       # RTN_FAIL and RTN_CRITICAL cases
            if dict["rslt"] == RTN_CRITICAL:
                # if there are no prior active criticals, then set renotif time to now + renotif value
                if self.next_renotif < datetime.datetime.now()  and  not self.are_criticals():
                    self.next_renotif = datetime.datetime.now().replace(microsecond=0) + datetime.timedelta(seconds=convert_time(getcfg("CriticalReNotificationInterval"))[0])
                    if not globvars.args.once:
                        logging.info(f"Next critical renotification:  {self.next_renotif}")
            if dict["notif_key"] not in self.events  and  not globvars.args.once:
                snd_notif (subj=NOTIF_SUBJ, msg=dict["message"], log=True)
            if dict["notif_key"] not in self.events  and  globvars.args.once:
                logging.warning(dict["message"])

        self.events[dict["notif_key"]] = {"message": dict["message"], "criticality": dict["rslt"]}


    def each_loop(self):
        """ Called every service loop (10 seconds)
        """
        logging.debug (f"Entering: {HANDLER_NAME}.each_loop")


    def renotif(self):
        """ Periodically send a consolidated notification with all current critical events
        if renotif time passed then
            if there are active criticals then
                send consolidated renotif message
            else
                set renotif time = now, which allows next critical to be notified immediately
        """
        logging.debug (f"Entering: {HANDLER_NAME}.renotif")
        if (self.next_renotif < datetime.datetime.now()):
            logging.debug (f"self.next_renotif:        {self.next_renotif}")
            logging.debug (f"datetime.datetime.now():  {datetime.datetime.now()}")

            if self.are_criticals():
                criticals = ""
                for event in self.events:
                    if self.events[event]["criticality"] == RTN_CRITICAL:
                        criticals += f"  {self.events[event]['message']}\n"
                snd_notif (subj=NOTIF_SUBJ, msg=criticals, log=True)
                self.next_renotif = datetime.datetime.now().replace(microsecond=0) + datetime.timedelta(seconds=convert_time(getcfg("CriticalReNotificationInterval"))[0])
                logging.info(f"Next critical renotification:  {self.next_renotif}")
            else:
                self.next_renotif = datetime.datetime.now().replace(microsecond=0)


    def summary(self):
        logging.debug (f"Entering: {HANDLER_NAME}.summary")
        if (self.next_summary < datetime.datetime.now())  or  globvars.args.once:
            sum = ""
            if len(self.events) == 0:
                sum += "  No current events.  All is well."
            else:
                for event in self.events:
                    sum += f"{self.events[event]['message']}\n"

            if globvars.args.once:
                logging.debug(f"lanmonitor status summary\n{sum}")
                return

            snd_email(subj="lanmonitor status summary", body=sum, to=getcfg("EmailTo"), log=True)

            if getcfg("LogSummary", False):
                logging.warning(f"Summary:\n{sum}")

            self.next_summary = next_summary_timestring()

