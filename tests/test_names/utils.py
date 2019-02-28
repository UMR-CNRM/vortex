# -*- coding: utf-8 -*-

"""
Basic utilities.
"""

from __future__ import print_function, division, absolute_import, unicode_literals

from collections import OrderedDict
import errno
import os


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
