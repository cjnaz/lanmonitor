#!/usr/bin/env python3
"""LAN monitor support functions
"""

__version__ = "V0.6 210415"

#==========================================================
#
#  Chris Nelson, 2021
#
# V0.6 200415  Support newest file activity being a link, Weeks time values, SysV-style service check
#
# Changes pending
#   
#==========================================================

import sys
import os.path
import subprocess
import datetime
import time
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../funcs3/'))
from funcs3 import *

# Configs / Constants
NOTIF_SUBJ = "LAN Monitor"
RTN_PASS     = 0
RTN_WARNING  = 1
RTN_FAIL     = 2
RTN_CRITICAL = 3


# Module global vars
args = None


def convert_time (timeX):
    """ Given time value term such as 90s, 15m, 20h, 3d, 2w return int seconds and units.
        <1h> returns (3600, "hours")
    If no units suffix, the value is interpreted as secs.
        <90> returns (90, "secs ")
    """
    if type(timeX) is int:
        return timeX, "secs "           # Case Int
    try:
        return int(timeX), "secs "      # Case Str without units
    except:
        pass
    try:                                # Case Str with units
        time_value = int(timeX[:-1])
        time_unit =  timeX[-1:].lower()
        if time_unit == "s":
            return time_value, "secs "
        if time_unit == "m":
            return time_value * 60, "mins "
        if time_unit == "h":
            return time_value * 60*60, "hours"
        if time_unit == "d":
            return time_value * 60*60*24, "days "
        if time_unit == "w":
            return time_value * 60*60*24*7, "weeks"
        raise Exception()
    except Exception as e:
        logging.error (f"ERROR:  Could not convert time value <{timeX}> - Aborting")
        logging.error (e)
        sys.exit(1)


def split_user_host(user_host):
    """ Handle variations in passed-in user_host and return separate host and user_host values.
    """
    host = user_host
    if host != "local":
        if "@" in host:
            host = host.split("@")[1]
        else:
            logging.error(f"ERROR:  Expecting <user@host> format, but found <{user_host}> - Aborting.")
            sys.exit(1)
    return user_host, host


def cmd_check(cmd, user_host, return_type, check_line_text=None, expected_text=None, not_text=None):
    """  Runs the cmd and operates on the response based on return_type.
    return_types:
        check_string        Returns True if expected_text occures in response of the cmd, plus the full full subprocess run structure
            check_line_text     If provided, only the first line containing this text is checked
            expected_text       Text that must be found
            not_text            Text that must NOT be found
        cmdrun              Returns True if the cmd return code was 0, plus the full full subprocess run structure
    """

    if user_host != "local":
        cmd = ["ssh", user_host] + cmd

    for nTry in range (getcfg('nRetries')):
        try:
            logging.debug(f"cmd_check subprocess command try {nTry+1}: <{cmd}>")
            # runtry = subprocess.run(cmd, capture_output=True, text=True)  # Py 3.7+
            runtry = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)   #Py3.6 requires old-style params
            # logging.debug(f"cmd_check subprocess response {runtry}>")
        except Exception as e:
            logging.error(f"ERROR:  subprocess.run of cmd <{cmd}> failed.\n  {e}")
            return False, None

        if return_type == "check_string":
            if check_line_text is None:
                text_to_check = runtry.stdout
            else:
                text_to_check = ""
                for line in runtry.stdout.split("\n"):
                    if check_line_text in line:
                        text_to_check = line
                        break
                
            if expected_text in text_to_check:
                if not_text is not None:
                    if not_text not in text_to_check:
                        return True, runtry
                else:
                    return True, runtry
            else:
                if nTry == getcfg('nRetries')-1:
                    return False, runtry

        elif return_type == "cmdrun":
            if runtry.returncode == 0:
                return True, runtry
            elif nTry == getcfg('nRetries')-1:
                return False, runtry

        else:
            logging.error (f"ERROR:  Invalid return_type <{return_type}> passed to checker - Aborting")
            sys.exit(1)
        time.sleep (convert_time(getcfg('RetryInterval'))[0])


def next_summary_timestring():
    """Calculate timestring of next summary.
    SummaryDays			0 1 2 3 4 5 6	# Days of week.  0 = Sunday
    SummaryTime			9:45		    # 24 hour clock
    NOTE:  May be off by 1 hour over a DTS changes.
    """
    try:
        target_hour   = int(getcfg("SummaryTime","").split(":")[0])
        target_minute = int(getcfg("SummaryTime","").split(":")[1])
        today_day_num = datetime.datetime.today().isoweekday()    # Sunday = 0, Saturday = 6
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        next_summary = now + datetime.timedelta(days=30)
        for daynum in getcfg("SummaryDays","").split():
            offset_num_days = int(daynum) - today_day_num
            if offset_num_days < 0:
                offset_num_days += 7
            plus_day =  now + datetime.timedelta(days=offset_num_days)
            with_time = plus_day.replace(hour=target_hour, minute=target_minute)
            # if with_time < now:
            if with_time < datetime.datetime.now():
                with_time = with_time + datetime.timedelta(days=7)
            if with_time < next_summary:
                next_summary = with_time
        logging.info(f"Next summary:  {next_summary}")
        return next_summary
    except Exception as e:
        logging.error(f"ERROR:  SummaryDays <{getcfg('SummaryDays','')}> or SummaryTime <{getcfg('SummaryTime','')}> settings could not be parsed.  Aborting\n  {e}")
        sys.exit(1)


class notif_handler:

    events = {}
    next_summary = None
    next_renotif = None

    def __init__(self):
        self.next_summary = next_summary_timestring()
        self.next_renotif = datetime.datetime.now()
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
            notif_key   - Corresponds to the monitortype_kay in the config file
            rslt
                RTN_PASS     - Clears any prior logged WARNING / FAIL / CRITICAL events
                RTN_WARNING  - Logged and included in summary, but no notification.
                RTN_FAIL     - Logged & notified
                RTN_CRITICAL - Logged & notified, with periodic renotification
            message     - Message text from the plugin
        """
        if dict["rslt"] == RTN_PASS:
            logging.info(dict["message"])
            if dict["notif_key"] in self.events:
                del self.events[dict["notif_key"]]
        else:
            if dict["rslt"] == RTN_CRITICAL:
                # if there are no active criticals, then set renotif time to now + renotif value
                if self.next_renotif < datetime.datetime.now()  and  not self.are_criticals():
                    self.next_renotif = datetime.datetime.now() + datetime.timedelta(seconds=convert_time(getcfg("CriticalReNotificationInterval"))[0])
                    logging.info(f"Next critical renotification:  {self.next_renotif}")

            if args.once:
                logging.warning(dict["message"])
            else:
                if dict["rslt"] == RTN_FAIL  or  dict["rslt"] == RTN_CRITICAL:
                    if dict["notif_key"] not in self.events:
                        snd_notif (subj=NOTIF_SUBJ, msg=dict["message"], log=True)
                logging.warning(dict["message"])

            self.events[dict["notif_key"]] = {"message": dict["message"], "criticality": dict["rslt"]}

    def summary(self):
        logging.debug ("Entering: notif_handler.summary")
        if (self.next_summary < datetime.datetime.now())  or  args.once:
            sum = ""
            if len(self.events) == 0:
                sum += "  No current events.  All is well."
            else:
                for event in self.events:
                    sum += f"  {self.events[event]['message']}\n"

            if args.once:
                logging.debug(f"lanmonitor status summary\n{sum}")
                return

            snd_email(subj="lanmonitor status summary", body=sum, to=getcfg("EmailTo"), log=True)

            self.next_summary = next_summary_timestring()

    def renotif(self):
        """ Periodically send a consolidated notification with all current critical events
        if renotif time passed then
            if there are active criticals then
                send consolidated renotif message
            else
                set renotif time = now, which allows next critical to be notified immediately
        """
        logging.debug ("Entering: notif_handler.renotif")
        if (self.next_renotif < datetime.datetime.now()):
            logging.debug (f"self.next_renotif:        {self.next_renotif}")
            logging.debug (f"datetime.datetime.now():  {datetime.datetime.now()}")

            if self.are_criticals():
                criticals = ""
                for event in self.events:
                    if self.events[event]["criticality"] == RTN_CRITICAL:
                        criticals += f"  {self.events[event]['message']}\n"
                snd_notif (subj=NOTIF_SUBJ, msg=criticals, log=True)
                self.next_renotif = datetime.datetime.now() + datetime.timedelta(seconds=convert_time(getcfg("CriticalReNotificationInterval"))[0])
                logging.info(f"Next critical renotification:  {self.next_renotif}")
            else:
                self.next_renotif = datetime.datetime.now()
