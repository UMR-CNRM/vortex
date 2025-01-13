"""
This is a pure package containing several modules that could be used
as standalone tools.
"""

from . import storage as storage
from . import schedulers as schedulers
from . import services as services
from . import systems as systems
from . import targets as targets
from . import date as date
from . import env as env
from . import names as names

#: No automatic export
__all__ = []

__tocinfoline__ = (
    "VORTEX generic tools (system interfaces, format handling, ...)"
)
