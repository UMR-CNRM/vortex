#!/usr/bin/env python
#  -*- coding: utf-8 -*-

"""
This module contains functions for type conversion between FORTRAN
literals, represented as strings, and corresponding python types.

For each literal type (integer, boz, real, complex, character and
logical), there is a corresponding function parse_* and a global
parser, simply called parser, choose automatically the appropriate
literal type. Here is the type conversion table:

  * integer   -> int
  * boz       -> int
  * real      -> float or Decimal
  * complex   -> complex
  * character -> string
  * logical   -> bool

For python data, functions are provided for conversion into FORTRAN
literals through a LiteralParser. Each literal type has its encode_* function and a global
encoder, simply called encode, chooses automatically the appropriate
encoder; python integers will be converted into a FORTRAN integer,
hence the only way to produce a FORTRAN boz is to use encode_boz
directly.

Running the module itself performs a set of tests with, I hope,
every situation that may happen.

Inital author: Joris Picot (2010-12-08 / CERFACS)
"""

from decimal import Decimal
import re
import StringIO

#: No automatic export
__all__ = []

_RE_FLAGS = re.IGNORECASE + re.DOTALL

# Processor
_LETTER             = "[A-Z]"
_DIGIT              = "[0-9]"
_UNDERSCORE         = "[_]"
_LETTER_UNDERSCORE  = "[A-Z_]"
_SPECIAL_CHARACTERS = "[ =+-*/(),.':!\"%&;<>?$]"
_OTHER_CHARACTERS   = "[^A-Z0-9_ =+-*/(),.':!\"%&;<>?$]"
_GRAPHIC_CHARACTERS = ".|\n"

_ALPHANUMERIC_CHARACTER = "[A-Z0-9_]"
_CHARACTER              = "[A-Z0-9_ =+-*/(),.':!\"%&;<>?$]"

# Low-lever
_QUOTE      = "'"
_DQUOTE     = '"'
_STRDELIM_B = "(?P<STRB>[" + _QUOTE + _DQUOTE + "])"
_STRDELIM_E = "(?(STRB)[" + _QUOTE + _DQUOTE + "])"
_NAME       = _LETTER + _ALPHANUMERIC_CHARACTER + '*'
_MACRONAME  = (_STRDELIM_B + r'?\$?' +
               "(?P<NAME>" + _LETTER_UNDERSCORE + _ALPHANUMERIC_CHARACTER + '*' + ")" +
               _STRDELIM_E)

# Operators
_POWER_OP  = "[*][*]"
_MULT_OP   = "[*/]"
_ADD_OP    = "[+-]"
_CONCAT_OP = "[/][/]"
_REL_OP    = r"\.EQ\.|\.NE\.|\.LT\.|\.GT\.|\.GE\.|[=][=]|[/][=]|[<]|[<][=]|[>]|[>][=]"
_NOT_OP    = r"\.NOT\."
_AND_OP    = r"\.AND\."
_OR_OP     = r"\.OR\."
_EQUIV_OP  = r"\.EQV\.|\.NEQV\."
_INTRINSIC_OPERATOR = '|'.join((_POWER_OP, _MULT_OP, _ADD_OP, _CONCAT_OP, _REL_OP, _NOT_OP,
                                _AND_OP, _OR_OP, _EQUIV_OP))

# Labels
_LABEL = _DIGIT + "{1,5}"

# Integers
_SIGN                        = "[+-]"
_DIGIT_STRING                = _DIGIT + "+"
_SIGNED_DIGIT_STRING         = _SIGN + "?" + _DIGIT_STRING
_KIND_PARAM                  = "[A-Z0-9]+"
_INT_LITERAL_CONSTANT        = _DIGIT_STRING + "(?:_" + _KIND_PARAM + ")?"
_SIGNED_INT_LITERAL_CONSTANT = _SIGN + "?" + _INT_LITERAL_CONSTANT

# BOZ
_BINARY_DIGIT         = "[0-1]"
_OCTAL_DIGIT          = "[0-7]"
_HEX_DIGIT            = "[ABCDEF0-9]"
_BINARY_CONSTANT      = "B" + "(?:'|\")" + _BINARY_DIGIT + "+" + "(?:'|\")"
_OCTAL_CONSTANT       = "O" + "(?:'|\")" + _OCTAL_DIGIT + "+" + "(?:'|\")"
_HEX_CONSTANT         = "Z" + "(?:'|\")" + _HEX_DIGIT + "+" + "(?:'|\")"
_BOZ_LITERAL_CONSTANT = "(?:" + _BINARY_CONSTANT + "|" + _OCTAL_CONSTANT + "|" + _HEX_CONSTANT + ")"

# Real
_SIGNIFICAND                  = "(?:" + _DIGIT_STRING + r"\." + "(?:" + _DIGIT_STRING + ")?" + \
                                "|" + r"\." + _DIGIT_STRING + ")"
_EXPONENT_LETTER              = "[DE]"
_EXPONENT                     = _SIGNED_DIGIT_STRING
_REAL_LITERAL_CONSTANT        = "(?:" + _SIGNIFICAND + "(?:" + _EXPONENT_LETTER + _EXPONENT + \
                                ")?" + "(?:_" + _KIND_PARAM + ")?" + "|" + _DIGIT_STRING +    \
                                _EXPONENT_LETTER + _EXPONENT + "(?:_" + _KIND_PARAM + ")?" + ")"
_SIGNED_REAL_LITERAL_CONSTANT = _SIGN + "?" + _REAL_LITERAL_CONSTANT

# Complex
_REAL_PART                = "(?:" + _SIGNED_INT_LITERAL_CONSTANT + "|" + \
                            _SIGNED_REAL_LITERAL_CONSTANT + ")"
_IMAG_PART                = "(?:" + _SIGNED_INT_LITERAL_CONSTANT + "|" + \
                            _SIGNED_REAL_LITERAL_CONSTANT + ")"
_COMPLEX_LITERAL_CONSTANT = "[(]" + _REAL_PART + "," + _IMAG_PART + "[)]"

# Character
_CHAR_LITERAL_CONSTANT = "(?:" + "(?:" + _KIND_PARAM + "_)?" + "'[^']*'" + "|" + "(?:" + \
                         _KIND_PARAM + "_)?" + "\"[^\"]*\"" + ")"

# Logical
_LOGICAL_LITERAL_CONSTANT = "(?:" + r"\.TRUE\." + "(?:_" + _KIND_PARAM + ")?" + "|" + \
                            r"\.FALSE\." + "(?:_" + _KIND_PARAM + ")?" + ")"

# Constants
_LITERAL_CONSTANT = "(?:" + _SIGNED_INT_LITERAL_CONSTANT + "|" + _BOZ_LITERAL_CONSTANT + "|" + \
                    _SIGNED_REAL_LITERAL_CONSTANT + "|" + _COMPLEX_LITERAL_CONSTANT + "|" + \
                    _CHAR_LITERAL_CONSTANT + "|" + _LOGICAL_LITERAL_CONSTANT + ")"

# Sorting
NO_SORTING = 0
FIRST_ORDER_SORTING = 1
SECOND_ORDER_SORTING = 2


class LiteralParser(object):
    """Object in charge of parsing litteral fortran expressions that could be found in a namelist."""
    def __init__(self,
                 re_flags     = _RE_FLAGS,
                 re_integer   = '^' + _SIGNED_INT_LITERAL_CONSTANT + '$',
                 re_boz       = '^' + _BOZ_LITERAL_CONSTANT + '$',
                 re_real      = '^' + _SIGNED_REAL_LITERAL_CONSTANT + '$',
                 re_complex   = '^' + _COMPLEX_LITERAL_CONSTANT + '$',
                 re_character = '^' + _CHAR_LITERAL_CONSTANT + '$',
                 re_logical   = '^' + _LOGICAL_LITERAL_CONSTANT + '$',
                 re_true      = r'\.T(?:RUE)?\.',
                 re_false     = r'\.F(?:ALSE)?\.'):
        self._re_flags     = re_flags
        self._re_integer   = re_integer
        self._re_boz       = re_boz
        self._re_real      = re_real
        self._re_complex   = re_complex
        self._re_character = re_character
        self._re_logical   = re_logical
        self._re_true      = re_true
        self._re_false     = re_false
        self._log = list()
        self.recompile()

    def recompile(self):
        """Recompile regexps according to internal characters strings by literal types."""
        self.integer = re.compile(self._re_integer, self._re_flags)
        self.boz = re.compile(self._re_boz, self._re_flags)
        self.real = re.compile(self._re_real, self._re_flags)
        self.complex = re.compile(self._re_complex, self._re_flags)
        self.character = re.compile(self._re_character, self._re_flags)
        self.logical = re.compile(self._re_logical, self._re_flags)
        self.true = re.compile(self._re_true, self._re_flags)
        self.false = re.compile(self._re_false, self._re_flags)

    # Fast check

    def check_integer(self, string):
        """Returns True if ``string`` could be an integer."""
        return bool(self.integer.match(string))

    def check_boz(self, string):
        """Returns True if ``string`` could be a binary, octal or hexa number."""
        return bool(self.boz.match(string))

    def check_real(self, string):
        """Returns True if ``string`` could be a real number."""
        return bool(self.real.match(string))

    def check_complex(self, string):
        """Returns True if ``string`` could be a complex number."""
        return bool(self.complex.match(string))

    def check_character(self, string):
        """Returns True if ``string`` could be a character string."""
        return bool(self.character.match(string))

    def check_logical(self, string):
        """Returns True if ``string`` could be a logical value."""
        return bool(self.logical.match(string))

    # Atomic type parsing

    def parse_integer(self, string):
        """If the argument looks like a FORTRAN integer, returns the matching python integer."""
        if self.integer.match(string):
            # Removes the kind parameter.
            cleaned_string = re.sub("_" + _KIND_PARAM, "", string, self._re_flags)
            return int(cleaned_string)
        raise ValueError("Literal %s doesn't represent a FORTRAN integer" % string)

    def parse_boz(self, string):
        """If the argument looks like a FORTRAN boz, returns the matching python integer."""
        if self.boz.match(string):
            if string[0] == "B":
                return int(string[2:-1], 2)
            elif string[0] == "O":
                return int(string[2:-1], 8)
            elif string[0] == "Z":
                return int(string[2:-1], 16)
        raise ValueError("Literal %s doesn't represent a FORTRAN boz" % string)

    def parse_real(self, string):
        """If the argument looks like a FORTRAN real, returns the matching python float."""
        if self.real.match(string):
            # Removes the kind parameter.
            string = re.sub("_" + _KIND_PARAM, "", string, self._re_flags)
            # Changes the exponent d to e.
            cleaned_string = re.sub("d|D", "E", string, self._re_flags)
            return Decimal(cleaned_string)
        raise ValueError("Literal %s doesn't represent a FORTRAN real" % string)

    def parse_complex(self, string):
        """If the argument looks like a FORTRAN complex, returns the matching python complex."""
        if self.complex.match(string):
            # Splits real and imag parts.
            (real_string, imag_string) = string[1:-1].split(',')
            # Parse real part
            if self.integer.match(real_string):
                real = self.parse_integer(real_string)
            else:
                real = self.parse_real(real_string)
            # Parse imag part
            if self.integer.match(imag_string):
                imag = self.parse_integer(imag_string)
            else:
                imag = self.parse_real(imag_string)
            return complex(real, imag)
        raise ValueError("Literal %s doesn't represent a FORTRAN complex" % string)

    def parse_character(self, string):
        """If the argument looks like a FORTRAN character, returns the matching python string."""
        if self.character.match(string):
            # Removes the kind parameter.
            cleaned_string = re.sub("^" + _KIND_PARAM + "_", "", string, self._re_flags)
            return cleaned_string[1:-1]
        raise ValueError("Literal %s doesn't represent a FORTRAN character" % string)

    def parse_logical(self, string):
        """If the argument looks like a FORTRAN logical, returns the matching python boolean."""
        if self.logical.match(string):
            # Removes the kind parameter.
            cleaned_string = re.sub("_" + _KIND_PARAM, "", string, self._re_flags)
            if self.true.match(cleaned_string):
                return True
            elif self.false.match(cleaned_string):
                return False
            else:
                raise ValueError("Literal %s is a weirdFORTRAN logical" % cleaned_string)
        raise ValueError("Literal %s doesn't represent a FORTRAN logical" % string)

    def parse(self, string):
        """
        Parse a FORTRAN literal and returns the corresponding python
        type. Resolution order is: integer, boz, real, complex, character
        and logical.
        """
        if self.check_integer(string):
            return self.parse_integer(string)
        elif self.check_boz(string):
            return self.parse_boz(string)
        elif self.check_real(string):
            return self.parse_real(string)
        elif self.check_complex(string):
            return self.parse_complex(string)
        elif self.check_character(string):
            return self.parse_character(string)
        elif self.check_logical(string):
            return self.parse_logical(string)
        else:
            raise ValueError("Literal %s doesn't represent a FORTRAN literal" % string)

    @staticmethod
    def encode_integer(value):
        """Returns the string form of the integer ``value``."""
        return str(value)

    @staticmethod
    def encode_boz(value):
        """Returns the string form of the BOZ ``value``."""
        return str(value)

    @staticmethod
    def encode_real(value):
        """Returns the string form of the real ``value``."""
        if value == 0.:
            real = '0.'
        else:
            real = '{0:.15G}'.format(value).replace('E', 'D')
        if '.' not in real:
            real = re.sub('D', '.0D', real)
            if '.' not in real:
                real += '.'
        return real.rstrip('0')

    def encode_complex(self, value):
        """Returns the string form of the complex ``value``."""
        return "(%s,%s)" % (self.encode_real(value.real), self.encode_real(value.imag))

    @staticmethod
    def encode_character(value):
        """Returns the string form of the character string ``value``."""
        if "'" in value and '"' in value:
            return '"%s"' % value.replace('"', '""')
        elif "'" in value:
            return '"%s"' % value
        elif '"' in value:
            return "'%s'" % value
        else:
            return "'%s'" % value

    @staticmethod
    def encode_logical(value):
        """Returns the string form of the logical ``value``."""
        if value:
            return '.TRUE.'
        else:
            return '.FALSE.'

    def encode(self, value):
        """Returns the string form of the specified ``value`` according to its type."""
        if isinstance(value, bool):
            return self.encode_logical(value)
        elif isinstance(value, int):
            return self.encode_integer(value)
        elif isinstance(value, float):
            return self.encode_real(value)
        elif isinstance(value, Decimal):
            return self.encode_real(value)
        elif isinstance(value, complex):
            return self.encode_complex(value)
        elif isinstance(value, str):
            return self.encode_character(value)
        else:
            raise ValueError("Type %s cannot be FORTRAN encoded" % type(value))


class NamelistBlock(object):
    """
    This class represent a FORTRAN namelist block.
    Values should be an iterable of FORTRAN compatible data.
    """

    def __init__(self, name='UNKNOWN'):
        self.__dict__['_name'] = name
        self.__dict__['_keys'] = list()
        self.__dict__['_pool'] = dict()
        self.__dict__['_mods'] = set()
        self.__dict__['_dels'] = set()
        self.__dict__['_subs'] = dict()
        self.__dict__['_literal'] = None

    @property
    def name(self):
        """The namelist block's name."""
        return self._name

    def __repr__(self):
        """Returns a formated id of the current namelist block, including number of items."""
        parent_repr = super(NamelistBlock, self).__repr__().rstrip('>')
        return '{0:s} | name={1:s} len={2:d}>'.format(parent_repr,
                                                      self.name,
                                                      len(self._pool))

    def __str__(self):
        return self.dumps()

    def setvar(self, varname, value):
        """Insert or change a namelist block key."""
        varname = varname.upper()
        if not isinstance(value, list):
            value = [value, ]
        self._pool[varname] = value
        if varname not in self._keys:
            self._keys.append(varname)
        self._mods.add(varname)
        self._dels.discard(varname)

    def __setitem__(self, varname, value):
        return self.setvar(varname, value)

    def __setattr__(self, varname, value):
        return self.setvar(varname, value)

    def getvar(self, varname):
        """
        Get ``varname`` value (this is not case sensitive).
        Also used as internal for attribute access or dictionary access.
        """
        varname = varname.upper()
        if varname in self._pool:
            if len(self._pool[varname]) == 1:
                return self._pool[varname][0]
            else:
                return self._pool[varname]
        else:
            raise AttributeError("Unknown Namelist variable")

    def __getitem__(self, varname):
        return self.getvar(varname)

    def __getattr__(self, varname):
        return self.getvar(varname)

    def delvar(self, varname):
        """Delete the specified ``varname`` from this block."""
        varname = varname.upper()
        if varname in self._pool:
            del self._pool[varname]
            self._keys.remove(varname)

    def __delitem__(self, varname):
        self.delvar(varname)

    def __delattr__(self, varname):
        self.delvar(varname)

    def __len__(self):
        return len(self._pool)

    def __iter__(self):
        for t in self._keys:
            yield t

    def __contains__(self, item):
        return item.upper() in self._pool

    def has_key(self, item):
        """
        Returns whether ``varname`` value is defined as a namelist key or not.
        Also used as internal for dictionary access.
        """
        return item in self

    def keys(self):
        """Returns the ordered keys of the namelist block."""
        return self._keys[:]

    def __call__(self):
        return self.pool()

    def values(self):
        """Returns the values of the internal pool of variables."""
        return self._pool.values()

    def pool(self):
        """Returns the reference of the internal pool of variables."""
        return self._pool

    def get(self, *args):
        """Proxy to the dictionary ``get`` mechanism on the internal pool of variables."""
        return self._pool.get(*args)

    def iteritems(self):
        """Iterate over the namelist lock's variables."""
        for k in self._keys:
            yield (k, self._pool[k])

    def update(self, dico):
        """Updates the pool of keys, and keeps as much as possible the initial order."""
        for var, value in dico.iteritems():
            self.setvar(var, value)

    def clear(self, rmkeys=None):
        """Remove specified keys or completly clear the namelist block."""
        if rmkeys:
            for k in rmkeys:
                self.delvar(k)
        else:
            self.__dict__['_keys'] = list()
            self.__dict__['_pool'] = dict()

    def todelete(self, varname):
        """Register a key to be deleted."""
        self._dels.add(varname.upper())

    def rmkeys(self):
        """Returns a set of key to be deleted in a merge or dump."""
        return self._dels

    def macros(self):
        """Returns list of used macros in this block."""
        return self._subs.keys()

    def addmacro(self, macro, value=None):
        """Add a new macro to this definition block, and/or set a value."""
        self._subs[macro] = value

    def nice(self, item, literal=None):
        """Nice encoded value of the item, possibly substitue with macros."""
        if literal is None:
            if self._literal is None:
                self._literal = LiteralParser()
            literal = self._literal
        if isinstance(item, basestring):
            itemli = item[:]
            # Ignore quote and double-quote when mathing macro's name
            if ((itemli.startswith("'") and itemli.endswith("'")) or
                    (itemli.startswith('"') and itemli.endswith('"'))):
                itemli = itemli[1:-1]
            # Ignore the dollar sign before a macro name
            if itemli.startswith('$'):
                itemli = itemli[1:]
        else:
            itemli = item
        if itemli in self._subs:
            if self._subs[itemli] is None:
                return item
            else:
                return literal.encode(self._subs[itemli])
        else:
            return literal.encode(item)

    def dumps(self, literal=None, sorting=NO_SORTING):
        """
        Returns a string of the namelist block, readable by fortran parsers.
        Sorting option **sorting**:

            * NO_SORTING;
            * FIRST_ORDER_SORTING => sort keys;
            * SECOND_ORDER_SORTING => sort only within indexes or attributes of the same key.

        """
        namout = " &{0:s}\n".format(self.name.upper())
        if literal is None:
            if self._literal is None:
                self.__dict__['_literal'] = LiteralParser()
            literal = self._literal
        if sorting:
            def str2tup(k):
                k_by_attr = k.split('%')
                split_k = []
                for a in k_by_attr:
                    table = re.match(r'(?P<radic>\w+)\((?P<indexes>.+)\)', a)
                    if table is None:  # scalar
                        split_k.append(a)
                    else:
                        split_k.append(table.group('radic'))
                        strindexes = table.group('indexes')
                        if all([s in strindexes for s in (':', ',')]):
                            raise NotImplementedError("both ':' and ',' in array indexes")
                        elif ':' in strindexes:
                            split_k.extend([int(i) for i in strindexes.split(':')])
                        elif ',' in strindexes:
                            split_k.extend([int(i) for i in strindexes.split(',')])
                        else:
                            split_k.append(int(strindexes))
                return tuple(split_k)
            if sorting == FIRST_ORDER_SORTING:
                keylist = sorted(self._keys, key=str2tup)
            elif sorting == SECOND_ORDER_SORTING:
                tuples = [str2tup(k) for k in self._keys]
                radics = [t[0] for t in tuples]
                radics = sorted(list(set(radics)), key=lambda x: radics.index(x))
                byradics = {r: sorted([{'indexes': tuples[i][1:], 'fullkey': self._keys[i]}
                                       for i in range(len(self._keys)) if tuples[i][0] == r],
                                      key=lambda x: x['indexes'])
                            for r in radics}
                keylist = []
                for r in radics:
                    keylist.extend([b['fullkey'] for b in byradics[r]])
            else:
                raise ValueError('unknown value for **sorting**:' + str(sorting))
        else:
            keylist = self._keys
        for key in keylist:
            value_strings = [self.nice(value, literal) for value in self._pool[key]]
            namout += '   {0:s}={1:s},\n'.format(key, ','.join(value_strings))
        return namout + " /\n"

    def merge(self, delta):
        """Merge the delta provided to the current block."""
        self.update(delta.pool())
        for dkey in [x for x in delta.rmkeys() if x in self]:
            self.delvar(dkey)
            self.todelete(dkey)
        # Preserve macros
        for skey in delta.macros():
            self._subs[skey] = delta._subs[skey]


class NamelistSet(object):
    """A set of namelist blocks (see :class:`NamelistBlock`)."""

    def __init__(self, namdict):
        self._namset = namdict

    def __getattr__(self, attr):
        return getattr(self._namset, attr)

    def keys(self):
        """Return the name of each namelist block stored in this set."""
        return sorted(self._namset.keys())

    def dumps(self, sorting=NO_SORTING):
        """
        Join the fortran-strings dumped by each namelist block.
        Sorting option **sorting**:

            * NO_SORTING;
            * FIRST_ORDER_SORTING => sort all keys within blocks;
            * SECOND_ORDER_SORTING => sort only within indexes or attributes of the same key.

        """
        return ''.join([self._namset[x].dumps(sorting=sorting) for x in self.keys()])

    def as_dict(self):
        """Return the actual namelist set as a dictionary."""
        return dict(self._namset)


class NamelistParser(object):
    """
    Parser that creates a :class:`NamelistSet` object from a namelist file or
    a string.
    """

    def __init__(self,
                 literal  = LiteralParser(),
                 macros = None,
                 re_flags = None,
                 re_clean = r"^(\s+|![^\n]*\n)",
                 re_block = r'&.*/',
                 re_bname = _NAME,
                 re_entry = _LETTER + r'[ A-Z0-9_,\%\(\):]*' + r"(?=\s*=)",
                 re_macro = _MACRONAME,
                 re_endol = r"(?=\s*(,|/|\n))",
                 re_comma = r"\s*,"):
        self._literal = literal
        if macros:
            self.macros = set(macros)
        else:
            self.macros = set()
        if re_flags:
            self._re_flags = re_flags
        else:
            self._re_flags = literal._re_flags
        self._re_clean = re_clean
        self._re_block = re_block
        self._re_bname = re_bname
        self._re_entry = re_entry
        self._re_macro = re_macro
        self._re_endol = re_endol
        self._re_comma = re_comma
        self.recompile()

    def recompile(self):
        """Recompile regexps according to internal characters strings by namelist entity."""
        self.clean = re.compile(self._re_clean, self._re_flags)
        self.block = re.compile(self._re_block, self._re_flags)
        self.bname = re.compile(self._re_bname, self._re_flags)
        self.entry = re.compile(self._re_entry, self._re_flags)
        self.macro = re.compile(self._re_macro, self._re_flags)
        self.endol = re.compile(self._re_endol, self._re_flags)
        self.comma = re.compile(self._re_comma, self._re_flags)

    def addmacro(self, macro):
        """Add an extra macro name (without associated value)."""
        self.macros.add(macro)

    @property
    def literal(self):
        """The literal parser used to process variable values."""
        return self._literal

    def _namelist_parse(self, source):
        """Parse the all bunch of source as a dict of namelist blocks."""
        namelists = dict()
        while source:
            if self.block.search(source):
                namblock, source = self._namelist_block_parse(source)
                namelists.update({namblock.name: namblock})
            else:
                break
        return NamelistSet(namelists)

    def _namelist_clean(self, dirty_source):
        """Removes spaces and comments before data."""
        cleaner_source = re.sub(self._re_clean, '', dirty_source, self._re_flags)
        while cleaner_source != dirty_source:
            dirty_source = cleaner_source
            cleaner_source = re.sub(self._re_clean, '', dirty_source, self._re_flags)
        return cleaner_source

    def _namelist_block_parse(self, source):
        """Parse a block of namelist."""
        source = self._namelist_clean(source)
        block_name = self.bname.match(source[1:]).group(0)
        source = self._namelist_clean(source[1 + len(block_name):])
        namelist = NamelistBlock(block_name)

        current = None
        values = list()

        while source:

            if self.entry.match(source):
                # Got a new entry in the namelist block
                if current:
                    namelist.update({current: values})
                current = self.entry.match(source).group(0).strip()
                values = list()
                source = self._namelist_clean(source[len(current):])
                # Removes equal
                source = self._namelist_clean(source[1:])
                continue

            elif re.match(r"^/(end)?", source, self._re_flags):
                if current:
                    namelist.update({current: values})
                source = source[1:]
                if re.match(r'end', source, self._re_flags):
                    source = source[3:]
                break

            elif re.match(r'\-+' + self._re_endol, source, self._re_flags):
                item = re.match(r'\-+' + self._re_endol,
                                source, self._re_flags).group(0)
                namelist.todelete(current)
                current = None
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source):
                    source = self._namelist_clean(self.comma.sub('', source, 1))
                continue

            elif re.match(self._re_macro + self._re_endol,
                          source, self._re_flags):
                rmatch = re.match(self._re_macro + self._re_endol,
                                  source, self._re_flags)
                if rmatch.group('NAME') in self.macros:
                    namelist.addmacro(rmatch.group('NAME'), None)
                    values.append(rmatch.group(0))
                    source = self._namelist_clean(source[len(rmatch.group(0)):])
                    if self.comma.match(source):
                        source = self._namelist_clean(self.comma.sub('', source, 1))
                    continue

            if re.match(_SIGNED_INT_LITERAL_CONSTANT + self._re_endol,
                        source, self._re_flags):
                item = re.match(_SIGNED_INT_LITERAL_CONSTANT + self._re_endol,
                                source, self._re_flags).group(0)
                values.append(self.literal.parse_integer(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source):
                    source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_BOZ_LITERAL_CONSTANT + self._re_endol,
                          source, self._re_flags):
                item = re.match(_BOZ_LITERAL_CONSTANT + self._re_endol,
                                source, self._re_flags).group(0)
                values.append(self.literal.parse_boz(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source):
                    source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_SIGNED_REAL_LITERAL_CONSTANT + self._re_endol,
                          source, self._re_flags):
                item = re.match(_SIGNED_REAL_LITERAL_CONSTANT + self._re_endol,
                                source, self._re_flags).group(0)
                values.append(self.literal.parse_real(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source):
                    source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_COMPLEX_LITERAL_CONSTANT + self._re_endol,
                          source, self._re_flags):
                item = re.match(_COMPLEX_LITERAL_CONSTANT + self._re_endol,
                                source, self._re_flags).group(0)
                values.append(self.literal.parse_complex(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source):
                    source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_CHAR_LITERAL_CONSTANT + self._re_endol,
                          source, self._re_flags):
                item = re.match(_CHAR_LITERAL_CONSTANT + self._re_endol,
                                source, self._re_flags).group(0)
                values.append(self.literal.parse_character(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source):
                    source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_LOGICAL_LITERAL_CONSTANT + self._re_endol,
                          source, self._re_flags):
                item = re.match(_LOGICAL_LITERAL_CONSTANT + self._re_endol,
                                source, self._re_flags).group(0)
                values.append(self.literal.parse_logical(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source):
                    source = self._namelist_clean(self.comma.sub('', source, 1))

            else:
                raise ValueError("Badly formatted FORTRAN namelist: [[%s]]" % source[:32])

        return (namelist, source)

    def parse(self, obj):
        """
        Parse a string or a file.
        Returns a dict of {namelist block title: namelist block object}.
        """
        if isinstance(obj, str):
            if not self.block.search(obj):
                obj = obj.strip()
                iod = open(obj, 'r')
                obj = iod.read()
                iod.close()
            return self._namelist_parse(obj)

        elif isinstance(obj, (file, StringIO.StringIO)):
            obj.seek(0)
            return self._namelist_parse(obj.read())
        else:
            raise ValueError("Argument %s cannot be parsed." % str(obj))


def namparse(obj, **kwargs):
    """Raw parsing with an default anonymous fortran parser."""
    namp = NamelistParser(**kwargs)
    return namp.parse(obj)
