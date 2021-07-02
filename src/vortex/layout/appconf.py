# -*- coding: utf-8 -*-

"""
This modules defines objects that any kind of configuration data
for jobs and nodes.
"""

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import re

from bronx.compat.moves import collections_abc
from bronx.syntax.decorators import secure_getattr

from vortex.util.config import AppConfigStringDecoder


class ConfigSet(collections_abc.MutableMapping):
    """Simple struct-like object that acts as a lower case dictionary.

    Two syntax are available to add a new entry in a :class:`ConfigSet` object:

    * ``ConfigSetObject.key = value``
    * ``ConfigSetObject[key] = value``

    Prior to being retrieved, entries ere passed to a
    :class:`vortex.util.config.AppConfigStringDecoder` object. It allows to
    describe complex data types (see the :class:`vortex.util.config.AppConfigStringDecoder`
    class documentation).

    Some extra features are added on top of the
    :class:`vortex.util.config.AppConfigStringDecoder` capabilities:

    * If ``key`` ends with *_map*, ``value`` will be seen as a dictionary
    * If ``key`` contains the words *geometry* or *geometries*, ``value``
      will be converted to a :class:`vortex.data.geometries.Geometry` object
    * If ``key`` ends with *_range*, ``value`` will be passed to the
      :func:`footprints.util.rangex` function

    """

    def __init__(self, *kargs, **kwargs):
        super(ConfigSet, self).__init__(*kargs, **kwargs)
        self.__dict__['_internal'] = dict()
        self.__dict__['_confdecoder'] = AppConfigStringDecoder(substitution_cb=self._internal.get)

    @staticmethod
    def _remap_key(key):
        return key.lower()

    def __iter__(self):
        for k in self._internal.keys():
            yield self._remap_key(k)

    def __getitem__(self, key):
        return self._confdecoder(self._internal[self._remap_key(key)])

    def __setitem__(self, key, value):
        if value is not None and isinstance(value, six.string_types):
            # Support for old style dictionaries (compatibility)
            if (key.endswith('_map') and not re.match(r'^dict\(.*\)$', value) and
                    not re.match(r'^\w+\(dict\(.*\)\)$', value)):
                key = key[:-4]
                if re.match(r'^\w+\(.*\)$', value):
                    value = re.sub(r'^(\w+)\((.*)\)$', r'\1(dict(\2))', value)
                else:
                    value = 'dict(' + value + ')'
            # Support for geometries (compatibility)
            if (('geometry' in key or 'geometries' in key) and
                    (not re.match(r'^geometry\(.*\)$', value, flags=re.IGNORECASE))):
                value = 'geometry(' + value + ')'
            # Support for oldstyle range (compatibility)
            if (key.endswith('_range') and not re.match(r'^rangex\(.*\)$', value) and
                    not re.match(r'^\w+\(rangex\(.*\)\)$', value)):
                key = key[:-6]
                if re.match(r'^\w+\(.*\)$', value):
                    value = re.sub(r'^(\w+)\((.*)\)$', r'\1(rangex(\2))', value)
                else:
                    value = 'rangex(' + value + ')'
        self._internal[self._remap_key(key)] = value

    def __delitem__(self, key):
        del self._internal[self._remap_key(key)]

    def __len__(self):
        return len(self._internal)

    def clear(self):
        self._internal.clear()

    def __contains__(self, key):
        return self._remap_key(key) in self._internal

    @secure_getattr
    def __getattr__(self, key):
        if key in self:
            return self[key]
        else:
            raise AttributeError('No such parameter <' + key + '>')

    def __setattr__(self, attr, value):
        self[attr] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]
        else:
            raise AttributeError('No such parameter <' + key + '>')

    def copy(self):
        newobj = self.__class__()
        newobj.update(**self._internal)
        return newobj
