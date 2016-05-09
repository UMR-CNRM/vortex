#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


import re

from vortex.tools import date, env
from vortex.data.flow import GeoFlowResource
from vortex.syntax.stdattrs import term, a_cutoff

from common.tools.igastuff import archive_suffix


class _AbstractLAMBoundary(GeoFlowResource):
    """
    Class of a coupling file for a Limited Area Model.
    A SpectralGeometry object is needed.
    """

    _abstract = True
    _footprint = [
        term,
        dict(
            info = 'Coupling file for a limited area model',
            attr = dict(
                kind = dict(
                    values  = ['boundary', 'elscf', 'coupled'],
                    remap   = dict(autoremap = 'first'),
                ),
                nativefmt = dict(
                    values  = ['fa', 'grib', 'unknown'],
                    default = 'fa',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'boundary'

    @property
    def _mysrc(self):
        raise NotImplementedError

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if self.mailbox.get('block', '-') == 'surfan':
            hhreal = self.term
        else:
            e = env.current()
            if 'HHDELTA_CPL' in e:
                actualbase = self.date - date.Time(e.HHDELTA_CPL + 'H')
            else:
                actualbase = date.synop(base=self.date)
            hhreal = (self.date - actualbase).time() + self.term
        return 'ELSCFALAD_' + self.geometry.area + '+' + hhreal.fmthour

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        suffix = archive_suffix(self.model, self.cutoff, self.date)
        prefix = 'COUPL'
        source = self._mysrc[0] if isinstance(self._mysrc, list) else self._mysrc
        if re.match('assist1bis|testms1', self.geometry.area):
            prefix = 'COUPL1'
        if re.match('ifs|ecmwf', source) and '16km' in self.geometry.rnice:
            prefix = 'COUPLIFS'

        return prefix + self.term.fmthour + '.r' + str(suffix)

    def basename_info(self):
        """Generic information, radical = ``cpl``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = [self.geometry.area, self.geometry.rnice],
            src     = self._mysrc,
            radical = 'cpl',
            term    = self.term.fmthm,
        )

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        if self.model == 'arome':
            directory = 'fic_day'
        else:
            directory = 'autres'
        return dict(
            fmt       = directory,
            model     = self.model,
            nativefmt = self.nativefmt,
        )


class LAMBoundary(_AbstractLAMBoundary):
    """
    Class of a coupling file for a Limited Area Model.
    A SpectralGeometry object is needed and the source model is given in the footprint.
    """

    _footprint = dict(
        attr = dict(
            source = dict(
                values  = ['arpege', 'aladin', 'arome', 'ifs', 'ecmwf']
            ),
        )
    )

    @property
    def _mysrc(self):
        return self.source


_a_source_cutoff = a_cutoff
del _a_source_cutoff['alias']
_a_source_cutoff['optional'] = True
_a_source_cutoff['default'] = 'production'


class EnhancedLAMBoundary(_AbstractLAMBoundary):
    """
    Class of a coupling file for a Limited Area Model.
    A SpectralGeometry object is needed and the source app, source conf and
    source cutoff is given in the footprint.
    """

    _footprint = dict(
        attr = dict(
            source_app = dict(),
            source_conf = dict(),
            source_cutoff = _a_source_cutoff,
        )
    )

    @property
    def _mysrc(self):
        return [self.source_app, self.source_conf,
                {'cutoff': self.source_cutoff}]
