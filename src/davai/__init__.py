#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The DAVAI extension package.

DAVAI stands for *Dispositif d'Aide à la VAlidation d'IFS-ARPEGE-AROME*.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

# Recursive inclusion of packages with potential FootprintBase classes
from . import algo, data, util, hooks

#: No automatic export
__all__ = []

__tocinfoline__ = 'The DAVAI extension'
