#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
The Mercator VORTEX extension package.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

# Recursive inclusion of packages with potential FootprintBase classes
from . import data

#: Automatic export of data subpackage
__all__ = ['data', ]

__tocinfoline__ = 'The Mercator VORTEX extension'
