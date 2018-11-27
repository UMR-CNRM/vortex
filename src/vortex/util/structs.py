#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines common base classes for miscellaneous purposes.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import json

import footprints

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class ShellEncoder(json.JSONEncoder):
    """Encoder for :mod:`json` dumps method."""

    def default(self, obj):
        """Overwrite the default encoding if the current object has a ``export_dict`` method."""
        if hasattr(obj, 'export_dict'):
            return obj.export_dict()
        elif hasattr(obj, 'footprint_export'):
            return obj.footprint_export()
        elif hasattr(obj, '__dict__'):
            return vars(obj)
        return super(ShellEncoder, self).default(obj)


class FootprintCopier(footprints.FootprintBaseMeta):
    """A meta class that copies its content into to the target class.

    The _footprint class variable is dealt with properly (hopefully).
    """

    _footprint = None

    def __new__(cls, n, b, d):

        # Merge the footprints if necessary
        if cls._footprint is not None:
            if '_footprint' in d:
                fplist = cls._footprint if isinstance(cls._footprint, list) else [cls._footprint, ]
                if isinstance(d['_footprint'], list):
                    fplist.extend(d['_footprint'])
                else:
                    fplist.append(d['_footprint'])
                d['_footprint'] = fplist
            else:
                d['_footprint'] = cls._footprint

        # Copy other things
        for var in [v for v in vars(cls) if
                    (not v.startswith('__') or v not in ('_footprint', )) and v not in d]:
            d[var] = getattr(cls, var)

        # Call super's new
        return super(FootprintCopier, cls).__new__(cls, n, b, d)
