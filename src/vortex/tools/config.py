#!/bin/env python
# -*- coding: utf-8 -*-

r"""
Configuration management through ini files.
"""

__all__ = []

import types
import logging
from ConfigParser import SafeConfigParser

from vortex import sessions


class GenericConfigParser(object):
    """Basic configuration file parser."""

    def __init__(self, inifile=None):
        self.parser = SafeConfigParser()
        if inifile:
            self.setfile(inifile)
        else:
            self.file = None
        self.updates = list()

    def setfile(self, inifile):
        """Read the specified ``inifile`` as new configuration."""
        self.file = inifile
        local = sessions.system()
        if not local.path.exists(self.file):
            glove = sessions.glove()
            self.file = glove.configrc + '/' + local.path.basename(inifile)
            if not local.path.exists(self.file):
                self.file = glove.siteconf + '/' + local.path.basename(inifile)
                if not local.path.exists(self.file):
                    raise Exception(self.file + ' not found')
        self.parser.read(self.file)

    def setall(self, kw):
        """Define in all section the couples of ( key, values ) given as dictionary argument."""
        self.updates.append(kw)
        for section in self.sections():
            for key, value in kw.iteritems():
                self.set(section, key, str(value))

    def save(self):
        """Write the current state of the configuration in the inital file."""
        with open(sefl.file, 'wb') as configfile:
            self.write(configfile)

    @property
    def updated(self):
        """Returns if this configuration has been updated or not."""
        return bool(self.updates)

    def historic(self):
        """Returns a list of the description for each update performed."""
        return self.updates

    def __getattr__(self, attr):
        if attr.startswith('__'):
            raise AttributeError
        return getattr(self.parser, attr)


class DelayedConfigParser(GenericConfigParser):
    """Configuration file parser with possible delayed loading."""


    def __init__(self, inifile=None):
        GenericConfigParser.__init__(self)
        self.__dict__['delay'] = inifile

    def refresh(self):
        """Load the delayed inifile."""
        if self.delay:
            self.setfile(self.delay)
            self.delay = None

    def __getattribute__(self, attr):
        try:
            logging.debug('Getattr %s < %s >', attr, self)
            if attr in filter(lambda x: not x.startswith('_'), dir(SafeConfigParser) + [ 'setall', 'save' ]):
                object.__getattribute__(self, 'refresh')()
        except:
            logging.abort('Trouble getattr %s < %s >', attr, self)
        return object.__getattribute__(self, attr)


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
