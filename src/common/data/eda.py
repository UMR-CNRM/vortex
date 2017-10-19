#!/usr/bin/env python
# -*- coding: utf-8 -*-
from common.data.assim import _BackgroundErrorInfo

#: Automatic export off
__all__ = []


import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.flow       import GeoFlowResource
from vortex.syntax.stdattrs import term
from gco.syntax.stdattrs    import gvar


class RawFiles(GeoFlowResource):
    """Input files for wavelet covariances estimation. To be removed soon."""

    _footprint = [
        term,
        gvar,
        dict(
            info = 'Input files for wavelet covariances estimation',
            attr = dict(
                kind = dict(
                    values   = ['rawfiles'],
                ),
                nativefmt   = dict(
                    values  = ['rawfiles', 'unknown'],
                ),
                gvar = dict(
                    default = 'aearp_rawfiles_t[geometry:truncation]'
                ),
                ipert = dict(
                    type = int,
                    optional = True,
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return self.kind

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        return dict(
            radical = self.realkind,
            geo     = self._geo2basename_info(add_stretching=False),
            fmt     = self.nativefmt,
            src     = [self.model],
            term    = self.term.fmthm,
        )

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'RAWFILEP(memberfix:member)+{:s}.{:d}'.format(self.term.fmthour, self.geometry.truncation)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        raise NotImplementedError()

    def gget_basename(self):
        """GGET specific naming convention."""
        if self.ipert is None:
            raise ValueError('ipert is mandatory with the GCO provider')
        return '.{:03d}.tar'.format(self.ipert)


class InflationFactor(_BackgroundErrorInfo):
    """
    Inflation factor profiles.
    """

    _footprint = [
        term,
        dict(
            info='Inflation factor profiles',
            attr=dict(
                kind=dict(
                    values=['infl_factor', 'infl', 'inflation_factor'],
                    remap=dict(autoremap='first'),
                ),
                gvar = dict(
                    default = 'inflation_factor'
                ),
                nativefmt=dict(
                    values=['ascii'],
                    default='ascii',
                ),
                term=dict(
                    optional=True,
                    default=3
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'inflation_factor'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return self.realkind

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return self.realkind
