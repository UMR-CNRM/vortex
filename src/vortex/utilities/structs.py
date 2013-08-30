#!/bin/env python
# -*- coding: utf-8 -*-
r"""
This module defines common base classes for miscellaneous purposes.
"""

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger


_tableroots = dict()

def idtree(tag):
    if tag not in _tableroots:
        _tableroots[tag] = Tree(name=tag)
    return _tableroots[tag]

class Tree(object):
    """A Miscelaneous hierarchical structure which is also able to track an changing active node."""

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
        if node == None:
            node = self.root
        if self.contains(node):
            print ' *[{0}]...'.format(self._root)
            self.rdump(id(node), 1)
        else:
            logger.critical('Object %s does not belong this tree', node)
