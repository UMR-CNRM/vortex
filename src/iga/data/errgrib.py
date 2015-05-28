#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints

from vortex.data.flow import GeoFlowResource
from vortex.tools.date import Time


class BackgroundStdErr(GeoFlowResource):

    _footprint = dict(
        info = 'Background error standard deviation file',
        attr = dict(
            kind = dict(
                values = ['bgstderr']
            ),
            term = dict(
                type   = Time,
                values = [3, 6, 9, 12],
            ),
        ),
        priority = dict(
          level = footprints.priorities.top.OPER,
        ),
    )

    @property
    def realkind(self):
        return 'bgstderr'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
            geo     = [{'truncation': self.geometry.truncation}],
            src     = self.model,
            term    = self.term.fmthm
        )

    def archive_basename(self):
        bname = 'errgribvor'
        if self.model == 'aearp':
            bname = bname + '(term' + self.term.fmthour + ':inout).(suffix:inout)'
        return bname
