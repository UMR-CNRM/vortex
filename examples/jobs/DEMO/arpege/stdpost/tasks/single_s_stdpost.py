# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.layout.nodes import Driver

from .commons_script import ScriptStdpost


def setup(t, **kw):
    """Just launch a single :class:`ScriptStdpost` task."""
    return Driver(
        tag='single_s',
        ticket=t,
        nodes=[
            ScriptStdpost(tag='single_stdpost', ticket=t, **kw),
        ],
        options=kw
    )
