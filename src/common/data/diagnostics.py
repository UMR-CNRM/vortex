#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.flow import GeoFlowResource
from vortex.syntax.stdattrs import a_term

#: No automatic export
__all__ = []


class ISP(GeoFlowResource):

    """
    Class for Forecasted Satellite Image resource. Obsolete.
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
        return dict(
            fmt     = self.nativefmt,
            geo     = self._geo2basename_info(),
            radical = self.realkind,
            src     = self.model,
        )


class _DDHcommon(GeoFlowResource):
    """
    Abstract class for Horizontal Diagnostics.
    """
    _abstract = True
    _footprint = dict(
        info = 'Diagnostic on Horizontal Domains',
        attr = dict(
            kind = dict(
                values = [ 'ddh', 'dhf' ],
                remap = dict( dhf = 'ddh' )
            ),
            nativefmt = dict(),
            scope = dict(
                values = [ 'limited', 'dlimited', 'global', 'zonal' ],
                remap = dict( limited = 'dlimited' )
            ),
        )
    )

    def basename_info(self):
        """Generic information, radical = ``ddh``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = self._geo2basename_info(),
            radical = 'ddh',
            src     = [ self.model, self.scope ],
        )


class DDH(_DDHcommon):
    """
    Class for Horizontal Diagnostics.
    Used to be a ``dhf`` !
    """
    _footprint = dict(
        info = 'Diagnostic on Horizontal Domains',
        attr = dict(
            nativefmt = dict(
                values = [ 'lfi', 'lfa' ],
                default = 'lfi',
            ),
            term = a_term
        )
    )

    @property
    def realkind(self):
        return 'ddh'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'dhf{:s}{:s}+{:s}'.format(self.scope[:2].lower(), self.model[:4].lower(), self.term.fmth)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'DHF{:s}{:s}+{:s}'.format(self.scope[:2].upper(), self.model[:4].upper(), self.term.fmth)

    def basename_info(self):
        bdict = super(DDH, self).basename_info()
        bdict['term'] = self.term.fmthm
        return bdict


class DDHpack(_DDHcommon):
    """
    Class for Horizontal Diagnostics with all terms packed in a single directory.
    Used to be a ``dhf`` !
    """
    _footprint = dict(
        info = 'Diagnostic on Horizontal Domains packed in a single directory',
        attr = dict(
            nativefmt = dict(
                values = [ 'ddhpack', ],
            ),
        )
    )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'DHF{:s}{:s}.tar'.format(self.scope[:2].upper(), self.model[:4].upper())

    @property
    def realkind(self):
        return 'ddhpack'
