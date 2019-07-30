#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Additional info resources for DAVAI.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.outflow import StaticResource
from vortex.data.contents import JsonDictContent


class XPinfo(StaticResource):
    """Contains info about an experiment."""
    _footprint = dict(
        info = 'Contains info about an experiment.',
        attr = dict(
            kind = dict(
                values = ['xpinfo']
            ),
            nativefmt = dict(
                values = ['json', ]
            ),
            clscontents = dict(
                default  = JsonDictContent
            ),
        )
    )

    def namebuilding_info(self):
        """Base name on the scope."""
        bdict = super(XPinfo, self).namebuilding_info()
        bdict.update(radical=self.kind, )
        return bdict


class TrolleyOfSummaries(StaticResource):
    """Trolley of Summary of task(s)."""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['trolley']
            ),
            nativefmt = dict(
                values = ['tar', ]
            ),
        )
    )

    def namebuilding_info(self):
        """Base name on the kind."""
        bdict = super(TrolleyOfSummaries, self).namebuilding_info()
        bdict.update(radical=self.kind, )
        return bdict
