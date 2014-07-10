#!/usr/bin/env python
# -*- coding:Utf-8 -*-

# author: stephane Mejias
# date: 09/05/2012
# purpose: script sending messages to the syslog system and a local log file

import logging
from logging.handlers import SysLogHandler

# create the logger object
logger = logging.getLogger()

# create the handlers
hand1 = logging.FileHandler('log1.log')
hand2 = SysLogHandler('/dev/log', facility=SysLogHandler.LOG_LOCAL2)

# create the formats
fmt1 = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
fmt2 = logging.Formatter('%(levelname)s %(message)s')

# set the formats of the handlers
hand1.setFormatter(fmt1)
hand2.setFormatter(fmt2)

# add the handlers to the logger
logger.addHandler(hand1)
logger.addHandler(hand2)

# create the message
logmessage = 'testing logger in Python'

# send the message
logger.error(logmessage)

