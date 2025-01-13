"""
Data resources (mostly NWP).
"""

# Recursive inclusion of packages with potential FootprintBase classes
from . import boundaries as boundaries
from . import climfiles as climfiles
from . import consts as consts
from . import diagnostics as diagnostics
from . import executables as executables
from . import fields as fields
from . import assim as assim
from . import gridfiles as gridfiles
from . import logs as logs
from . import modelstates as modelstates
from . import namelists as namelists
from . import obs as obs
from . import surfex as surfex
from . import eps as eps
from . import eda as eda
from . import providers as providers
from . import stores as stores
from . import query as query
from . import monitoring as monitoring
from . import ctpini as ctpini
from . import oopsexec as oopsexec
from . import configfiles as configfiles

#: No automatic export
__all__ = []
