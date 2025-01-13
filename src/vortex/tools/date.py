"""
Classes and functions form this module are dedicated to the manipulation of
date and time quantities.

It is kept for backward compatibility, however :mod:`bronx.stdtypes.date` should
be used now and on.
"""

import sys

from bronx.stdtypes import date as _b_date

_ALIASES = _b_date.local_date_functions.copy()
_ALIASES.update(
    dict(
        guess=_b_date.guess,
        daterange=_b_date.daterange,
        stamp=_b_date.stamp,
        Period=_b_date.Period,
        Date=_b_date.Date,
        Time=_b_date.Time,
        Month=_b_date.Month,
    )
)

for n, obj in _ALIASES.items():
    sys.modules[__name__].__dict__.update(_ALIASES)
