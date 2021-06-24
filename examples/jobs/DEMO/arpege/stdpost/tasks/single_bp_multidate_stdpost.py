# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.layout.nodes import Driver, LoopFamily

from .commons_basic import BasicPlusStdpost


def setup(t, **kw):
    """
    Loop on several dates and launch a :class:`BasicPlusStdpost` task
    on each of them.
    """
    return Driver(
        tag='single_b',
        ticket=t,
        nodes=[
            LoopFamily(
                tag='single_b_stdposts',
                loopconf='rundates',
                loopsuffix='+d{.ymdh:s}',
                nodes=[
                    BasicPlusStdpost(tag='single_stdpost', ticket=t, **kw),
                ],
                ticket=t,
                **kw
            ),
        ],
        options=kw
    )
