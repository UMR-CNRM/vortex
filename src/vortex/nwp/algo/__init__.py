"""
AlgoComponents for NWP
"""

# Recursive inclusion of packages with potential FootprintBase classes
from . import forecasts, fpserver, coupling, mpitools, odbtools, stdpost, assim, \
    eps, eda, request, monitoring, clim
from . import oopsroot, oopstests


#: No automatic export
__all__ = []
