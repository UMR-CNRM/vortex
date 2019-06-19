#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module is an interface to call ECfs from Python using Vortex.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

import footprints
import vortex
from ecmwf.tools.interfaces import ECfs

logger = footprints.loggers.getLogger(__name__)

if __name__ == '__main__':
    t = vortex.ticket()
    sh = t.sh
    ecfs = ECfs(sh)
    sys_list_args = sys.argv
    logger.info("You have launched the python ECfs interface by Vortex.\n\n"
                "The command line used for this interface has the following format:\n"
                "ecfs.py command -attr1=val1[,val2] -attr2\n\n"
                "You have launched the following command line:\n"
                "{}\n\n".format(" ".join(sys_list_args)))
    command_header, args, kwargs, options = ecfs.prepare_arguments(list_args=sys_list_args)
    ecfs(command=command_header, list_args=args, dict_args=kwargs, list_options=options)
