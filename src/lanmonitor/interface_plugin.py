#!/usr/bin/env python3
"""LAN Monitor plugin - interface_plugin

Each interface is checked with a `ifconfig <interface name>`, checking for 'UP' and 'RUNNING'.

      MonType_Interface		interface_plugin
      Interface_<friendly_name>  <local or user@host>  [CRITICAL]  <check_interval>  <interface name>
      Interface_router_vlan0       local			CRITICAL  1m  vlan0
"""
__version__ = "3.1"

#==========================================================
#
#  Chris Nelson, Copyright 2021-2024
#
# 3.1 230320 - Warning for ssh fail to remote
# 3.0 230301 - Packaged
#
# TODO
#   Check for blank interface in setup
#   
#==========================================================

import datetime
import lanmonitor.globvars as globvars
from lanmonitor.lanmonfuncs import RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL, cmd_check
from cjnfuncs.core import logging

# Configs / Constants


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
            rest_of_line    Remainder of line (plugin specific formatting)
        Returns True if all good, else False
        """

        logging.debug (f"{item['key']} - {__name__}.setup() called:\n  {item}")

        self.key            = item["key"]                           # vvvv These items don't need to be modified
        self.key_padded     = self.key.ljust(globvars.keylen)
        self.tag            = item["tag"]
        self.user_host_port = item["user_host_port"]
        self.host           = item["host"]
        self.host_padded    = self.host.ljust(globvars.hostlen)
        if item["critical"]:
            self.failtype = RTN_CRITICAL
            self.failtext = "CRITICAL"
        else:
            self.failtype = RTN_FAIL
            self.failtext = "FAIL"
        self.next_run       = datetime.datetime.now().replace(microsecond=0)
        self.check_interval = item['check_interval']                # ^^^^ These items don't need to be modified

        self.interface_name = item["rest_of_line"]

        return RTN_PASS


    def eval_status (self):
        """ Check status of this item.
        Returns dictionary with these keys:
            rslt            Integer status:  RTN_PASS, RTN_WARNING, RTN_FAIL, RTN_CRITICAL
            notif_key       Unique handle for tracking active notifications in the notification handler 
            message         String with status and context details
        """

        logging.debug (f"{self.key} - {__name__}.eval_status() called")

        cmd = ["ifconfig", self.interface_name]
        rslt = cmd_check(cmd, user_host_port=self.user_host_port, return_type="cmdrun")
        # logging.debug (f"cmd_check response:  {rslt}")

        if rslt[0] == RTN_WARNING:
            errro_msg = rslt[1].stderr.replace('\n','')
            return {"rslt":RTN_WARNING, "notif_key":self.key, "message":f"  WARNING: {self.key} - {self.host} - {errro_msg}"}

        if rslt[0] == RTN_PASS:
            if "UP" not in rslt[1].stdout:
                return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - INTERFACE <{self.interface_name}> IS DOWN"}
            if "RUNNING" not in rslt[1].stdout:
                return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - INTERFACE <{self.interface_name}> IS NOT RUNNING"}
            return {"rslt":RTN_PASS, "notif_key":self.key, "message":f"{self.key_padded}  OK - {self.host_padded} - Interface <{self.interface_name}> is Up and Running"}
        else:
            return {"rslt":self.failtype, "notif_key":self.key, "message":f"  {self.failtext}: {self.key} - {self.host} - UNABLE TO READ INTERFACE <{self.interface_name}> STATE"}
