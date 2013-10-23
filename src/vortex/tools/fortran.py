#!/bin/env python
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

#: No automatic export
__all__ = []

from decimal import Decimal
import re
_RE_FLAGS = re.IGNORECASE + re.DOTALL

# Processor
_LETTER             = "[A-Z]"
_DIGIT              = "[0-9]"
_UNDERSCORE         = "[_]"
_SPECIAL_CHARACTERS = "[ =+-*/(),.':!\"%&;<>?$]"
_OTHER_CHARACTERS   = "[^A-Z0-9_ =+-*/(),.':!\"%&;<>?$]"
_GRAPHIC_CHARACTERS = ".|\n"

_ALPHANUMERIC_CHARACTER = "[A-Z0-9_]"
_CHARACTER              =  "[A-Z0-9_ =+-*/(),.':!\"%&;<>?$]"

# Low-lever
_NAME = _LETTER + _ALPHANUMERIC_CHARACTER + '*'

# Operators
_POWER_OP  = "[*][*]"
_MULT_OP   = "[*/]"
_ADD_OP    = "[+-]"
_CONCAT_OP = "[/][/]"
_REL_OP    = "\.EQ\.|\.NE\.|\.LT\.|\.GT\.|\.GE\.|[=][=]|[/][=]|[<]|[<][=]|[>]|[>][=]"
_NOT_OP    = "\.NOT\."
_AND_OP    = "\.AND\."
_OR_OP     = "\.OR\."
_EQUIV_OP  = "\.EQV\.|\.NEQV\."
_INTRINSIC_OPERATOR = '|'.join((_POWER_OP, _MULT_OP, _ADD_OP, _CONCAT_OP, _REL_OP, _NOT_OP, _AND_OP, _OR_OP, _EQUIV_OP))

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
_SIGNIFICAND                  = "(?:" + _DIGIT_STRING + "\." + "(?:" + _DIGIT_STRING +")?" + "|" + "\." + _DIGIT_STRING + ")"
_EXPONENT_LETTER              = "[DE]"
_EXPONENT                     = _SIGNED_DIGIT_STRING
_REAL_LITERAL_CONSTANT        = "(?:" + _SIGNIFICAND + "(?:" + _EXPONENT_LETTER + _EXPONENT + ")?" + "(?:_" + _KIND_PARAM + ")?" + "|" + _DIGIT_STRING + _EXPONENT_LETTER + _EXPONENT + "(?:_" + _KIND_PARAM + ")?" + ")"
_SIGNED_REAL_LITERAL_CONSTANT = _SIGN + "?" + _REAL_LITERAL_CONSTANT

# Complex
_REAL_PART                = "(?:" + _SIGNED_INT_LITERAL_CONSTANT + "|" + _SIGNED_REAL_LITERAL_CONSTANT + ")"
_IMAG_PART                = "(?:" + _SIGNED_INT_LITERAL_CONSTANT + "|" + _SIGNED_REAL_LITERAL_CONSTANT + ")"
_COMPLEX_LITERAL_CONSTANT = "[(]" + _REAL_PART + "," + _IMAG_PART + "[)]"

# Character
_CHAR_LITERAL_CONSTANT = "(?:" + "(?:" + _KIND_PARAM + "_)?" + "'[^']*'" + "|" + "(?:" + _KIND_PARAM + "_)?" + "\"[^\"]*\"" + ")"

# Logical
_LOGICAL_LITERAL_CONSTANT = "(?:" + "\.TRUE\." + "(?:_" + _KIND_PARAM + ")?" + "|" + "\.FALSE\." + "(?:_" + _KIND_PARAM + ")?" + ")"

# Constants
_LITERAL_CONSTANT = "(?:" + _SIGNED_INT_LITERAL_CONSTANT + "|" + _BOZ_LITERAL_CONSTANT + "|" + _SIGNED_REAL_LITERAL_CONSTANT + "|" + _COMPLEX_LITERAL_CONSTANT + "|" + _CHAR_LITERAL_CONSTANT + "|" + _LOGICAL_LITERAL_CONSTANT + ")"


class LiteralParser(object):

    def __init__(self,
        re_flags     = _RE_FLAGS,
        re_integer   = '^' + _SIGNED_INT_LITERAL_CONSTANT + '$',
        re_boz       = '^' + _BOZ_LITERAL_CONSTANT + '$',
        re_real      = '^' + _SIGNED_REAL_LITERAL_CONSTANT + '$',
        re_complex   = '^' + _COMPLEX_LITERAL_CONSTANT + '$',
        re_character = '^' + _CHAR_LITERAL_CONSTANT + '$',
        re_logical   = '^' + _LOGICAL_LITERAL_CONSTANT + '$',
        re_true      = '\.T(?:RUE)?\.',
        re_false     = '\.F(?:ALSE)?\.',
        ):
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
        """Recompile regexps according to internal characters strings by type."""
        self.integer   = re.compile(self._re_integer,   self._re_flags)
        self.boz       = re.compile(self._re_boz,       self._re_flags)
        self.real      = re.compile(self._re_real,      self._re_flags)
        self.complex   = re.compile(self._re_complex,   self._re_flags)
        self.character = re.compile(self._re_character, self._re_flags)
        self.logical   = re.compile(self._re_logical,   self._re_flags)
        self.true      = re.compile(self._re_true,      self._re_flags)
        self.false     = re.compile(self._re_false,     self._re_flags)

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
        if ( self.integer.match(string) ):
            # Removes the kind parameter.
            cleaned_string = re.sub("_"+_KIND_PARAM, "", string, self._re_flags)
            return int(cleaned_string)
        raise ValueError("Literal %s doesn't represent a FORTRAN integer" % string)

    def parse_boz(self, string):
        """If the argument looks like a FORTRAN boz, returns the matching python integer."""
        if ( self.boz.match(string) ):
            if(  string[0]=="B"): return int(string[2:-1],  2)
            elif(string[0]=="O"): return int(string[2:-1],  8)
            elif(string[0]=="Z"): return int(string[2:-1], 16)
        raise ValueError("Literal %s doesn't represent a FORTRAN boz" % string)

    def parse_real(self, string):
        """If the argument looks like a FORTRAN real, returns the matching python float."""
        if ( self.real.match(string) ):
            # Removes the kind parameter.
            string = re.sub("_"+_KIND_PARAM, "", string, self._re_flags)
            # Changes the exponent d to e.
            cleaned_string = re.sub("d|D", "E", string, self._re_flags)
            return Decimal(cleaned_string)
        raise ValueError("Literal %s doesn't represent a FORTRAN real" % string)

    def parse_complex(self, string):
        """If the argument looks like a FORTRAN complex, returns the matching python complex."""
        if ( self.complex.match(string) ):
            # Splits real and imag parts.
            (real_string, imag_string) = string[1:-1].split(',')
            # Parse real part
            if ( self.integer.match(real_string) ):
                real = self.parse_integer(real_string)
            else:
                real = self.parse_real(real_string)
            # Parse imag part
            if ( self.integer.match(imag_string) ):
                imag = self.parse_integer(imag_string)
            else:
                imag = self.parse_real(imag_string)
            return complex(real, imag)
        raise ValueError("Literal %s doesn't represent a FORTRAN complex" % string)

    def parse_character(self, string):
        """If the argument looks like a FORTRAN character, returns the matching python string."""
        if ( self.character.match(string) ):
            # Removes the kind parameter.
            cleaned_string = re.sub("^" + _KIND_PARAM + "_", "", string, self._re_flags)
            return cleaned_string[1:-1]
        raise ValueError("Literal %s doesn't represent a FORTRAN character" % string)

    def parse_logical(self, string):
        """If the argument looks like a FORTRAN logical, returns the matching python boolean."""
        if ( self.logical.match(string) ):
            # Removes the kind parameter.
            cleaned_string = re.sub("_"+_KIND_PARAM, "", string, self._re_flags)
            if ( self.true.match(cleaned_string) ):
                return True
            elif ( self.false.match(cleaned_string) ):
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
        if   self.check_integer(string)  : return self.parse_integer(string)
        elif self.check_boz(string)      : return self.parse_boz(string)
        elif self.check_real(string)     : return self.parse_real(string)
        elif self.check_complex(string)  : return self.parse_complex(string)
        elif self.check_character(string): return self.parse_character(string)
        elif self.check_logical(string)  : return self.parse_logical(string)
        else:
            raise ValueError("Literal %s doesn't represent a FORTRAN literal" % string)

    def encode_integer(self, value):
        """Returns the string form of the integer ``value``."""
        return str(value)

    def encode_boz(self, value):
        """Returns the string form of the BOZ ``value``."""
        return str(value)

    def encode_real(self, value):
        """Returns the string form of the real ``value``."""
        real = '{0:G}'.format(value).replace('E', 'D')
        if '.' not in real:
            real = re.sub('D', '.0D', real)
            if '.' not in real: real += '.'
        return real

    def encode_complex(self, value):
        """Returns the string form of the complex ``value``."""
        return "(%s,%s)" % (self.encode_real(value.real), self.encode_real(value.imag))

    def encode_character(self, value):
        """Returns the string form of the character string ``value``."""
        if ( "'" in value and '"' in value ):
            return '"%s"' % value.replace('"', '""')
        elif ( "'" in value ):
            return '"%s"' % value
        elif ( '"' in value ):
            return "'%s'" % value
        else:
            return "'%s'" % value

    def encode_logical(self, value):
        """Returns the string form of the logical ``value``."""
        if ( value ):
            return '.TRUE.'
        else:
            return '.FALSE.'

    def encode(self, value):
        """Returns the string form of the specified ``value`` according to its type."""
        if   isinstance(value, bool    ): return self.encode_logical(value)
        elif isinstance(value, int     ): return self.encode_integer(value)
        elif isinstance(value, float   ): return self.encode_real(value)
        elif isinstance(value, Decimal ): return self.encode_real(value)
        elif isinstance(value, complex ): return self.encode_complex(value)
        elif isinstance(value, str     ): return self.encode_character(value)
        else:
            raise ValueError("Type %s is cannot be FORTRAN encoded" % type(value))


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

    @property
    def name(self):
        return self._name

    def __repr__(self):
        """Returns a formated id of the current namelist block, including number of items."""
        sr = object.__repr__(self).rstrip('>')
        return '{0:s} | name={1:s} len={2:d}>'.format(sr, self.name, len(self._pool))

    def __str__(self):
        return self.dumps()

    def setvar(self, varname, value):
        """Insert or change a namelist block key."""
        varname = varname.upper()
        if type(value) != list:
            value = [ value ]
        self._pool[varname] = value
        if varname not in self._keys:
            self._keys.append(varname)
        self._mods.add(varname)

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
            return None

    def __getitem__(self, varname):
        return self.getvar(varname)

    def __getattr__(self, varname):
        return self.getvar(varname)

    def delvar(self, varname):
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
        return self.has_key(item)

    def has_key(self, item):
        """
        Returns either ``varname`` value is defined as a namelist key or not.
        Also used as internal for dictionary access.
        """
        return item.upper() in self._pool

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
        """Simulates the dictionary ``get`` mechanism on the internal pool of variables."""
        return self._pool.get(*args)

    def iteritems(self):
        return self._pool.iteritems()

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
        if not literal:
            literal = LiteralParser()
        if item in self._subs:
            if self._subs[item] is None:
                return item
            else:
                return literal.encode(self._subs[item])
        else:
            return literal.encode(item)

    def dumps(self, literal=None):
        """Returns a string of the namelist block, readable by fortran parsers."""
        namout= " &{0:s}\n".format(self.name.upper())
        if not literal:
            literal = LiteralParser()
        for key in self._keys:
            value_strings = [ self.nice(value, literal) for value in self._pool[key] ]
            namout += '   {0:s}={1:s},\n'.format(key, ','.join(value_strings))
        return namout + " /\n"

    def merge(self, delta):
        """Merge the delta provided to the current block."""
        self.update(delta.pool())
        for dk in filter(lambda x: x in self, delta.rmkeys()):
            self.delvar(dk)

class NamelistSet(object):

    def __init__(self, namdict):
        self._namset = namdict

    def __getattr__(self, attr):
        return getattr(self._namset, attr)

    def keys(self):
        return sorted(self._namset.keys())

    def dumps(self):
        return ''.join([ self._namset[x].dumps() for x in self.keys() ])

    def as_dict(self):
        return self._namset

class NamelistParser(object):

    def __init__(self,
        literal  = LiteralParser(),
        macros = None,
        re_flags = None,
        re_clean = "^(\s+|![^\n]*\n)",
        re_block = r'&.*/',
        re_bname = _NAME,
        re_entry = _LETTER + '[ A-Z0-9_,\%\(\):]*' + "(?=\s*=)",
        re_macro = _LETTER + '+',
        re_endol = "(?=\s*(,|/|\n))",
        re_comma = "\s*,"
        ):
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
        """Recompile regexps according to internal characters strings by type."""
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
        return self._literal

    def _namelist_parse(self, source):
        """Parse the all bunch of source as a dict of namelist blocks."""
        namelists = dict()
        while source:
            if self.block.search(source):
                namblock, source = self._namelist_block_parse(source)
                namelists.update({namblock.name : namblock})
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
        source = self._namelist_clean(source[1+len(block_name):])
        namelist = NamelistBlock(block_name)

        current = None
        values = list()

        while source:

            if self.entry.match(source):
                # Got a new entry in the namelist block
                if (current):
                    namelist.update({current : values})
                current = self.entry.match(source).group(0)
                values = list()
                source = self._namelist_clean(source[len(current):])
                # Removes equal
                source = self._namelist_clean(source[1:])
                continue

            elif re.match("^/(end)?", source, self._re_flags):
                if current: namelist.update({current : values})
                source = source[1:]
                if re.match('end', source, self._re_flags): source = source[3:]
                break

            elif re.match('\-+' + self._re_endol, source, self._re_flags):
                item = re.match('\-+' + self._re_endol, source, self._re_flags).group(0)
                namelist.todelete(current)
                current = None
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source): source = self._namelist_clean(self.comma.sub('', source, 1))
                continue

            elif re.match(self._re_macro + self._re_endol, source, self._re_flags):
                item = re.match(self._re_macro + self._re_endol, source, self._re_flags).group(0)
                if item in self.macros:
                    namelist.addmacro(item, None)
                    values.append(item)
                    source = self._namelist_clean(source[len(item):])
                    if self.comma.match(source): source = self._namelist_clean(self.comma.sub('', source, 1))
                    continue

            if re.match(_SIGNED_INT_LITERAL_CONSTANT + self._re_endol, source, self._re_flags):
                item = re.match(_SIGNED_INT_LITERAL_CONSTANT + self._re_endol, source, self._re_flags).group(0)
                values.append(self.literal.parse_integer(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source): source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_BOZ_LITERAL_CONSTANT + self._re_endol, source, self._re_flags):
                item = re.match(_BOZ_LITERAL_CONSTANT + self._re_endol, source, self._re_flags).group(0)
                values.append(self.literal.parse_boz(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source): source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_SIGNED_REAL_LITERAL_CONSTANT + self._re_endol, source, self._re_flags):
                item = re.match(_SIGNED_REAL_LITERAL_CONSTANT + self._re_endol, source, self._re_flags).group(0)
                values.append(self.literal.parse_real(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source): source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_COMPLEX_LITERAL_CONSTANT + self._re_endol, source, self._re_flags):
                item = re.match(_COMPLEX_LITERAL_CONSTANT + self._re_endol, source, self._re_flags).group(0)
                values.append(self.literal.parse_complex(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source): source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_CHAR_LITERAL_CONSTANT + self._re_endol, source, self._re_flags):
                item = re.match(_CHAR_LITERAL_CONSTANT + self._re_endol, source, self._re_flags).group(0)
                values.append(self.literal.parse_character(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source): source = self._namelist_clean(self.comma.sub('', source, 1))

            elif re.match(_LOGICAL_LITERAL_CONSTANT + self._re_endol, source, self._re_flags):
                item = re.match(_LOGICAL_LITERAL_CONSTANT + self._re_endol, source, self._re_flags).group(0)
                values.append(self.literal.parse_logical(item))
                source = self._namelist_clean(source[len(item):])
                if self.comma.match(source): source = self._namelist_clean(self.comma.sub('', source, 1))

            else:
                raise ValueError("Badly formatted FORTRAN namelist: [[%s]]" % source[:32])

        return ( namelist, source )

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

        elif isinstance(obj, file):
            obj.seek(0)
            return self._namelist_parse(obj.read())
        else:
            raise ValueError("Argument %s cannot be parsed." % str(obj))

def namparse(obj):
    """Raw parsing with an default anonymous fortran parser."""
    np = NamelistParser()
    return np.parse(obj)

def _test_literal(lp):
    """
    This function tries to parse most tricky FORTRAN literals.
    It also checks that exceptions are triggered when one needs to.
    """

    def _parse_test(string, parser=None):
        parse = lp.parse
        if parser:
            parse = getattr(lp, 'parse_' + parser)
        try:
            parsed = parse(string)
        except ValueError, e:
            parsed = e
        print "Parsing %10s with %15s: %s" % (string, parse.__name__, parsed)
        return

    _parse_test("1")
    _parse_test("+0")
    _parse_test("-2")
    _parse_test("+46527_8")         # With kind.
    _parse_test("1.", 'integer')    # To avoid confusion with real.
    _parse_test("B'1010'")
    _parse_test("O'76'")
    _parse_test("Z'ABC'")
    _parse_test("B'012'")           # Meaningless digit.
    _parse_test("1.")
    _parse_test("-.1")
    _parse_test("+1E23")
    _parse_test("2.e4_8")           # With kind.
    _parse_test(".45D2")
    _parse_test("10", 'real')       # To avoid confusion with integer
    _parse_test("(1.,0.)")
    _parse_test("(0,1d0)")
    _parse_test("'Foo'")
    _parse_test('"baR"')
    _parse_test('2_"kind"')         # With kind.
    _parse_test("'T_machin'")       # Underscore in the string.
    _parse_test('foo')
    _parse_test(".TRUE.")
    _parse_test(".False.")
    _parse_test(".true._2")         # With kind.
    _parse_test(".truea")

    def _encode_test(string):
        parsed = lp.encode(string)
        print "Encoding %s: %s" % (string, parsed)
        return

    _encode_test(1)
    _encode_test(1243523)
    _encode_test(1.)
    _encode_test(1e-76)
    _encode_test(1e124)
    _encode_test(complex(1,1))
    _encode_test("machin")
    _encode_test("mach'in")
    _encode_test("mach\"in")
    _encode_test("'mach\"in")
    _encode_test(True)

    return

def _test_incore(np):
    from StringIO import StringIO
    ori = StringIO()
    ori.write("""\
! This is a test namelist
 &MyNamelistTest
  title = 'Coordinates/t=10',
  A = 25,30, ! This is a parameter
  x = 300.d0, y=628.318, z=0d0,
  /
&MySecondOne C=.TRUE./
""")
    for namelist in np.parse(ori.getvalue()).values():
        print namelist.dumps()
    return

def _test_namparser(np):
    import sys

    if ( len(sys.argv ) == 1 ):
        _test_incore(np)
    else:
        filename = sys.argv[1]
        testIn = open(filename,"r")
        try:
            namelists = np.parse(testIn)
            for namelist in namelists.values():
                sys.stdout.write( "\nContent of %s\n" % namelist.name )
                for ( name, values ) in namelist.items():
                    sys.stdout.write( "%s: %s\n" % (name, values) )
        finally:
            testIn.close()


if __name__=="__main__":
    _test_literal(LiteralParser())
    _test_namparser(NamelistParser())
