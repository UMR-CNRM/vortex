#!/bin/env python
# -*- coding: utf-8 -*-

from vortex.tools import date

def bestdate(day=None, hh=None):
    """Find out the most accurate ``today`` date."""
    return date.synop()

class Application(object):
    """
    Wrapper for setting up and performing a miscellaneous task.
    The abstract interface is the same as :class:`vortex.layout.nodes.Configuration`.
    """
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def setup(self, t, **kw):
        """Abstract method: defines the interaction with vortex env."""
        pass

    def build(self, t, **kw):
        """Abstract method: fills the configuration contents."""
        pass

    def process(self, t, **kw):
        """Abstract method: perform the taks to do."""
        pass