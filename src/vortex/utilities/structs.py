#!/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines common base classes for miscellaneous purposes.
"""

#: No automatic export
__all__ = []

import collections
from datetime import datetime

from vortex.autolog import logdefault as logger

def idtree(tag, _tableroots=dict()):
    if tag not in _tableroots:
        _tableroots[tag] = Tree(name=tag)
    return _tableroots[tag]

class Tree(object):
    """A Miscelaneous hierarchical structure which is also able to track and change active node."""

    def __init__(self, name='all', root=None):
        self.name = name
        self._nodes = dict()
        self._root = root
        self._tokens = []

    @property
    def root(self):
        return self._nodes[self._root]['node']

    def addnode(self, node, parent=None, token=False):
        if parent and not id(parent) in self._nodes:
            logger.critical('Could not add an orphean %s without parent %s', node, parent)
        if parent:
            parent = id(parent)
            self._nodes[parent]['kids'].append(id(node))
        self._nodes[id(node)] = dict(node=node, parent=parent, kids=[])
        if token:
            self._tokens.append(id(node))

    def setroot(self, root):
        self._root = id(root)
        self.addnode(root)

    def isroot(self, node):
        return id(node) == self._root

    def contains(self, node):
        return id(node) in self._nodes

    def node(self, idn):
        if idn in self._nodes:
            return self._nodes[idn]['node']
        else:
            logger.critical('Id %s does not belong this tree', idn)

    def parent(self, node):
        if self.contains(node):
            parent = self._nodes[id(node)]['parent']
            if parent:
                return self.node(parent)
            else:
                return None
        else:
            logger.critical('Object %s does not belong this tree', node)

    def kids(self, node):
        if self.contains(node):
            return [ self.node(x) for x in self._nodes[id(node)]['kids'] ]
        else:
            logger.critical('Object %s does not belong this tree', node)

    def ancestors(self, node):
        if self.contains(node):
            pp = [ node ]
            parent = self.parent(node)
            while parent:
                pp.append(parent)
                parent = self.parent(parent)
            return pp
        else:
            logger.critical('Object %s does not belong this tree', node)

    @property
    def token(self):
        if self._tokens and self._tokens[-1] in self._nodes:
            return self._nodes[self._tokens[-1]]['node']
        else:
            return None

    @property
    def previous(self):
        if len(self._tokens) > 1:
            return self._nodes[self._tokens[-2]]['node']

    def gettoken(self, node):
        if node and self.contains(node):
            self._tokens.append(id(node))

    def rmtoken(self, node):
        if node and self.contains(node):
            idn = id(node)
            self._tokens = filter(lambda x: x != idn, self._tokens)

    def rdump(self, idn, indent):
        print '{0:s}\_[{1}] {2}'.format('   ' * indent, idn, self.node(idn))
        for kid in self._nodes[idn]['kids']:
            self.rdump(kid, indent+1)

    def dump(self, node=None):
        if node is None:
            node = self.root
        if self.contains(node):
            print ' *[{0}]...'.format(self._root)
            self.rdump(id(node), 1)
        else:
            logger.critical('Object %s does not belong this tree', node)

class History(object):
    """Multi-purpose history like object."""

    def __init__(self, tag='void', status=False, histsize=512):
        self._tag = tag
        self._history = collections.deque(maxlen=histsize)
        self._status = status
        self._count = 0

    @property
    def tag(self):
        return self._tag

    @property
    def count(self):
        return self._count

    @property
    def histsize(self):
        return self._history.maxlen

    def resize(self, histsize=None):
        """Resize the internal history log to the specified length."""
        if maxlen:
            self._history = collections.deque(self._history, maxlen=int(histsize))
        return self._history.maxlen

    def __len__(self):
        return len(self._history)

    def __getitem__(self, key):
        return self._history[key]

    def __setitem__(self, key, value):
        logger.warning('Could not set a value to a history item.')

    def __delitem__(self, key, value):
        logger.warning('Could not delete a value of a history item.')

    def __contains__(self, key):
        return key in [ item for stamp, item in self._history ]

    def append(self, item):
        stamp = datetime.now()
        self._count += 1
        self._history.append((self._count, stamp, item))
        return (self._count, stamp)

    def get(self, start=1, end=None):
        if end is None:
            end = self._count
        return [ (c, t, i) for c, t, i in self._history if c>=start and c<=end ]

    def show(self, start=1, end=None):
        for c, t, i in self.get(start, end):
            print str(c).rjust(4), ':', i

    @property
    def last(self):
        return self._history[-1][-1]
