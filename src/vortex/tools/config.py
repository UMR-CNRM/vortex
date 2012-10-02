#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Configuration management through ini files.
"""

__all__ = []

from ConfigParser import SafeConfigParser

from vortex import sessions

class GenericConfigParser(SafeConfigParser):
    """Basic configuration file parser."""

    def __init__(self, inifile):
        SafeConfigParser.__init__(self)
        glove = sessions.glove()
        local = sessions.system()
        self.file = inifile
        self.updates = list()
        if not local.path.exists(self.file):
            self.file = glove.configrc + '/' + local.path.basename(inifile)
            if not local.path.exists(self.file):
                raise Exception(self.file)
        self.read(self.file)

    def setall(self, kw):
        """Define in all section the couples of ( key, values ) given as dictionary argument."""
        self.updates.append(kw)
        for section in self.sections():
            for key, value in kw.iteritems():
                self.set(section, key, str(value))

    def updated(self):
        """Returns the number of updates that occured in this configuration."""
        return len(self.updates)

    def historic(self):
        """Returns a list of the description for each update performed."""
        return self.updates


class JacketConfigParser(GenericConfigParser):
    """Configuration parser for Jacket files."""

    def get(self, section, option):
        r"""
        Returns for the specified ``option`` in the ``section`` a sequence of values
        build on the basis of a comma separated list.
        """
        s = SafeConfigParser.get(self, section, option)
        l = s.replace(' ', '').split(',')
        if len(l) > 1:
            return l
        else:
            return l[0]
