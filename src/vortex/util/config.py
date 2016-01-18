#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration management through ini files.
"""

__all__ = []


import itertools
import re
from ConfigParser import SafeConfigParser

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions


def load_template(t, tplfile):
    """
    Load a template according to filename provided, either absolute or relative path.
    The first argument ``t`` should be a valid ticket session.
    """
    if t.sh.path.exists(tplfile):
        tplfile = t.sh.path.abspath(tplfile)
    else:
        persofile = t.sh.path.join(t.glove.configrc, 'templates', t.sh.path.basename(tplfile))
        if t.sh.path.exists(persofile):
            tplfile = persofile
        else:
            sitefile = t.sh.path.join(t.glove.siteroot, 'templates', t.sh.path.basename(tplfile))
            if t.sh.path.exists(sitefile):
                tplfile = sitefile
            else:
                raise ValueError('Template file not found: <{}>'.format(tplfile))
    try:
        import string
        with open(tplfile, 'r') as tplfd:
            tpl = string.Template(tplfd.read())
        tpl.srcfile = tplfile
    except Exception as pb:
        logger.error('Could not read template <{!s}>'.format(pb))
        raise
    return tpl


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
        memo[id(self)] = self
        return self

    def as_dump(self):
        """Return a nicely formated class name for dump in footprint."""
        return "{0:s}.{1:s}('{2:s}')".format(self.__module__, self.__class__.__name__, str(self.file))

    def setfile(self, inifile):
        """Read the specified ``inifile`` as new configuration."""
        if self.parser is None:
            self.parser = self.clsparser()
        self.file = None
        local = sessions.system()
        if local.path.exists(inifile):
            self.file = local.path.abspath(inifile)
        else:
            glove = sessions.getglove()
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
                        local.filecocoon(persofile)
                        local.touch(persofile)
                    else:
                        raise ValueError('Configuration file ' + inifile + ' not found')
        if self.file is not None:
            self.parser.read(self.file)

    def setall(self, kw):
        """Define in all sections the couples of ( key, values ) given as dictionary argument."""
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

    def as_dict(self, merged=True):
        if merged:
            dico = dict()
        else:
            dico = dict(defaults = dict(self.defaults()))
        for section in self.sections():
            if merged:
                dico[section] = dict(self.items(section))
            else:
                dico[section] = { k : v for k, v in self.items(section) if k in self.parser._sections[section] }
        return dico

    def __getattr__(self, attr):
        if attr.startswith('__'):
            raise AttributeError
        return getattr(self.parser, attr)

    def footprint_export(self):
        return self.file


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
        except StandardError:
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


class AppConfigStringDecoder(object):
    """Convert a string from a configuration file into a proper Python's object.

    This introduces a lot of flexibility regarding configuration strings since
    it allows to describe lists and dictionaries (with an optional type
    conversion).

    The decoding is done simply by calling the :class:`AppConfigStringDecoder`
    object: ``decoded_string = DecoderObject(config_string)``


    A meta-language is used. Here are some examples:

    * ``toto`` will be decoded as ``toto``
    * ``1,2,3`` will be decoded as a list of strings ``['1', '2', '3']``
    * ``int(1,2,3)`` will decoded as a list of ints ``[1, 2, 3]``
    * ``dict(prod:1 assim:2)`` will be decoded as a dictionary of strings
      ``dict(prod='1', assim='2')``
    * ``geometry(dict(prod:globalsp assim:globalsp2))`` will be decoded as a
      dictionary of geometries
      ``dict(prod=data.geometries.Geometry('globalsp'), assim=data.geometries.Geometry('globalsp2'))``
    * Dictionaries can be combined like in:
      ``dict(production:dict(0:102 12:24) assim:dict(0:6 12:6))``
    * Dictionaries and lists can be mixed:
      ``dict(production:dict(0:0,96,102 12:3,6,24) assim:dict(0:0,3,6 12:0,3,6))``

    Multiple spaces and line breaks are ignored and removed during the decoding.

    The only supported type conversion are: ``int``, ``float`` and ``geometry``.
    """

    def remap_int(self, value):
        try:
            value = int(value)
        except ValueError:
            pass
        return value

    def remap_float(self, value):
        try:
            value = float(value)
        except ValueError:
            pass
        return value

    def remap_geometry(self, value):
        from vortex.data import geometries
        try:
            value = geometries.get(tag=value)
        except ValueError:
            pass
        return value

    def remap_default(self, value):
        return value

    @staticmethod
    def _litteral_cleaner(litteral):
        """Remove unwanted characters from a configuration file's string."""
        cleaned = litteral.lstrip().rstrip()
        # Remove \n and \r
        cleaned = cleaned.replace("\n", ' ').replace("\r", '')
        # Useless spaces after/before parenthesis
        cleaned = re.sub('\(\s*', '(', cleaned)
        cleaned = re.sub('\s*\)', ')', cleaned)
        # Useless spaces around separators
        cleaned = re.sub('\s*:\s*', ':', cleaned)
        cleaned = re.sub('\s*,\s*', ',', cleaned)
        # Duplicated spaces
        cleaned = re.sub('\s+', ' ', cleaned)
        return cleaned

    @staticmethod
    def _sparser(litteral, itemsep=None, keysep=None):
        """Split a string taking into account (nested?) parenthesis."""
        if itemsep is None and keysep is None:
            return [litteral, ]
        if keysep is not None and itemsep is None:
            raise ValueError("keysep can not be set without itemsep")
        # What are the expected separators ?
        markers_it = itertools.cycle([keysep, itemsep ] if keysep else [itemsep, ])
        # Default values
        res_stack = []
        accumstr = ''
        parenthesis = 0
        marker = markers_it.next()
        # Process the string characters one by one and but take parenthesis into
        # account.
        for c in litteral:
            if c == '(':
                parenthesis += 1
            elif c == ')':
                parenthesis -= 1
            if parenthesis < 0:
                raise ValueError("'{}' unbalanced paranthesis". format(litteral))
            if parenthesis == 0 and c == marker:
                res_stack.append(accumstr)
                marker = markers_it.next()
                accumstr = ''
            else:
                accumstr += c
        res_stack.append(accumstr)
        if parenthesis > 0:
            raise ValueError("'{}' unbalanced paranthesis". format(litteral))
        if (keysep is not None) and (res_stack) and (len(res_stack) % 2 != 0):
            raise ValueError("'{}' could not be processed as a dictionnary".format(litteral))
        return res_stack

    def _value_expand(self, value, remap):
        """Recursively expand the configuration file's string."""
        # dictionaries...
        if isinstance(value, basestring) and re.match('^dict\(.*\)$', value):
            value = value[5:-1]
            basis = self._sparser(value, itemsep=' ', keysep=':')
            value = {k: self._value_expand(v, remap)
                     for k, v in zip(basis[0::2], basis[1::2])}
        # lists...
        separeted = self._sparser(value, itemsep=',')
        if isinstance(value, basestring) and len(separeted) > 1:
            value = [self._value_expand(v, remap) for v in separeted]
        # None ?
        if value == 'None':
            value = None
        # Usual values...
        if isinstance(value, basestring):
            value = remap(value)
        return value

    def __call__(self, value):
        """Return the decoded configuration string."""
        if value is not None and isinstance(value, basestring):
            # Check if a type cast is needed, remove spaces, ...
            rmap = 'default'
            value = self._litteral_cleaner(value)
            if (not re.match('^dict', value) and
                    re.match('^\w+\(.*\)$', value)):
                ipos = value.index('(')
                rmap = value[:ipos].lower()
                value = value[ipos + 1:-1]
            remap = getattr(self, 'remap_' + rmap)
            # Process the values recursively
            value = self._value_expand(value, remap)
        return value
