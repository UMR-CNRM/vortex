# -*- coding: utf-8 -*-

"""
Basic utilities and methods useful for test_names.
"""

from __future__ import print_function, division, absolute_import, unicode_literals
import six

from collections import OrderedDict
import contextlib
import errno
import os
import sys


class YamlOrderedDict(OrderedDict):
    """An OrderedDict that can be dumped to a YAML file."""
    pass


def mkdir_p(path):
    """Recursively create directories (like Linux ``mkdir -p``)."""
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


@contextlib.contextmanager
def output_capture(outputs=None):
    """
    A context manager that captures stdout/stderr and store them in **outputs**.
    """
    if outputs is None:
        outputs = six.StringIO()
    out, sys.stdout = sys.stdout, outputs
    err, sys.stderr = sys.stderr, sys.stdout
    try:
        yield outputs
    finally:
        sys.stdout = out
        sys.stderr = err
