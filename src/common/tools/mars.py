#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

"""
Utility classes and function to work with the Mars database.
"""

#: No automatic export
__all__ = []


class MarsError(Exception):
    """General Mars error."""
    pass


class MarsRequestConfigurationError(MarsError):
    """Specific Mars request configuration error."""
    pass


class MarsGetError(MarsError):
    """Generic Mars get error."""
    pass
