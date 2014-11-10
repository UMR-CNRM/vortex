#!/usr/bin/env python
# -*- coding:Utf-8 -*-

# author: stephane Mejias
# date: 09/05/2012
# purpose: script sending messages to the syslog system and a local log file

import logging
from logging.handlers import SysLogHandler

import platform
if platform.system() == 'Darwin':
    log_address = '/var/run/syslog'
else:
    # should be common tyo all Linux versions
    log_address = '/dev/log'


# create the logger object
logger = logging.getLogger('testlog')

# create the handlers
hand1 = logging.FileHandler('syslog.log')
hand2 = SysLogHandler(log_address, facility=SysLogHandler.LOG_LOCAL3)
hand3 = logging.StreamHandler()

# create the formats
fmt1 = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fmt2 = logging.Formatter('%(levelname)s %(message)s')
fmt3 = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%m-%d %H:%M',
)

# set the formats of the handlers
hand1.setFormatter(fmt1)
hand2.setFormatter(fmt2)
hand3.setFormatter(fmt3)

# add the handlers to the logger
logger.addHandler(hand1)
logger.addHandler(hand2)
logger.addHandler(hand3)

# create the message
logmessage = 'testing logger in Python'

# send the message
logger.setLevel(logging.DEBUG)
logger.warning(logmessage)
logger.debug(logmessage)
