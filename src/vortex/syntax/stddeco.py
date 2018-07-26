#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Class decorators used in abstract footprints defined in :mod:`vortex.syntax.stdattr`
in order to alter resource's behaviours to be consistent with the added
attribute.
"""

from __future__ import print_function, absolute_import, unicode_literals, division


def namebuilding_insert(targetkey, valuecb, none_discard=False, setdefault=False):
    """Insert/Overwrite an entry in the dictionary returned by namebuilding_info().

    :param str targetkey: The dictionary's key to alter.
    :param valuecb: The new value for this entry will be returned by the *valuecd*
                    callback function.
    :param bool none_discard: ``None`` values are ignored silently.
    :param bool setdefault: Use ``setdefault`` indtead of the usual ``setitem``
    """

    def _namebuilding_insert_stuff(cls):

        if hasattr(cls, 'namebuilding_info'):
            original_namebuilding_info = cls.namebuilding_info

            def namebuilding_info(self):
                vinfo = original_namebuilding_info(self)
                value = valuecb(self)
                if not none_discard or value is not None:
                    if setdefault:
                        vinfo.setdefault(targetkey, value)
                    else:
                        vinfo[targetkey] = value
                return vinfo

            namebuilding_info.__doc__ = original_namebuilding_info.__doc__
            cls.namebuilding_info = namebuilding_info

        return cls

    return _namebuilding_insert_stuff


def namebuilding_append(targetkey, valuecb, none_discard=False):
    """Append something to an entry of the dictionary returned by namebuilding_info().

    :param str targetkey: The dictionary's key to alter
    :param valuecb: The new value for this entry will be returned by the *valuecd*
                    callback function.
    :param bool none_discard: ``None`` values are ignored silently.
    """

    def _namebuilding_append_stuff(cls):

        if hasattr(cls, 'namebuilding_info'):
            original_namebuilding_info = cls.namebuilding_info

            def namebuilding_info(self):
                vinfo = original_namebuilding_info(self)
                value = valuecb(self)
                if not isinstance(value, list):
                    value = [value, ]
                if none_discard:
                    value = [v for v in value if v is not None]
                if targetkey in vinfo:
                    some_stuff = vinfo[targetkey]
                    if not isinstance(some_stuff, list):
                        some_stuff = [some_stuff, ]
                    some_stuff.extend(value)
                else:
                    some_stuff = value
                vinfo[targetkey] = some_stuff
                return vinfo

            namebuilding_info.__doc__ = original_namebuilding_info.__doc__
            cls.namebuilding_info = namebuilding_info

        return cls

    return _namebuilding_append_stuff


def namebuilding_delete(targetkey):
    """Delete an entry from the dictionary returned by namebuilding_info().

    :param str targetkey: The dictionary's key to alter
    """

    def _namebuilding_delete_stuff(cls):

        if hasattr(cls, 'namebuilding_info'):
            original_namebuilding_info = cls.namebuilding_info

            def namebuilding_info(self):
                vinfo = original_namebuilding_info(self)
                del vinfo[targetkey]
                return vinfo

            namebuilding_info.__doc__ = original_namebuilding_info.__doc__
            cls.namebuilding_info = namebuilding_info

        return cls

    return _namebuilding_delete_stuff


def generic_pathname_insert(targetkey, valuecb, none_discard=False, setdefault=False):
    """Insert/Overwrite an entry in the dictionary returned by generic_pathinfo().

    :param str targetkey: The dictionary's key to alter.
    :param valuecb: The new value for this entry will be returned by the *valuecd*
                    callback function.
    :param bool none_discard: ``None`` values are ignored silently.
    :param bool setdefault: Use ``setdefault`` indtead of the usual ``setitem``
    """

    def _generic_pathinfo_insert_stuff(cls):

        if hasattr(cls, 'generic_pathinfo'):
            original_generic_pathinfo = cls.generic_pathinfo

            def generic_pathinfo(self):
                vinfo = original_generic_pathinfo(self)
                value = valuecb(self)
                if not none_discard or value is not None:
                    if setdefault:
                        vinfo.setdefault(targetkey, value)
                    else:
                        vinfo[targetkey] = value
                return vinfo

            generic_pathinfo.__doc__ = original_generic_pathinfo.__doc__
            cls.generic_pathinfo = generic_pathinfo

        return cls

    return _generic_pathinfo_insert_stuff