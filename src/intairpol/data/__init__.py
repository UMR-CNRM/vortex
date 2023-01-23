"""
Specific INTAIRPOL data resources.
"""

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
