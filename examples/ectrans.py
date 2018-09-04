#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This module is an interface to call ECtrans from Python using Vortex.
"""

from __future__ import print_function, absolute_import, unicode_literals, division


import sys

import footprints
import vortex
from ecmwf.tools.interfaces import ECtrans

logger = footprints.loggers.getLogger(__name__)

if __name__ == '__main__':
    t = vortex.ticket()
    sh = t.sh
    ectrans = ECtrans(sh)
    sys_list_args = sys.argv
    logger.info("You have launched the python ECtrans interface by Vortex.\n\n"
                "The command line of used for this interface has the following format:\n"
                "ectrans.py -attr1=val1[,val2] -attr2\n\n"
                "You have launched the following command line:\n"
                "{}\n\n".format(" ".join(sys_list_args)))
    command_header, args, kwargs, options = ectrans.prepare_arguments(list_args=sys_list_args)
    ectrans(list_args=args, dict_args=kwargs, list_options=options)
