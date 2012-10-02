#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Hierarchical documents to store information.
Derived from :class:`xml.dom.minidom.Document`.
Used to track structured information given by :mod:`~vortex.utilities.observers`.
"""

#: No automatic export
__all__ = []

from datetime import datetime
from xml.dom.minidom import Document

_tracktable = dict()

def tracktable():
    """Get a copy of the table of index."""
    return _tracktable.copy()

def tracker(tag='default', xmlbase=None):
    """Factory to retrieve a information tracker document, according to the ``tag`` provided."""
    if tag not in _tracktable:
        _tracktable[tag] = InformationTracker(tag, xmlbase)
    return _tracktable[tag]


class InformationTracker(Document):

    def __init__(self, tag=None, xmlbase=None):
        Document.__init__(self)
        self.root = self.createElement('tracker')
        self.root.setAttribute('tag', tag)
        self.appendChild(self.root)
        self._current = self.root


    def new_entry(self, kind, name):
        """Insert a top level entry (child of the root node)."""
        entry = self.createElement(str(kind))
        entry.setAttribute('name', name)
        entry.setAttribute('stamp', str(datetime.now()))
        self.root.appendChild(entry)
        return self.root.lastChild

    def add(self, kind, name, base=None, text=None):
        """Add a information node to the ``base`` or current note."""
        if not base:
            base = self.current()
        entry = self.createElement(str(kind))
        entry.setAttribute('name', name)
        if text:
            entry.setAttribute('text', text)
        base.appendChild(entry)
        return base.lastChild

    def current(self, node=None):
        """Return current active node of the document."""
        if node:
            self._current = node
        return self._current

    def alldump(self):
        """Return a string with a complete formatted dump of the document."""
        return self.toprettyxml(indent='    ')
