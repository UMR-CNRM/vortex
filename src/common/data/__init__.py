#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Common data resources (mostly NWP).
"""

from __future__ import print_function, absolute_import, unicode_literals, division

# Recursive inclusion of packages with potential FootprintBase classes
from . import boundaries, climfiles, consts, diagnostics, executables, fields
from . import assim, gridfiles, logs, modelstates, namelists, obs, surfex, eps, eda
from . import providers, stores, query, monitoring, ctpini

#: No automatic export
__all__ = []
