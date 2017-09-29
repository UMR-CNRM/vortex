#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Miscellaneous I/O tools.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from six import io
import os
import sys
from contextlib import contextmanager
import csv

import footprints.loggers

logger = footprints.loggers.getLogger(__name__)

#: No automatic export
__all__ = []


@contextmanager
def stdout_redirected(to=os.devnull):
    """
    Redirect *sys.stdout* to **to**.

    Usage::

        with stdout_redirected(to=filename):
            print("from Python")
            import os
            os.system("echo non-Python applications are also supported")
    """
    return redirected_stdio(module=sys, stdio='stdout', to=to)


@contextmanager
def stderr_redirected(to=os.devnull):
    """
    Redirect *sys.stderr* to **to**.

    Usage::

        with stdout_redirected(to=filename):
            # there, an error message won't be printed
    """
    return redirected_stdio(module=sys, stdio='stderr', to=to)


def redirected_stdio(module=sys, stdio='stdout', to=os.devnull):
    """
    Redirect **module.stdio** to **to**,
    e.g. (default): *sys.stdout* to *os.devnull*

    Usage::

        with _redirected_stdio(sys, out='stdout', to=filename):
            print("from Python")
            import os
            os.system("echo non-Python applications are also supported")

    Inspired from:
    `<http://stackoverflow.com/questions/5081657/how-do-i-prevent-a-c-shared-library-to-print-on-stdout-in-python>`
    """
    fd = getattr(module, stdio).fileno()

    def _redirect_stdout(to):
        getattr(module, stdio).close()  # + implicit flush()
        os.dup2(to.fileno(), fd)  # fd writes to 'to' file
        setattr(module, stdio, os.fdopen(fd, 'w'))  # Python writes to fd
    with os.fdopen(os.dup(fd), 'w') as old_stdio:
        with open(to, 'w') as f:
            _redirect_stdout(f)
        try:
            yield  # allow code to be run with the redirected stdio
        finally:
            _redirect_stdout(to=old_stdio)  # restore stdio.


def read_dict_in_CSV(filename):
    """
    Reads a .csv file formatted as follow:
    - on first line is described the delimiter
    - on second line is described the 'priority' of the dict.
    - all subsequent lines contain equivalent of a dict, with key/value duets
      separated by the delimiter
    """
    field_dict = []
    with io.open(filename, 'r') as f:
        delimiter = str(f.readline()[0])
        file_priority = str(f.readline()[0:-1])
        field_table = csv.reader(f, delimiter=delimiter)
        for field in field_table:
            # syntax example of field description:
            # name:FIELDNAME;param:value;...
            if len(field) > 1 and field[0][0] != '#':
                fd = {}
                for kv in field:
                    k,v = kv.split(':')
                    try:
                        fd[k] = int(v)
                    except ValueError:
                        fd[k] = v
                field_dict.append(fd)

    return field_dict, file_priority
