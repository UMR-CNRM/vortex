#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A collection of basic utilities that are used in the Vortex project
but also in other one. Consequently, this package is independent
of the Vortex package. Ideally, we would have chosen the name
*swissknife* for this package but sadly we were pipped to the post.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints.loggers

logger = footprints.loggers.getLogger(__name__)

#: No automatic export
__all__ = []

__version__ = '1.0.2'
