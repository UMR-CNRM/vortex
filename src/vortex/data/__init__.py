#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Abstract classes involved in data management within VORTEX.

Actual resources and custom providers should be defined in dedicated packages.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from . import handlers, resources, containers, contents, providers, \
    executables, stores, geometries

#: No automatic export
__all__ = []

__tocinfoline__ = 'Abstract classes involved in data management within VORTEX'
