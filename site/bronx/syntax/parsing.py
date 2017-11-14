#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parsing tools.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import itertools
import re
import six


#: No automatic export
__all__ = []


def str2dict(string, try_convert=None):
    """
    Parse a **string** (of syntax ``key1:value1,key2=value2``) to a dict.

    :param try_convert: try to convert values as type **try_convert**,
                        e.g. try_convert=int
    """
    if ':' not in string and '=' not in string:
        raise SyntaxError("string: '{}' is not convertible to a dict".format(string))
    d = {e[0].strip(): e[1].strip()
         for e in [i.replace('=', ':').split(':', 1) for i in string.split(',')]}
    if try_convert is not None:
        for k, v in d.items():
            try:
                d[k] = try_convert(v)
            except ValueError:
                pass
    return d


class StringDecoderSubstError(RuntimeError):
    """
    Raised whenever an error occurs during variable substitution in the
    :class:`StringDecoder` class.
    """
    def __init__(self, sub, msg):
        msg = 'Unable to substitute "{}". {}.'.format(sub, msg)
        super(StringDecoderSubstError, self).__init__(msg)


class StringDecoderRemapError(RuntimeError):
    """
    Raised whenever an error occurs when re-mapping a configuration line to a
    given Python's type in the :class:`StringDecoder` class.
    """
    def __init__(self, rmap):
        msg = 'Re-mapping to "{}" is not implemented'.format(rmap)
        super(StringDecoderRemapError, self).__init__(msg)


class StringDecoderSyntaxError(ValueError):
    """
    Raised whenever a syntax error is detected in a configuration line
    (when the the :class:`StringDecoder` class is used).
    """
    def __init__(self, value, msg):
        msg = 'Unable to parse "{}". {}.'.format(value, msg)
        super(StringDecoderSyntaxError, self).__init__(msg)


class StringDecoder(object):
    """Convert a string into a proper Python's object.

    This generic decoder only supports list, dictionaries and conversion to basic
    data types. However, it can easily be extended through inheritance.

    The decoding is done simply by calling the :class:`StringDecoder`
    object: ``decoded_string = DecoderObject(config_string)``

    A meta-language is used. Here are some examples:

    * ``toto`` will be decoded as ``toto``
    * ``1,2,3`` will be decoded as a list of strings ``['1', '2', '3']``
    * ``int(1,2,3)`` will decoded as a list of ints ``[1, 2, 3]``
    * ``dict(prod:1 assim:2)`` will be decoded as a dictionary of strings
      ``dict(prod='1', assim='2')``
    * Dictionaries can be combined like in:
      ``dict(production:dict(0:102 12:24) assim:dict(0:6 12:6))``
    * Dictionaries and lists can be mixed:
      ``dict(production:dict(0:0,96,102 12:3,6,24) assim:dict(0:0,3,6 12:0,3,6))``
    * ``dict(production:&(prodconf) assim:&(assimconf))`` will be decoded as a
      dictionary where ``&(prodconf)`` and ``&(assimconf)`` are replaced by
      entries *prodconf* and *assimconf* returned by the **substitution_cb**
      callback (see the explanation below for more details).

    Multiple spaces and line breaks are ignored and removed during the decoding.

    The only supported type conversion are: ``int``, ``float``.

    The class constructor accepts a **substitution_cb** argument (*None* by
    default) that may be a callback function that is used to get a configuration
    line for a given *key*. This is (solely) used by the substitution mechanism.
    If **substitution_cb** is *None*, the substitution mechanism should not be
    used since it would lead to a :class:`StringDecoderSubstError` exception.

    A cache mechanism is used to lesser the cost of string parsing when the
    several identical calls are made. As a consequence, the same object can be
    returned by two subsequent calls. This can be deactivated using the
    **with_cache** constructor's argument.

    The following exception may be raised:

    * :class:`StringDecoderSubstError`: An error occurred during the substitution
      mechanism;
    * :class:`StringDecoderRemapError`: An error occurred during the type conversion;
    * :class:`StringDecoderSyntaxError`: A syntax error was detected (e.g.
      unbalanced parenthesis).

    """

    BUILDERS = ['dict', ]

    def __init__(self, substitution_cb=None, with_cache=True):
        self._subcb = substitution_cb
        # Regexes used in utility methods
        self._builders_re = {k: re.compile(r'^' + k + '\((.*)\)$')
                             for k in self.BUILDERS}
        self._sub1_re = re.compile(r'[&\$]\{(\w+)\}')
        self._sub2_re = re.compile(r'[&\$]\{(\w+)\}$')
        # Results will be cached here:
        self._with_cache = with_cache
        self._cache = dict()

    def _cache_get(self, key):
        return self._cache.get(key)

    def _cache_check(self, key):
        return self._with_cache and key in self._cache

    def _cache_put(self, key, value):
        if self._with_cache:
            self._cache[key] = value

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
        """Split a string taking into account (nested?) parenthesis.

        :param str itemsep: The separator between two items of the list
        :param str keysep: The separator between key and value pairs

        If **keysep** is provided, a dictionary consisting of the key/value
        pairs is returned. Otherwise a list is returned.
        """
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
                raise ValueError("'{}' unbalanced parenthesis". format(litteral))
            if parenthesis == 0 and c == marker:
                res_stack.append(accumstr)
                marker = markers_it.next()
                accumstr = ''
            else:
                accumstr += c
        if accumstr:
            res_stack.append(accumstr)
        if parenthesis > 0:
            raise StringDecoderSyntaxError(litteral, "Unbalanced parenthesis")
        if keysep is not None:
            if res_stack and len(res_stack) % 2 != 0:
                raise StringDecoderSyntaxError(litteral, "It's not a key/value mapping")
            else:
                res_stack = {k: v for k, v in zip(res_stack[0::2], res_stack[1::2])}
        return res_stack

    def _build_dict(self, value, remap, subs):
        """Build a dictionary from the **value** string."""
        return {k: self._value_expand(v, remap, subs)
                for k, v in six.iteritems(self._sparser(value, itemsep=' ', keysep=':'))}

    def _value_expand(self, value, remap, subs):
        """Recursively expand the configuration file's string."""
        if isinstance(value, six.string_types):
            # Substitution
            sub_m = self._sub2_re.match(value)
            if sub_m is not None:
                return subs[sub_m.group(1)]
            # complex builders...
            for b, bre in six.iteritems(self._builders_re):
                value_m = bre.match(value)
                if value_m is not None:
                    return getattr(self, '_build_' + b)(value_m.group(1), remap, subs)
            # lists...
            separeted = self._sparser(value, itemsep=',')
            if len(separeted) > 1:
                return [self._value_expand(v, remap, subs) for v in separeted]
            # None ?
            if value == 'None':
                return None
            if re.match('true$', value, flags=re.IGNORECASE):
                return True
            if re.match('false$', value, flags=re.IGNORECASE):
                return False
            # Usual values...
            return remap(value)
        # Hopeless...
        return value

    def _substitute_lookup(self, value, substitute_set):
        """Lists substitutions, performs several checks and compute the hashkey."""
        # Lists substitution at this level and check for cyclic substitutions
        sublist = list()
        for m in self._sub1_re.finditer(value):
            sub = m.group(1)
            if sub in substitute_set:
                raise StringDecoderSubstError(sub, "Cyclic substitution detected")
            sublist.append(sub)
        # Check the callback
        if sublist and not callable(self._subcb):
            raise StringDecoderSubstError(sublist[0], "The Callback is not callable")
        # Compute the possible substitutions
        u_subs = dict()
        hashstack = list()
        for sub in sublist:
            try:
                l_value = self._subcb(sub)
            except (ValueError, KeyError, RuntimeError, AttributeError) as e:
                raise StringDecoderSubstError(sub, 'The callback raised an exception: {!s}'.format(e))
            if not isinstance(l_value, six.string_types):
                raise StringDecoderSubstError(sub, 'The Callback did not return a string: {!s}'.format(l_value))
            else:
                l_value = self._litteral_cleaner(l_value)
            (l_u_subs, l_hashkey) = self._substitute_lookup(l_value,
                                                            substitute_set | set([sub]))
            u_subs.update(l_u_subs)
            u_subs[sub] = l_value
            hashstack.append(l_hashkey)
        hashstack = tuple(hashstack)
        hashkey = (value, hashstack)
        return (u_subs, hashkey)

    def _substitute_solver(self, value, u_subs):
        """Tries to solve substitutions."""
        # Lists substitution at this level and check for cyclic substitutions
        sublist = [m.group(1) for m in self._sub1_re.finditer(value)]
        # Compute the possible substitutions
        return {s: self._fullprocessing(u_subs[s], u_subs) for s in sublist}

    def _fullprocessing(self, value, u_subs):
        """Return the decoded configuration string."""
        # Check if a type cast is needed, remove spaces, ...
        rmap = 'default'
        rmap_m = re.match(r'^(\w+)\((.*)\)$', value)
        if (rmap_m is not None) and (rmap_m.group(1) not in self.BUILDERS):
            (rmap, value) = rmap_m.groups()
            rmap = rmap.lower()
        if not hasattr(self, 'remap_' + rmap):
            raise StringDecoderRemapError(rmap)
        remap = getattr(self, 'remap_' + rmap)
        # Resolve substitutions first
        subs = self._substitute_solver(value, u_subs)
        # Process the values recursively
        return self._value_expand(value, remap, subs)

    def __call__(self, value):
        """Return the decoded configuration string (possibly from cache)."""
        if value is not None and isinstance(value, basestring):
            clean_value = self._litteral_cleaner(value)
            u_subs, hashkey = self._substitute_lookup(clean_value, set())
            if self._cache_check(hashkey):
                value = self._cache_get(hashkey)
            else:
                value = self._fullprocessing(clean_value, u_subs)
                self._cache_put(hashkey, value)
        return value