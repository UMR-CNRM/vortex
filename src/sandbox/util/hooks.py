# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

#: No automatic export
__all__ = []


def dummy_hook(t, rh):
    """A very simple example of an hook function"""
    print("Dummy hook: The localpath is {}".format(rh.container.localpath()))
