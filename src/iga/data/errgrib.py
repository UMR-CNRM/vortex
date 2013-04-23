#!/bin/env python
# -*- coding:Utf-8 -*-

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
                values = [ 3, 6, 9, 12 ],
            ),
        )
    )
     
    @classmethod
    def realkind(cls):
        return 'bgerrstd'
    
    def basename_info(self):
        return dict(
            radical='bgerrstd',
            format=self.nativefmt,
            geo=[{'truncation':self.geometry.truncation}],
            src=self.model,
            term=self.term.fmthm
        )
            
    def archive_basename(self):
        bname = 'errgribvor'
        if self.model == 'aearp':
            bname = bname + '(term' + self.term.fmthour + ':inout).(suffix:inout)'
        return bname


