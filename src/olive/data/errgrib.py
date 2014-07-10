#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.flow import GeoFlowResource
from vortex.tools.date import Time


class BackgroundErrStd(GeoFlowResource):

    _footprint = dict(
        info = 'Background error standard deviation file',
        attr = dict(
            kind = dict(
                values = [ 'bgerrstd' ]
            ),
            term = dict(
                type = Time,
                values = [ 3, 9, 12 ],
            ),
        )
    )

    @property
    def realkind(self):
        return 'bgerrstd'

    def basename_info(self):
        return dict(
            radical = 'bgerrstd',
            fmt     = self.nativefmt,
            geo     = [{'truncation':self.geometry.truncation}],
            src     = self.model,
            term    = self.term.fmthm
        )

    def archive_basename(self):
        return '(errgribfix:igakey)'


