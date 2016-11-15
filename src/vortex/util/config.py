#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration management through ini files.
"""

from ConfigParser import SafeConfigParser, NoOptionError, InterpolationDepthError
import itertools
import re

import footprints

from vortex import sessions

__all__ = []

logger = footprints.loggers.getLogger(__name__)

_RE_AUTO_TPL = re.compile(r'^@([^/]+\.tpl)$')


def load_template(t, tplfile):
    """
    Load a template according to filename provided, either absolute or relative path.
    The first argument ``t`` should be a valid ticket session.
    """
    autofile = _RE_AUTO_TPL.match(tplfile)
    if autofile is None:
        if t.sh.path.exists(tplfile):
            tplfile = t.sh.path.abspath(tplfile)
        else:
            raise ValueError('Template file not found: <{}>'.format(tplfile))
    else:
        autofile = autofile.group(1)
        persofile = t.sh.path.join(t.glove.configrc, 'templates', autofile)
        if t.sh.path.exists(persofile):
            tplfile = persofile
        else:
            sitefile = t.sh.path.join(t.glove.siteroot, 'templates', autofile)
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
        logger.error('Could not read template <%s>', str(pb))
        raise
    return tpl


class GenericReadOnlyConfigParser(object):
    """A Basic ReadOnly configuration file parser.

    It relies on a :class:`ConfigParser.SafeConfigParser` parser (or another class
    that satisfies the interface) to access the configuration data.

    :param str inifile: Path to a configuration file or a configuration file name
    :param ConfigParser.SafeConfigParser parser: an existing configuration parser
        object the will be used to access the configuration
    :param bool mkforce: If the configuration file doesn't exists. Create an empty
        one in ``~/.vortexrc``
    :param type clsparser: The class that will be used to create a parser object
        (if needed)

    :note: Some of the parser's methods are directly accessible because ``__getattr__``
        is implemented. For this ReadOnly class, only methods ``defaults``,
        ``sections``, ``options``, ``items``, ``has_section`` and ``has_option``
        are accessible. The user will refer to the Python's ConfigParser module
        documentation for more details.
    """

    _RE_AUTO_SETFILE = re.compile(r'^@([^/]+\.ini)$')

    def __init__(self, inifile=None, parser=None, mkforce=False, clsparser=SafeConfigParser):
        self.parser = parser
        self.mkforce = mkforce
        self.clsparser = clsparser
        if inifile:
            self.setfile(inifile)
        else:
            self.file = None

    def __deepcopy__(self, memo):
        """Warning: deepcopy of any item of the class is... itself!"""
        memo[id(self)] = self
        return self

    def as_dump(self):
        """Return a nicely formated class name for dump in footprint."""
        return 'file={!s}'.format(self.file)

    def setfile(self, inifile):
        """Read the specified ``inifile`` as new configuration.

        If ``inifile`` is not a valid file path, the configuration file is looked for
        both in ``~/.vortexrc`` and in the ``conf`` directory of the vortex
        installation. If a section/option is  defined in ``~/.vortexrc`` it takes
        precedence over the one defined in ``conf``.

        :example:

        Let's consider the following declaration in ``conf``::

            [mysection]
            var1=Toto
            var2=Titi

        Let's consider the following declaration in ``~/.vortexrc``::

            [mysection]
            var1=Personalised

        A call to ``get('mysection', 'var1')`` will return ``Personalised`` and a
        call to ``get('mysection', 'var2')`` will return ``Titi``.
        """
        if self.parser is None:
            self.parser = self.clsparser()
        self.file = None
        filestack = list()
        local = sessions.system()
        autofile = self._RE_AUTO_SETFILE.match(inifile)
        if not autofile:
            if local.path.exists(inifile):
                filestack.append(local.path.abspath(inifile))
            else:
                raise ValueError('Configuration file ' + inifile + ' not found')
        else:
            autofile = autofile.group(1)
            glove = sessions.getglove()
            sitefile = glove.siteconf + '/' + autofile
            persofile = glove.configrc + '/' + autofile
            if local.path.exists(sitefile):
                filestack.append(sitefile)
            if local.path.exists(persofile):
                filestack.append(persofile)
            if not filestack:
                if self.mkforce:
                    filestack.append(persofile)
                    local.filecocoon(persofile)
                    local.touch(persofile)
                else:
                    raise ValueError('Configuration file ' + inifile + ' not found')
        self.file = ",".join(filestack)
        self.parser.read(filestack)

    def as_dict(self, merged=True):
        """Export the configuration file as a dictionary."""
        if merged:
            dico = dict()
        else:
            dico = dict(defaults = dict(self.defaults()))
        for section in self.sections():
            if merged:
                dico[section] = dict(self.items(section))
            else:
                dico[section] = {k: v for k, v in self.items(section)
                                 if k in self.parser._sections[section]}
        return dico

    def __getattr__(self, attr):
        # Give access to a very limited set of methods
        if attr.startswith('get') or attr in ('defaults', 'sections', 'options', 'items',
                                              'has_section', 'has_option'):
            return getattr(self.parser, attr)
        else:
            raise AttributeError

    def footprint_export(self):
        return self.file


class ExtendedReadOnlyConfigParser(GenericReadOnlyConfigParser):
    """A ReadOnly configuration file parser with a nice inheritance feature.

    Using this readonly configuration parser, a section can inherit from one or
    several other sections. The basic interpolation (with the usual ``%(varname)s``
    syntax) is available.

    It relies on a :class:`ConfigParser.SafeConfigParser` parser (or another class
    that satisfies the interface) to access the configuration data.

    :param str inifile: Path to a configuration file or a configuration file name
    :param ConfigParser.SafeConfigParser parser: an existing configuration parser
        object the will be used to access the configuration
    :param bool mkforce: If the configuration file doesn't exists. Create an empty
        one in ``~/.vortexrc``
    :param type clsparser: The class that will be used to create a parser object
        (if needed)

    :example: Here is an example using the inheritance mechanism. Let's consider
        the following section declaration::

            [newsection:base1:base2]
            var1=...

        ``newsection`` will inherit the variables contained in sections ``base1``
        and ``base2``. In case of a conflict, ``base1`` takes precedence over ``base2``.
    """

    _re_validate = re.compile(r'([\w-]+)[ \t]*:?')
    _max_interpolation_depth = 20

    def _get_section_list(self, zend_section):
        """
        Return the stack of sections that will be used to look for a given
        variable. Somehow, it is close to python's MRO.
        """
        found_sections = []
        if self.parser.has_section(zend_section):
            found_sections.append(zend_section)
        for section in self.parser.sections():
            pieces = re.split(r'[ \t]*:[ \t]*', section)
            if len(pieces) >= 2 and pieces[0] == zend_section:
                found_sections.append(section)
                for inherited in pieces[1:]:
                    found_sections.extend(self._get_section_list(inherited))
                break
        return found_sections

    def _interpolate(self, section, rawval):
        """Performs the basic interpolation."""
        value = rawval
        depth = self._max_interpolation_depth

        def _interpolation_replace(match):
            s = match.group(1)
            return self.get(section, self.parser.optionxform(s), raw=False)

        while depth:  # Loop through this until it's done
            depth -= 1
            if value and self._KEYCRE.match(value):
                value = self._KEYCRE.sub(_interpolation_replace, value)
            else:
                break
        if value and self._KEYCRE.match(value):
            raise InterpolationDepthError(self.options(section), section, rawval)
        return value

    _KEYCRE = re.compile(r"%\(([^)]+)\)s")

    def get(self, section, option, raw=False, myvars=None):
        """Behaves like the GenericConfigParser's ``get`` method."""
        expanded = self._get_section_list(section)
        expanded.reverse()
        acc_result = None
        acc_except = None
        mydefault = self.defaults().get(option, None)
        for isection in [s for s in expanded if s is not None]:
            try:
                tmp_result = self.parser.get(isection, option, raw=True, vars=myvars)
                if tmp_result is not mydefault:
                    acc_result = tmp_result
            except NoOptionError as err:
                acc_except = err
        if acc_result is None and mydefault is not None:
            acc_result = mydefault
        if acc_result is not None:
            if not raw:
                acc_result = self._interpolate(section, acc_result)
            return acc_result
        else:
            raise acc_except

    def sections(self):
        """Behaves like the Python ConfigParser's ``section`` method."""
        seen = set()
        for section_m in [self._re_validate.match(s) for s in self.parser.sections()]:
            if section_m is not None:
                seen.add(section_m.group(1))
        return list(seen)

    def has_section(self, section):
        """Return whether a section exists or not."""
        return section in self.sections()

    def options(self, section):
        """Behaves like the Python ConfigParser's ``options`` method."""
        expanded = self._get_section_list(section)
        if not expanded:
            return self.parser.options(section)  # A realistic exception will be thrown !
        options = set()
        for isection in [s for s in expanded]:
            options.update(set(self.parser.options(isection)))
        return list(options)

    def has_option(self, section, option):
        """Return whether an option exists or not."""
        return option in self.options(section)

    def items(self, section, raw=False, myvars=None):
        """Behaves like the Python ConfigParser's ``items`` method."""
        return [(o, self.get(section, o, raw, myvars)) for o in self.options(section)]

    def __getattr__(self, attr):
        # Give access to a very limited set of methods
        if attr in ('defaults', ):
            return getattr(self.parser, attr)
        else:
            raise AttributeError

    def as_dict(self, merged=True):
        """Export the configuration file as a dictionary."""
        if not merged:
            raise ValueError("merged=False is not allowed with ExtendedReadOnlyConfigParser.")
        return super(ExtendedReadOnlyConfigParser, self).as_dict(merged=True)


class GenericConfigParser(GenericReadOnlyConfigParser):
    """A Basic Read/Write configuration file parser.

    It relies on a :class:`ConfigParser.SafeConfigParser` parser (or another class
    that satisfies the interface) to access the configuration data.

    :param str inifile: Path to a configuration file or a configuration file name
    :param ConfigParser.SafeConfigParser parser: an existing configuration parser
        object the will be used to access the configuration
    :param bool mkforce: If the configuration file doesn't exists. Create an empty
        one in ``~/.vortexrc``
    :param type clsparser: The class that will be used to create a parser object
        (if needed)

    :note: All of the parser's methods are directly accessible because ``__getattr__``
        is implemented. The user will refer to the Python's ConfigParser module
        documentation for more details.
    """

    def __init__(self, inifile=None, parser=None, mkforce=False, clsparser=SafeConfigParser):
        super(GenericConfigParser, self).__init__(inifile, parser, mkforce, clsparser)
        self.updates = list()

    def setall(self, kw):
        """Define in all sections the couples of ( key, values ) given as dictionary argument."""
        self.updates.append(kw)
        for section in self.sections():
            for key, value in kw.iteritems():
                self.set(section, key, str(value))

    def save(self):
        """Write the current state of the configuration in the inital file."""
        with open(self.file.split(",").pop(), 'wb') as configfile:
            self.write(configfile)

    @property
    def updated(self):
        """Return if this configuration has been updated or not."""
        return bool(self.updates)

    def history(self):
        """Return a list of the description for each update performed."""
        return self.updates[:]

    def __getattr__(self, attr):
        # Give access to all of the parser's methods
        if attr.startswith('__'):
            raise AttributeError
        return getattr(self.parser, attr)


class DelayedConfigParser(GenericConfigParser):
    """Configuration file parser with possible delayed loading.

    :param str inifile: Path to a configuration file or a configuration file name

    :note: All of the parser's methods are directly accessible because ``__getattr__``
        is implemented. The user will refer to the Python's ConfigParser module
        documentation for more details.
    """

    def __init__(self, inifile=None):
        GenericConfigParser.__init__(self)
        self.delay = inifile

    def refresh(self):
        """Load the delayed inifile."""
        if self.delay:
            self.setfile(self.delay)
            self.delay = None

    def __getattribute__(self, attr):
        try:
            logger.debug('Getattr %s < %s >', attr, self)
            if attr in filter(lambda x: not x.startswith('_'), dir(SafeConfigParser) + ['setall', 'save']):
                object.__getattribute__(self, 'refresh')()
        except StandardError:
            logger.critical('Trouble getattr %s < %s >', attr, self)
        return object.__getattribute__(self, attr)


class JacketConfigParser(GenericConfigParser):
    """Configuration parser for Jacket files.

    :param str inifile: Path to a configuration file or a configuration file name
    :param ConfigParser.SafeConfigParser parser: an existing configuration parser
        object the will be used to access the configuration
    :param bool mkforce: If the configuration file doesn't exists. Create an empty
        one in ``~/.vortexrc``
    :param type clsparser: The class that will be used to create a parser object
        (if needed)

    :note: All of the parser's methods are directly accessible because ``__getattr__``
        is implemented. The user will refer to the Python's ConfigParser module
        documentation for more details.
    """

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
        cleaned = re.sub(r'\(\s*', '(', cleaned)
        cleaned = re.sub(r'\s*\)', ')', cleaned)
        # Useless spaces around separators
        cleaned = re.sub(r'\s*:\s*', ':', cleaned)
        cleaned = re.sub(r'\s*,\s*', ',', cleaned)
        # Duplicated spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned

    @staticmethod
    def _sparser(litteral, itemsep=None, keysep=None):
        """Split a string taking into account (nested?) parenthesis."""
        if itemsep is None and keysep is None:
            return [litteral, ]
        if keysep is not None and itemsep is None:
            raise ValueError("keysep can not be set without itemsep")
        # What are the expected separators ?
        markers_it = itertools.cycle([keysep, itemsep] if keysep else [itemsep, ])
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
        if accumstr:
            res_stack.append(accumstr)
        if parenthesis > 0:
            raise ValueError("'{}' unbalanced paranthesis". format(litteral))
        if (keysep is not None) and (res_stack) and (len(res_stack) % 2 != 0):
            raise ValueError("'{}' could not be processed as a dictionnary".format(litteral))
        return res_stack

    def _value_expand(self, value, remap):
        """Recursively expand the configuration file's string."""
        # dictionaries...
        if isinstance(value, basestring) and re.match(r'^dict\(.*\)$', value):
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
                    re.match(r'^\w+\(.*\)$', value)):
                ipos = value.index('(')
                rmap = value[:ipos].lower()
                value = value[ipos + 1:-1]
            remap = getattr(self, 'remap_' + rmap)
            # Process the values recursively
            value = self._value_expand(value, remap)
        return value
