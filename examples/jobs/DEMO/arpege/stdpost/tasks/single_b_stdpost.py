# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.layout.nodes import Driver

from .commons_basic import BasicStdpost


def setup(t, **kw):
    """Just launch a single :class:`BasicStdpost` task."""
    return Driver(
        tag='single_b',
        ticket=t,
        nodes=[
            BasicStdpost(tag='single_stdpost', ticket=t, **kw),
        ],
        options=kw
    )
