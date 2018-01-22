#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.outflow  import NoDateResource
from vortex.data.flow import GeoFlowResource

from vortex.syntax.stdattrs import date, cutoff


class RawFields(NoDateResource):

    _footprint = [
        date, cutoff,
        dict(
            info = 'File containing a limited list of observations fields',
            attr = dict(
                kind = dict(
                    values = ['rawfields']
                ),
                origin = dict(
                    values = ['bdm', 'nesdis', 'ostia', 'psy4', 'bdpe', 'safosi']
                ),
                fields = dict(
                    values = ['sst', 'seaice', 'ocean']
                ),
            )
        )
    ]

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            nativefmt = self.nativefmt,
            date      = self.date,
            cutoff    = self.cutoff,
        )

    @property
    def realkind(self):
        return 'rawfields'

    def olive_basename(self):
        if self.origin == 'nesdis' and self.fields == 'sst':
            bname = '.'.join((self.fields, self.origin, 'bdap'))
        elif self.fields == 'seaice':
            bname = 'ice_concent'
        else:
            bname = '.'.join((self.fields, self.origin))
        return bname

    def archive_basename(self):
        if self.origin == 'nesdis' and self.fields == 'sst':
            bname = '.'.join((self.fields, self.origin, 'bdap'))
        elif self.fields == 'seaice':
            bname = 'ice_concent'
        else:
            bname = '.'.join((self.fields, self.origin))
        return bname

    def basename_info(self):
        return dict(
            radical = self.fields,
            src     = [self.origin, ],
        )


class GeoFields(GeoFlowResource):

    _footprint = [
        dict(
            info = 'File containing a limited list of fields in a specific geometry',
            attr = dict(
                kind = dict(
                    values  = ['geofields']
                ),
                fields = dict(
                    values  = ['sst', 'seaice', 'ocean']
                ),
                nativefmt = dict(
                    values  = ['fa'],
                    default = 'fa'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'geofields'

    def olive_basename(self):
        bname = 'icmshanal' + self.fields
        if self.fields == 'seaice':
            bname = bname.upper()
        return bname

    def archive_basename(self):
        return 'icmshanal' + self.fields

    def basename_info(self):
        return dict(
            radical = self.fields,
            geo     = self._geo2basename_info(),
            fmt     = self.nativefmt,
            src     = [self.model],
        )
