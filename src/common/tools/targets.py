#!/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common targets sused at Meteo France.
"""

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger

from vortex.tools.targets import Target


class NECSX9(Target):
    """NEC Vector Computer."""

    _footprint = dict(
        info = 'NEC vector computer SX9',
        attr = dict(
            hostname = dict(
                values = [ 'unix' ] + [ x+'0'+str(y) for x in ('yuki', 'kumo') for y in range(10) ]
            ),
            sysname = dict(
                values = [ 'SUPER-UX' ]
            ),
            inifile = dict(
                default = 'target-necsx9.ini',
            )
        )
    )
