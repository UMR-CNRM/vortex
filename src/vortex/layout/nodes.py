#!/bin/env python
# -*- coding:Utf-8 -*-

"""
This modules defines the base nodes of the logical layout
for any :mod:`vortex` experiment.
"""

#: Export real nodes.
__all__ = [ 'Task', 'Family' ]

from vortex.autolog import logdefault as logger
import dataflow


class Node(object):
    """Base class type for any element in the logical layout."""

    def __init__(self, tag, **kw):
        logger.debug('Node initialisation %s', self)
        self._tag = tag
        self.parameters = dict()
        self.target = None
        for kp in [ x for x in kw.keys() if x.startswith('param') ]:
            self.parameters.update(kw[kp])
            del kw[kp]
        self.__dict__.update(kw)

    @property
    def tag(self):
        return self._tag

    def clear_params(self):
        """Clear all existing parameters associated to that node."""
        self.parameters = dict()


class Task(Node):
    """Terminal node including a :class:`Sequence`."""

    def __init__(self, tag, **kw):
        logger.debug('Task init %s', self)
        super(Task, self).__init__(*args, **kw)
        self.sequence = dataflow.Sequence()

    @property
    def realkind(self):
        return 'task'

    def executions(self):
        """Return the number of executable sections in the task's sequence."""
        return len([ x for x in self.sequence if x.kind == dataflow.ixo.EXEC ])

    def retrieve(self):
        """Get all input data."""
        for indata in self.sequence.inputs:
            indata.get()

class Family(Node):
    """Logical group of :class:`Family` or :class:`Task`."""

    def __init__(self, tag, **kw):
        logger.debug('Family init %s', self)
        super(Family, self).__init__(*args, **kw)
        self.contents = list()

    @property
    def realkind(self):
        return 'family'

    def __iter__(self):
        for node in self.contents:
            yield node 

    def __call__(self):
        return self.contents[:]
