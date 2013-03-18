#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
This modules defines the base nodes of the logical layout
for any :mod:`vortex` experiment.
"""

#: Export real nodes.
__all__ = [ 'Task', 'Family' ]

from vortex.autolog import logdefault as logger
from dataflow import Sequence


class Node(object):
    """Base class type for any element in the logical layout."""

    def __init__(self, *args, **kw):
        logger.debug('Node initialisation %s', self)
        self.parameters = dict()


class Task(Node):
    """Terminal node including a :class:`Sequence`."""
    
    def __init__(self, *args, **kw):
        logger.debug('Task init %s', self)
        super(Task, self).__init__(*args, **kw)
        self.sequence = Sequence()



class Family(Node):
    """Logical group of :class:`Family` or :class:`Task`."""

    def __init__(self, *args, **kw):
        logger.debug('Family init %s', self)
        super(Family, self).__init__(*args, **kw)
        self.contents = list()

    def __iter__(self):
        for node in self.contents:
            yield node 

    def __call__(self):
        return self.contents[:]
