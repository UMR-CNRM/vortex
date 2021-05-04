#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Common standalone tools (mostly for NWP).
"""

from __future__ import print_function, absolute_import, unicode_literals, division

# Recursive inclusion of packages with potential FootprintBase classes
from . import conftools
from . import ifstools

#: Automatic export of data subpackage
__all__ = []
