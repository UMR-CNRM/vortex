#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.flow import Resource
from vortex.syntax.stdattrs import date, cutoff
from vortex.data.geometries import SpectralGeometry


class RawFields(Resource):

    _footprint = [
        date,
        cutoff,
        dict(
            info = 'File containing a limited list of observations fields',
            attr = dict(
                kind = dict(
                    values = [ 'rawfields' ]
                ),
                origin = dict(
                    values = [ 'nesdis', 'ostia', 'bdm' ]
                ),
                fields = dict(
                    values = [ 'sst', 'seaice' ]
                ),
            )
        )
    ]

    def olive_basename(self):
        return self.fields + self.origin

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
            radical=self.fields,
            src=self.origin,
        )

    def vortex_pathinfo(self):
        return dict(
            nativefmt = self.nativefmt,
            date      = self.date,
            cutoff    = self.cutoff
        )


class GeoFields(Resource):

    _footprint = [
        date,
        cutoff,
        dict(
            info = 'File containing a limited list of fields in a specific geometry',
            attr = dict(
                kind = dict(
                    values = [ 'geofields' ]
                ),
                fields = dict(
                    values = [ 'sst', 'seaice' ]
                ),
                geometry = dict(
                    type = SpectralGeometry,
                ),
                nativefmt = dict(
                    values = [ 'fa' ],
                    default = 'fa'
                )
            )
        )
    ]

    def olive_basename(self):
        bname = 'icmshanal' + self.fields
        if self.fields == 'seaice':
            bname = bname.upper()
        return bname

    def archive_basename(self):
        return 'icmshanal' + self.fields

    def vortex_pathinfo(self):
        return dict(
            nativefmt = self.nativefmt,
            date = self.date,
            cutoff = self.cutoff
        )

    def basename_info(self):
        if self.geometry.lam:
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}]
        return dict(
            radical = self.fields,
            geo     = lgeo,
            fmt     = self.nativefmt
        )
