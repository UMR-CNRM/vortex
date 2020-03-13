# -*- coding: utf-8 -*-

"""
Basic utilities.
"""

from __future__ import print_function, division, absolute_import, unicode_literals
import six

from collections import OrderedDict
import contextlib
import errno
import os
import sys


class YamlOrderedDict(OrderedDict):
    pass


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


@contextlib.contextmanager
def output_capture(outputs=None):
    if outputs is None:
        outputs = six.StringIO()
    out, sys.stdout = sys.stdout, outputs
    err, sys.stderr = sys.stderr, sys.stdout
    try:
        yield outputs
    finally:
        sys.stdout = out
        sys.stderr = err
