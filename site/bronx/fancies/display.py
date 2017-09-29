#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Display tools.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import sys

import footprints.loggers

logger = footprints.loggers.getLogger(__name__)

#: No automatic export
__all__ = []


def printstatus(step, end, refresh_freq=1):
    """
    Print percentage of the loop it is in.

    :param step: the current loop step
    :param end: the final loop step
    :param refresh_freq: the frequency in % at which reprinting status.
    """
    status = step * 100. / end
    if status % refresh_freq == 0:
        sys.stdout.write('{:>{width}}%'.format(int(status), width=3))
        sys.stdout.flush()
        if step < end :
            sys.stdout.write('\b' * 4)
        else:
            sys.stdout.write('\n')
