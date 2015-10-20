#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.flow import SpectralGeoFlowResource
from vortex.syntax.stdattrs import a_term


class ISP(SpectralGeoFlowResource):

    """
    Class for Forecasted Satellite Image resource.
    Used to be an ``isp`` !
    """
    _footprint = dict(
       info = 'Forecasted Satellite Image',
       attr = dict(
           kind = dict(
               values = [ 'isp', 'fsi' ]
           ),
           nativefmt = dict(
                values = [ 'foo' ],
                default = 'foo',
           ),
        )
    )

    @property
    def realkind(self):
        return 'isp'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'anim0'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'ISP' + self.model[:4].upper()

    def basename_info(self):
        """Generic information, radical = ``isp``."""
        if self.geometry.lam:
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}]

        return dict(
            fmt     = self.nativefmt,
            geo     = lgeo,
            radical = self.realkind,
            src     = self.model,
        )


class DDH(SpectralGeoFlowResource):

    """
    Class for Horizontal Diagnostics.
    Used to be a ``dhf`` !
    """
    _footprint = dict(
       info = 'Diagnostic on Horizontal Domains',
       attr = dict(
           kind = dict(
               values = [ 'ddh', 'dhf' ],
               remap = dict( dhf = 'ddh' )
           ),
           nativefmt = dict(
                values = [ 'lfi', 'lfa' ],
                default = 'lfi',
           ),
           scope = dict(
            values = [ 'limited', 'dlimited', 'global', 'zonal' ],
            remap = dict( limited = 'dlimited' )
           ),
           term = a_term
        )
    )

    @property
    def realkind(self):
        return 'ddh'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'dhf%s%s+%4.4d'.format(self.scope[:2].lower(), self.model[:4].lower(), self.term.fmth)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'DHF{0:s}{0:s}+{0:s}'.format(self.scope[:2].upper(), self.model[:4].upper(), self.term.fmth)

    def basename_info(self):
        """Generic information, radical = ``isp``."""
        if self.geometry.lam:
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}]

        return dict(
            fmt     = self.nativefmt,
            geo     = lgeo,
            radical = 'ddh',
            src     = [ self.model, self.scope ],
            term    = self.term.fmthm,
        )

