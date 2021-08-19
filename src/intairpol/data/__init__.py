# -*- coding: utf-8 -*-

"""
Specific INTAIRPOL data resources.
"""

from __future__ import absolute_import, print_function, division, unicode_literals

# Recursive inclusion of packages with potential FootprintBase classes
from . import (
    climfiles,
    consts,
    current_scenario,
    elements,
    executables,
    executables_mocacc,
    mocacc,
    mocage,
    mocage_cfg,
)

#: No automatic export
__all__ = []
