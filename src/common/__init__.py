#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The common (mostly NWP) VORTEX extension package.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

# Recursive inclusion of packages with potential FootprintBase classes
from . import algo, data, tools, syntax

#: No automatic export
__all__ = []

__tocinfoline__ = 'The common (mostly NWP) VORTEX extension'
