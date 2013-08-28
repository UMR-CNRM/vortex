#!/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common targets sused at Meteo France.
"""

#: No automatic export
__all__ = []

from vortex.tools.targets import Target
from vortex.syntax.priorities import top


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

class MeteoBull(Target):
    """Bull Computer."""

    _footprint = dict(
        info = 'Bull Supercomputer at Meteo France',
        attr = dict(
            hostname = dict(
                values = \
                    [ x+str(y) for x in ('beaufix',) for y in range(1000) ] + \
                    [ x+str(y) for x in ('beaufixlogin',) for y in range(6) ] + \
                    [ x+str(y) for x in ('beaufixtransfert',) for y in range(4) ]
            ),
            sysname = dict(
                values = [ 'Linux' ]
            ),
            inifile = dict(
                default = 'target-beaufix.ini',
            )
        ),
        priority = dict(
            level = top.OPER
        )
    )
