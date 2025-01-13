"""
Standalone tools for NWP
"""

# Recursive inclusion of packages with potential FootprintBase classes
from . import conftools as conftools
from . import ifstools as ifstools

#: Automatic export of data subpackage
__all__ = []
