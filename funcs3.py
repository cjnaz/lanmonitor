#!/usr/bin/env python3
"""Funcs (gen 3)
A collection of support funcs for simplifying writing basic tool scripts.

Functions:
    setuplogging             - Set up default logger
    funcs3_min_version_check - Checker for funcs3 module min version
    loadconfig, JAM, getcfg  - Config file handlers
    requestlock, releaselock - Cross-tool/process safety handshake
    snd_notif, snd_email     - Send text message and email messages

    Import this module from the main script as follows:
        from funcs3 import *

Globals:
    cfg - Dictionary that contains the info read from the config file
    progdir - A string var that contains the full path to the main
        program directory.  Useful for file IO when running the script
        from a different pwd, such as when running from cron.
"""

funcs3_version = "V0.6 210427"

#==========================================================
#
#  Chris Nelson, 2018-2020
#
# V0.6 210427  loadconfig returns True when cfg has been (re)loaded.  loadconfig support import, flush and booleans.
# V0.5 201203  Passing None to setuplogging logfile directs output to stdout.  Added funcs3_min_version_check().
# V0.4 201028  Reworked loadconfig & JAM with re to support ':' and '=' delimiters.
#   loadconfig may be re-called and will re-load if the config file mod time has changed.
#   Added '/' to progdir.  Requires Python3.
# V0.3 200426  Updated for Python 3. Python 2 unsupported.  Using tempfile module.
# V0.2 190319  Added email port selection and SSL/TLS support
# V0.1 180520  New
#
# Changes pending
#   
#==========================================================

import sys
import time
import os.path
import io
import smtplib
from email.mime.text import MIMEText
import logging
import tempfile
import re
import __main__

# Project globals
cfg = {}
PROGDIR = os.path.dirname(os.path.realpath(__main__.__file__)) + "/"
progdir = PROGDIR           # Backward compatibility
config_timestamp = 0


# Module exceptions
class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class ConfigError(Error):
    """Exceptions raised for config file function errors.
    Attributes:
        message -- error message including item in error
    Format:
        ConfigError:  <function> - <message>.
    """
    def __init__(self, message):
        self.message = message

class SndEmailError(Error):
    """Exceptions raised for snd_email and snd_notif errors.
    Attributes:
        message -- error message including item in error
    Format:
        SndEmailError:  <function> - <message>.
    """
    def __init__(self, message):
        self.message = message


# ***** Logging setup *****
def setuplogging (logfile= 'log.txt'):
    """Set up logging.

    Param:
    logfile -- 
        The default log file is <main file path>/log.txt.
        Absolute or relative path (from the main program directory) may
        be specified.
        Passing None causes output to bge sent to stdout.
    """
    if logfile == None:
        logging.basicConfig(format='%(message)s')
    else:
        if os.path.isabs(logfile):  logpath = logfile
        else:                       logpath = PROGDIR + logfile
        logging.basicConfig(filename=logpath, format='%(asctime)s/%(module)s/%(funcName)s/%(levelname)s:  %(message)s')


# ***** funcs3 minimum version checker *****
def funcs3_min_version_check(min_version):
    """Compare current funcs3 module version against passed in minimum expected version.
    Return True if current version >= passed in min version.
    """
    current_version = float(funcs3_version[1:4])
    if current_version >= min_version:
        return True
    else:
        return False


# ***** Config file functions loadconfig, JAM, getcfg *****
cfgline = re.compile(r"([^\s=:]+)[\s=:]+(.+)")

def __loadline__(line):     # Common code for loadconfig and JAM
    # line = line.split("#", maxsplit=1)[0].lstrip().rstrip()
    line = line.split("#", maxsplit=1)[0].strip()
    if len(line) > 0:
        out = cfgline.match(line)
        if out:
            key = out.group(1)
            rol = out.group(2)  # rest of line
            isint = False
            try:
                cfg[key] = int(rol)   # append int to dict
                isint = True
            except:
                pass
            if not isint:
                if rol.lower() == "true":
                    cfg[key] = True
                elif rol.lower() == "false":
                    cfg[key] = False
                else:
                    cfg[key] = rol    # append string to dict

            # except:
            #     if rol.lower() == "true":
            #         cfg[key] = True
            #     elif rol.lower() == "false":
            #         cfg[key] = False
            #     else:
            #         cfg[key] = rol    # append string to dict
            #         # print (rol)
            logging.debug (f"Loaded {key} = <{cfg[key]}>  ({type(cfg[key])})")
        else: logging.warning (f"loadconfig/JAM error on line <{line}>.  Line skipped.")


def loadconfig(cfgfile='config.cfg', cfgloglevel=30, cfg_flush=False, isimport=False):
    """Read config file into dictionary cfg.

    Params:
    cfgfile     -- Default is 'config.cfg' in the program directory
        Absolute path or relative path from the main program directory may
        be specified.
    cfgloglevel -- sets logging level during config file loading. Default is 30:WARNING.
    cfg_flush   -- Purges / flushes the cfg dictionary before forced reloading.
    isimport    -- Internally set True when handling imports.

    Notes:
    Logging module levels: 10:DEBUG, 20:INFO, 30:WARNING, 40:ERROR, 50:CRITICAL
    Optional LoggingLevel in the config file will set the logging level after
    the config has been loaded.  If not specified in the config file, then 
    the logging level is set to 30:WARNING after loading the config file.

    loadconfig may be called periodically by the main script.  loadconfig detects
    if the config file modification time has changed and reloads the file, as needed.

    Returns True if cfg has been (re)loaded, and False if not reloaded, so that the
    caller can do processing only if the cfg is freshly loaded.
    """
    global config_timestamp
    global cfg

    logging.getLogger().setLevel(cfgloglevel)

    if cfg_flush:
        logging.debug("loadconfig:  cfg dictionary flushed")
        cfg = {}
        config_timestamp = 0

    if os.path.isabs(cfgfile):
        config = cfgfile
    else:
        config = PROGDIR + cfgfile

    if not os.path.exists(config):
        _msg = f"loadconfig - Config file <{config}> not found."
        logging.error (f"ConfigError:  {_msg}")
        raise ConfigError (_msg)

    try:
        xx = os.path.getmtime(cfgfile)
        if config_timestamp == xx:
            logging.debug("loadconfig:  reload skipped")
            return False
        config_timestamp = xx

        logging.info (f"Loading {config}")
        with io.open(config, encoding='utf8') as ifile:
            for line in ifile:
                if line.strip().lower().startswith("import"):
                    line = line.split("#", maxsplit=1)[0].strip()
                    target = os.path.expanduser(line.split()[1])
                    if os.path.exists(target):
                        loadconfig(target, cfgloglevel, isimport=True)
                    else:
                        _msg = f"loadconfig:  Could not find and import <{target}>"
                        logging.error (f"ConfigError:  {_msg}")
                        raise ConfigError (_msg)
                else:
                    __loadline__(line)
    except Exception as e:
        # print ("In exception")
        _msg = f"loadconfig - Failed while attempting to open/read config file <{config}>.\n  {e}"
        logging.error (f"ConfigError:  {_msg}")
        raise ConfigError (_msg) from None

    if not isimport:                    # Operations only for a top-level call
        if getcfg("DontEmail", False):
            logging.info ('DontEmail is set - Emails and Notifications will NOT be sent')
        elif getcfg("DontNotif", False):
            logging.info ('DontNotif is set - Notifications will NOT be sent')

        if 'LoggingLevel' in cfg:
            ll = cfg['LoggingLevel']
            logging.info (f"Logging level set to <{ll}>")
            logging.getLogger().setLevel(ll)
        else:  logging.getLogger().setLevel(30)

    return True


def JAM():
    """Jam new values into cfg from the file 'JAM' in the program directory,
    if exists.  This allows for changing config values on a running program.
    Use getcfg or direct references to cfg[] for each access, rather than
    getting a local value, else newly jammed values wont be used.
    After the new values are loaded the JAM file is renamed to JAMed.
    The logging level may be changed by setting/changing LoggingLevel.

    JAM is effectively replaced by loadconfig support for reloading the config
    file when its timestamp changes.
    """
    
    jamfile = PROGDIR + 'JAM'
    try:
        if os.path.exists(jamfile):
            with io.open(jamfile, encoding='utf8') as ifile:
                for line in ifile:
                    __loadline__(line)

            if os.path.exists(PROGDIR + 'JAMed'):
                os.remove(PROGDIR + 'JAMed')
            os.rename (jamfile, PROGDIR + 'JAMed')
    except Exception as e:
        _msg = f"JAM - Failed while attempting to open/read/rename JAM file.\n  {e}"
        logging.error (f"ConfigError:  {_msg}")
        raise ConfigError (_msg) from None

    if 'LoggingLevel' in cfg:
        ll = cfg['LoggingLevel']
        logging.info (f"Logging level set to <{ll}>")
        logging.getLogger().setLevel(ll)
    else:  logging.getLogger().setLevel(30)


def getcfg(param, default=None):
    """Get a param from the cfg dictionary.
    Equivalent to just referencing cfg[], but with handling if the item does
    not exist.
    
    Params:
    param   -- string name of item to be fetched from cfg
    default -- if provided, is returned if the param doesn't exist in cfg.

    raise ConfigError if param does not exist in cfg and no default provided.
    """
    
    try:
        return cfg[param]
    except:
        if default != None:
            return default
    _msg = f"getcfg - Config parameter <{param}> not in cfg and no default."
    logging.error (f"ConfigError:  {_msg}")
    raise ConfigError (_msg)


# ***** Lock file management functions *****
LOCKFILE_DEFAULT = "funcs3_LOCK"
def requestlock(caller, lockfile=LOCKFILE_DEFAULT):
    """Lock file request.
    Param:
    caller   -- Info written to the lock file and displayed in any error messages.
    lockfile -- Various lock files may be used simultaneously.
    """
    lock_file = os.path.join(tempfile.gettempdir(), lockfile)

    for _ in range(5):
        if os.path.exists(lock_file):
            with io.open(lock_file, encoding='utf8') as ifile:
                lockedBy = ifile.read()
                logging.info (f"Lock file already exists.  {lockedBy}  Waiting a sec.")
            time.sleep (1)
        else:  
            with io.open(lock_file, 'w', encoding='utf8') as ofile:
                ofile.write(f"Locked by <{caller}> at {time.asctime(time.localtime())}.")
                logging.debug (f"LOCKed by <{caller}> at {time.asctime(time.localtime())}.")
            return 0
    logging.warning (f"Timed out waiting for lock file <{lock_file}> file to be cleared.  {lockedBy}")
    return -1
        

def releaselock(lockfile=LOCKFILE_DEFAULT):
    """Lock file release.
    Any code can release a lock, even if that code didn't request the lock.
    Only the requester should issue the releaselock.

    Param:
    lockfile -- Remove the specified lock file.
    """
    lock_file = os.path.join(tempfile.gettempdir(), lockfile)
    if os.path.exists(lock_file):
        logging.debug(f"Lock file removed: <{lock_file}>")
        os.remove(lock_file)
        return 0
    else:
        logging.warning(f"Attempted to remove lock file <{lock_file}> but the file does not exist.")
        return -1


#***** Notification and email functions *****
def snd_notif(subj='Notification message', msg='', log=False):
    """Send a text message using the cfg NotifList.

    Params:
    subj -- Subject text string
    msg  -- Message text string
    log  -- If True, elevates log level from DEBUG to WARNING to force logging

    cfg NotifList is required in the config file.
    cfg DontNotif is optional, and if == True no text message is sent. Useful for debug.
    """

    xx = 0
    if getcfg('DontNotif', default=False):
        if log:
            logging.warning (f"Notification not sent <{subj}> <{msg}>")
        else:
            logging.debug (f"Notification not sent <{subj}> <{msg}>")
        return 0

    xx = snd_email (subj=subj, body=msg, to='NotifList')
    if log:
        logging.warning (f"Notification sent <{subj}> <{msg}>")
    else:
        logging.debug (f"Notification sent <{subj}> <{msg}>")
    return xx


def snd_email(subj='', body='', filename='', to='', log=False):
    """Send an email message using email account info from the config file.
    Either body or filename must be passed.  body takes precedence over filename.

    Params:
    subj     -- email subject text
    body     -- is a string message to be sent.
    filename -- is a string full path to the file to be sent.
        Default path is the program directory.
        Absolute and relative paths accepted.
    to       -- to whom to send the message
        to may be a single email address (contains an '@') 
        or it is assumed to be a cfg keyword with a space separated list of email addresses
    log  -- If True, elevates log level from DEBUG to WARNING to force logging of the email subj

    cfg EmailFrom, EmailServer, and EmailServerPort are required in the config file
        EmailServerPort must be one of the following:
            P25:  SMTP to port 25 without any encryption
            P465: SMTP_SSL to port 465
            P587: SMTP to port 587 without any encryption
            P587TLS:  SMTP to port 587 and with TLS encryption
    cfg EmailUser and EmailPass are optional in the config file.
        Needed if the server requires credentials.
    cfg DontEmail is optional, and if == True no email is sent.
        Also blocks snd_notifs.  Useful for debug.
    cfg EmailVerbose = True enables the emailer debug level.
    """

    if getcfg('DontEmail', default=False):
        if log:
            logging.warning (f"Email not sent <{subj}>")
        else:
            logging.debug (f"Email not sent <{subj}>")
        return 0

    if not (body == ''):
        m = body
    elif os.path.exists(filename):
        fp = io.open(filename, encoding='utf8')
        m = fp.read()
        fp.close()
    else:
        _msg = f"snd_email - No <body> and can't find file <{filename}>."
        logging.error (f"SndEmailError:  {_msg}")
        raise SndEmailError (_msg)

    m += f"\n(sent {time.asctime(time.localtime())})"

    if '@' in to:
          To = to.split()           # To must be a list
    else: To = getcfg(to).split()
    if not (len(To) > 0):
        _msg = f"snd_email - 'to' list is invalid: <{to}>."
        logging.error (f"SndEmailError:  {_msg}")
        raise SndEmailError (_msg)

    try:
        msg = MIMEText(m)
        msg['Subject'] = subj
        msg['From'] = getcfg('EmailFrom')
        msg['To'] = ", ".join(To)

        server = getcfg('EmailServer')
        port = getcfg('EmailServerPort')
        if port == "P25":
            s = smtplib.SMTP(server, 25)
        elif port == "P465":
            s = smtplib.SMTP_SSL(server, 465)
        elif port == "P587":
            s = smtplib.SMTP(server, 587)
        elif port == "P587TLS":
            s = smtplib.SMTP(server, 587)
            s.starttls()

        if 'EmailUser' in cfg:
            s.login (getcfg('EmailUser'), getcfg('EmailPass'))
        if getcfg("EmailVerbose", default=False): # == True:
            s.set_debuglevel(1)
        s.sendmail(getcfg('EmailFrom'), To, msg.as_string())
        s.quit()

        if log:
            logging.warning (f"Email sent <{subj}>")
        else:
            logging.debug (f"Email sent <{subj}>")
    except Exception as e:
        logging.warning (f"snd_email:  Send failed for <{subj}>:\n  <{e}>")
        return -1
    return 0


if __name__ == '__main__':

    # setuplogging(logfile= 'testlogfile.txt')
    setuplogging(logfile= None)
    loadconfig (cfgfile='testcfg.cfg', cfgloglevel=10)

    # # Tests for funcs3_min_version_check
    # if not funcs3_min_version_check(2.0):
    #     print(f"ERROR:  funcs3 module must be at least version 2.0.  Found <{funcs3_version}>.")
    # if funcs3_min_version_check(0.5):
    #     print(f"funcs3_min_version_check passes.  Found <{funcs3_version}>.")


    # # Tests for loadconfig, getcfg
    # try:
    #     loadconfig("nosuchfile.txt")
    # except ConfigError as e:
    #     print ("In main...", e)
    # # loadconfig("nosuchfile.txt")      # This one exercises untrapped error caught by Python

    # for key in cfg:
    #     print (f"{key:>20} = {cfg[key]}") #.format(key, cfg[key]))

    # print (f"Testing getcfg - Not in cfg with default: <{getcfg('NotInCfg', 'My Default Value')}>") #.format(getcfg('NotInCfg', 'My Default Value')))
    # try:
    #     getcfg('NotInCfg-NoDef')
    # except ConfigError as e:
    #     print (e)
    # # getcfg('NotInCfg-NoDef')          # This one exercises untrapped error caught by Python


    # # Tests for JAM
    # with io.open("JAM", 'w') as ofile:
    #     ofile.write("JammedInt 1234\n")
    #     ofile.write("JammedStr This is a text string # with a comment on the end\n")
    #     ofile.write("JammedBool false\n")
    #     ofile.write("LoggingLevel 10\n")
    # JAM()
    # print (f"JammedInt  = <{getcfg('JammedInt')}>, {type(getcfg('JammedInt'))}") #.format(getcfg('JammedInt'), type(getcfg('JammedInt'))))
    # print (f"JammedStr  = <{getcfg('JammedStr')}>, {type(getcfg('JammedStr'))}") #.format(getcfg('JammedStr'), type(getcfg('JammedStr'))))
    # print (f"JammedBool = <{getcfg('JammedBool')}>, {type(getcfg('JammedBool'))}") #.format(getcfg('JammedBool'), type(getcfg('JammedBool'))))


    # Tests for sndNotif and snd_email
    # cfg['DontEmail'] = True
    # cfg['DontNotif'] = True
    # snd_email (subj="Test email with body", body="To be, or not to be...", to="EmailTo")
    # snd_email (subj="Test email with body", body="To be, or not to be...", to="xyz@gmail.com")
    # snd_email (subj="Test email with filename JAMed", filename="JAMed", to="EmailTo")
    # snd_email (subj="Test email with filename LICENSE.txt", filename="LICENSE.txt", to="EmailTo", log=True)
    # snd_notif (subj="This is a test subject", msg='This is the message body')
    # snd_notif (subj="This is another test subject", msg='This is another message body', log=True)


    # # Tests for lock files
    # stat = requestlock ("try1")
    # print (f"got back from requestLock.  stat = {stat}") #.format(stat))
    # stat = requestlock ("try2")
    # print (f"got back from 2nd requestLock.  stat = {stat}") #.format(stat))
    # stat = releaselock ()
    # print (f"got back from releaseLock.  stat = {stat}") #.format(stat))
    # stat = releaselock ()
    # print (f"got back from 2nd releaseLock.  stat = {stat}") #.format(stat))