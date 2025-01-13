"""
AlgoComponents for NWP
"""

# Recursive inclusion of packages with potential FootprintBase classes
from . import forecasts as forecasts
from . import fpserver as fpserver
from . import coupling as coupling
from . import mpitools as mpitools
from . import odbtools as odbtools
from . import stdpost as stdpost
from . import assim as assim
from . import eps as eps
from . import eda as eda
from . import request as request
from . import monitoring as monitoring
from . import clim as clim
from . import oopsroot as oopsroot
from . import oopstests as oopstests

__all__ = []
