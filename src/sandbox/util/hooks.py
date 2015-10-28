#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


def dummy_hook(t, rh):
    """A very simple example of an hook function"""
    print "Dummy hook: The localpath is {}".format(rh.container.localpath())
