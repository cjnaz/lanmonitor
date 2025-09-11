#!/usr/bin/env python3
"""
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
"""

__version__ = '4.0'

#==========================================================
#
#  Chris Nelson, Copyright 2021-2025
#
# 4.0 250911 - Updated to lanmonitor V4.0.
# 3.3 240805 - New
#   
#==========================================================

import datetime
import re
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, RTNCODE_CONNECT_ATTEMPT_FAILED, cmd_check
from cjnfuncs.core import logging

# Configs / Constants
FREE_MAP = {'ki':'--kibi', 'mi':'--mebi', 'gi':'--gibi', 'ti':'--tebi'}

class monitor:

    def __init__ (self):
        pass

    def setup (self, item):
        """ Set up instance vars and check item values.
        Passed in item dictionary keys:
            key             Full 'itemtype_tag' key value from config file line
            tag             'tag' portion only from 'itemtype_tag' from config file line
            user_host_port  'local' or 'user@hostname[:port]' from config file line
            host            'local' or 'hostname' from config file line
            critical        True if 'CRITICAL' is in the config file line
            check_interval  Time in seconds between rechecks
            cmd_timeout     Max time in seconds allowed for the command execution in cmd_check()
            rest_of_line    Remainder of line (plugin specific formatting)
        Returns True if all good, else False
        """
        logging.debug (f"{item['key']} - {__name__}.setup() called:\n  {item}")

        self.key            = item['key']                           # vvvv These items don't need to be modified
        self.key_padded     = self.key.ljust(globvars.keylen)
        self.tag            = item['tag']
        self.user_host_port = item['user_host_port']
        self.host           = item['host']
        self.host_padded    = self.host.ljust(globvars.hostlen)
        if item['critical']:
            self.failtype = RTN_CRITICAL
            self.failtext = 'CRITICAL'
        else:
            self.failtype = RTN_FAIL
            self.failtext = 'FAIL'
        self.next_run       = datetime.datetime.now().replace(microsecond=0)
        self.check_interval = item['check_interval']
        self.cmd_timeout    = item['cmd_timeout']                   # ^^^^ These items don't need to be modified


        def parse_limit(limit):
            limit = limit.lower().strip()
            percent_form = re.search(r'^(\d+)%$', limit)
            if percent_form:
                _limit   = int(percent_form.group(1))
                _type    = '%'
            else:
                absolute_form = re.search(r'^(\d+)([kmgt])i$', limit)
                if absolute_form:
                    _limit   = int(absolute_form.group(1))
                    _type = absolute_form.group(2) + 'i'
                else:
                    return -1, -1
            return _limit, _type

        error = False
        self.free_switch = '--kibi'
        limits = item['rest_of_line'].split()

        if len(limits) == 1  or  len(limits) == 2:                          # RAM usage
            self.ram_limit, self.ram_type  = parse_limit(limits[0])
            self.swap_limit = self.swap_type = None
            if self.ram_limit == -1:
                logging.error (f"  ERROR:  <{self.key}> COULD NOT PARSE FREE RAM SETTINGS <{limits[0]}>")
                error = True
            elif self.ram_type != '%':
                self.free_switch = FREE_MAP[self.ram_type]

        if len(limits) == 2:                                                # Swap usage
            self.swap_limit, self.swap_type = parse_limit(limits[1])
            if self.swap_limit == -1:
                logging.error (f"  ERROR:  <{self.key}> COULD NOT PARSE FREE SWAP SETTINGS <{limits[1]}>")
                error = True
            elif self.swap_type != '%':
                self.free_switch = FREE_MAP[self.swap_type]

        if len(limits) < 1  or  len(limits) > 2:
            logging.error (f"  ERROR:  <{self.key}> COULD NOT PARSE FREE RAM AND SWAP SETTINGS <{item['rest_of_line']}>")
            error = True

        if len(limits) == 2  and  self.ram_type != '%'  and  self.swap_type != '%'  and  not error:
            if self.ram_type != self.swap_type:
                logging.error (f"  ERROR:  <{self.key}> ABSOLUTE TYPE LIMITS FOR free_mem AND free_swap MUST USE SAME SUFFIX <{item['rest_of_line']}>")
                error = True

        if error:
            return RTN_FAIL
        else:
            return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        cmd = 'free ' + self.free_switch
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type='cmdrun', cmd_timeout=self.cmd_timeout)
        # $ free -m
        #                total        used        free      shared  buff/cache   available
        # Mem:           47787       21865        2054        3384       27829       25922
        # Swap:           7995        5475        2520
        # logging.debug (f"cmd_check returned:  ({rslt[0]}, {rslt[1]})")
        logging.debug (f"cmd_check returned ({rslt[0]}, (args: '{rslt[1].args}', returncode: '{rslt[1].returncode}', stdout: '{rslt[1].stdout[0:30]}...,' stderr: '{rslt[1].stderr}')")


        if rslt[0] == RTN_WARNING:
            error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':RTN_WARNING, 'notif_key':self.key, 'message':f"  WARNING: {self.key} - {self.host} - {error_msg}"}

        elif rslt[0] == RTN_FAIL:
            if rslt[1].returncode == RTNCODE_CONNECT_ATTEMPT_FAILED:
                error_msg = 'COULD NOT CONNECT TO EXECUTION HOST'
            else:
                error_msg = 'COULD NOT READ free MEMORY STATS FROM TARGET HOST'
            if '__*****__' in rslt[1].stderr:
                error_msg += ' - ' + rslt[1].stderr.split('__*****__')[1]
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {error_msg}"}

        # cmd_check RTN_PASS case
        try:
            lines = rslt[1].stdout.split('\n')
            memline = lines[1].split()
            if self.ram_type == '%':    # Mem Percentage limit
                percent_free_ram = int(memline[6]) / int(memline[1]) * 100
                mem_calc_str = f"Free mem {percent_free_ram:5.1f}%  (minfree {self.ram_limit}%)"
                if percent_free_ram < self.ram_limit:
                    return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {mem_calc_str}"}
            else:                       # Mem Absolute limit
                mem_calc_str = f"Free mem {memline[6]}{self.ram_type}  (minfree {self.ram_limit}{self.ram_type})"
                if int(memline[6]) < self.ram_limit:
                    return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {mem_calc_str}"}

            swapline = lines[2].split()
            swap_calc_str = ''
            if self.swap_type is not None:
                if self.swap_type == '%':   # Swap Percentage limit
                    percent_free_swap = int(swapline[3]) / int(swapline[1]) * 100
                    swap_calc_str = f",  Free swap {percent_free_swap:5.1f}%  (minfree {self.swap_limit}%)"
                    if percent_free_swap < self.swap_limit:
                        return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} - {swap_calc_str}"}
                else:                       # Swap Absolute limit
                    swap_calc_str = f",  Free swap {memline[3]}{self.swap_type}  (minfree {self.swap_limit}{self.swap_type})"
                    if int(swapline[3]) < self.swap_limit:
                        return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: {self.key} - {self.host} -  {swap_calc_str}"}

            return {'rslt':RTN_PASS, 'notif_key':self.key, 'message':f"{self.key_padded}  OK - {self.host_padded} - {mem_calc_str}{swap_calc_str}"}


        except Exception as e:
            logging.warning (f"Could not parse {cmd} response - returned\n  {rslt[1].stdout}\n  {e}")
            return {'rslt':self.failtype, 'notif_key':self.key, 'message':f"  {self.failtext}: COULD NOT PARSE <{cmd}> RESPONSE - returned\n  {rslt[1].stdout}"}