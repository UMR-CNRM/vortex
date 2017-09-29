#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module is in charge of getting informations on Memory.

Various concrete implementations may be provided since the mechanism to retrieve
information on Memory may not be portable across platforms.
At the present time, the only concrete implementation is
the :class:`LinuxMemInfo`.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six
import abc
import os
import resource

import footprints

logger = footprints.loggers.getLogger(__name__)

DEFAULT_MEM_UNIT = 'MB'


class MemToolUnavailableError(Exception):
    """Raised whenever the necessary commands and/or system files are missing."""
    pass


def mem_in_unit(mem_b, unit):
    """Convert memory in bytes to **unit** (among KB, MB, GB)."""
    unit_power = {'B':0, 'KB':1, 'MB':2, 'GB':3}
    if unit != 'B':
        mem_b = float(mem_b)
    return mem_b / (1024**unit_power[unit])


@six.add_metaclass(abc.ABCMeta)
class MemInfo(object):
    """Provide various informations about Memory (abstract class)."""

    @abc.abstractmethod
    def __init__(self):
        self._system_RAM = None

    def system_RAM(self, unit=DEFAULT_MEM_UNIT):
        """Get total RAM memory available in the system."""
        return mem_in_unit(self._system_RAM, unit)

    @abc.abstractmethod
    def process_maxRSS(self, unit=DEFAULT_MEM_UNIT):
        pass

    @abc.abstractmethod
    def children_maxRSS(self, unit=DEFAULT_MEM_UNIT):
        pass


class LinuxMemInfo(MemInfo):
    """Provide various informations about Memory."""

    def __init__(self):
        self._system_RAM = os.sysconf(b'SC_PAGE_SIZE') * os.sysconf(b'SC_PHYS_PAGES')

    def process_maxRSS(self, unit=DEFAULT_MEM_UNIT):
        """
        Get Maximum Resident Set Size (i.e. maximum memory used at one moment)
        used by of the process.
        """
        maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        return mem_in_unit(maxrss, unit)

    def children_maxRSS(self, unit=DEFAULT_MEM_UNIT):
        """
        Get Maximum Resident Set Size (i.e. maximum memory used at one moment)
        of the process children.
        """
        maxrss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024
        return mem_in_unit(maxrss, unit)
