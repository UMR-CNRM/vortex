#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
*meteo.constants* sub-module:

Atmospheric physics constants.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import numpy

import footprints.loggers

logger = footprints.loggers.getLogger(__name__)

#: No automatic export
__all__ = []

#: gravity constant
g0 = 9.80665
#: Cp dry air
Cpd = 1004.709
#: Specific gas constant, dry air
Rd = 287.059
#: Specific gas constant, water vapor
Rv = 461.524
