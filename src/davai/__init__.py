"""
The DAVAI extension package.

DAVAI stands for *Dispositif d'Aide à la VAlidation d'IFS-ARPEGE-AROME*.
"""

# Recursive inclusion of packages with potential FootprintBase classes
from . import algo, data, util, hooks

#: No automatic export
__all__ = []

__tocinfoline__ = 'The DAVAI extension'
