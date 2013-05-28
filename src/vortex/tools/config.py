#!/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration management through ini files.
"""

__all__ = []

from ConfigParser import SafeConfigParser

import vortex
from vortex.autolog import logdefault as logger


class GenericConfigParser(object):
    """Basic configuration file parser."""

    def __init__(self, inifile=None, parser=None, mkforce=False, clsparser=SafeConfigParser):
        self.parser = parser
        self.mkforce = mkforce
        self.clsparser = clsparser
        if inifile:
            self.setfile(inifile)
        else:
            self.file = None
        self.updates = list()

    def __deepcopy__(self, memo):
        """Warning: deepcopy of any item of the class is... itself!"""
        memo[self] = self
        return self

    def dumpinfp(self):
        """Return a nicely formated class name for dump in footprint."""
        return "{0:s}.{1:s}('{2:s}')".format(self.__module__, self.__class__.__name__, str(self.file))

    def setfile(self, inifile):
        """Read the specified ``inifile`` as new configuration."""
        if self.parser == None:
            self.parser = self.clsparser()
        self.file = None
        local = vortex.sessions.system()
        if local.path.exists(inifile):
            self.file = local.path.abspath(inifile)
        else:
            glove = vortex.sessions.glove()
            persofile = glove.configrc + '/' + local.path.basename(inifile)
            if local.path.exists(persofile):
                self.file = persofile
            else:
                sitefile = glove.siteconf + '/' + local.path.basename(inifile)
                if local.path.exists(sitefile):
                    self.file = sitefile
                else:
                    if self.mkforce:
                        self.file = persofile
                        local.touch(persofile)
                    else:
                        raise Exception('Configuration file ' + inifile + ' not found')
        if self.file != None:
            self.parser.read(self.file)

    def setall(self, kw):
        """Define in all section the couples of ( key, values ) given as dictionary argument."""
        self.updates.append(kw)
        for section in self.sections():
            for key, value in kw.iteritems():
                self.set(section, key, str(value))

    def save(self):
        """Write the current state of the configuration in the inital file."""
        with open(self.file, 'wb') as configfile:
            self.write(configfile)

    @property
    def updated(self):
        """Return if this configuration has been updated or not."""
        return bool(self.updates)

    def history(self):
        """Return a list of the description for each update performed."""
        return self.updates[:]

    def as_dict(self):
        dico = dict()
        for section in self.sections():
            dico[section] = dict(self.items(section))
        return dico

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
            logger.debug('Getattr %s < %s >', attr, self)
            if attr in filter(lambda x: not x.startswith('_'), dir(SafeConfigParser) + [ 'setall', 'save' ]):
                object.__getattribute__(self, 'refresh')()
        except:
            logger.critical('Trouble getattr %s < %s >', attr, self)
        return object.__getattribute__(self, attr)


class JacketConfigParser(GenericConfigParser):
    """Configuration parser for Jacket files."""

    def get(self, section, option):
        """
        Return for the specified ``option`` in the ``section`` a sequence of values
        build on the basis of a comma separated list.
        """
        s = SafeConfigParser.get(self, section, option)
        l = s.replace(' ', '').split(',')
        if len(l) > 1:
            return l
        else:
            return l[0]
