#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.resources import Resource
from vortex.data.flow import FlowResource, GeoFlowResource

from common.data.modelstates import InitialCondition
from vortex.tools.date import Date


class SolutionPoint(FlowResource):
    """Class for point solutions of the model HYCOM i.e s*pts (ascii file)."""

    _footprint = dict(
        info = 'Surges model point solution',
        attr = dict(
            kind = dict(
                values = ['Pts', 'PtsGironde'],
            ),
            nativefmt = dict(
                values  = ['ascii'],
                default = 'ascii',
            ),
            fields = dict(
                values = ['s_pts', 's_ffpts', 's_ddpts', 's_pppts', 's_marpts',
                          '_huv.txt', 'surcote', 'windFF10', 'windDD10', 'Pmer',
                          'maree', 'HUV_Gironde'],
                remap = {
                    'surcote': 's_pts',
                    'windFF10': 's_ffpts',
                    'windDD10': 's_ddpts',
                    'Pmer': 's_pppts',
                    'maree': 's_marpts',
                    'HUV_Gironde': '_huv.txt',
                },
            ),
        )
    )

    @property
    def realkind(self):
        return 'pts'

    def basename_info(self):
        return dict(
            radical = self.fields,
        )


class ForcingOutData(InitialCondition):
    """Class of a Stress, wind and pressure interpolated file min max values."""

    _footprint = dict(
        info = 'Set of ...',
        attr = dict(
            kind = dict(
                values  = ['ForcingOut']
            ),
            nativefmt = dict(
                values  = ['ascii', 'unknown'],
            ),
            fields = dict(
                values  = ['preatm', 'tauewd', 'taunwd', 'windx', 'windy'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'ForcingOut'

    def basename_info(self):
        lgeo = [self.geometry.area, self.geometry.rnice]
        return dict(
            fmt     = self.nativefmt,
            geo     = lgeo,
            radical = self.realkind + '.' + self.fields,
            src     = [self.filling, self.model],
        )


class ConfigData(Resource):
    """Class of a simple file that contains configuration data for HYCOM."""

    _footprint = dict(
        info = 'Configuration data for HYCOM',
        attr = dict(
            nativefmt = dict(
                default = 'ascii',
                values = ['ascii'],
            ),
            kind = dict(
                values = ['dataconf'],
            ),
            mod = dict(
                optional = True,
                default = 'PR',
                values = ['PR', 'AA'],
            ),
            date = dict(
                optional = True,
                type = Date,
            ),
        )
    )


class Rules_fileGrib(Resource):
    """Class of a simple file that contains Rules for grib_api's grib_filter."""

    _footprint = dict(
        info = 'Rules_files for grib_filter (grib_api)',
        attr = dict(
            nativefmt = dict(
                default = ['ascii'],
            ),
            kind = dict(
                values = ['Rules_fileGrib'],
            ),
        )
    )


class TarResult(GeoFlowResource):

    _footprint = dict(
        info = 'tarfile archive with all members directories of HYCOM',
        attr = dict(
            kind = dict(
                values = ['surges_tarfile', ],
            ),
            nativefmt = dict(
                values = ['tar'],
                default = 'tar'
            ),
        )
    )

    @property
    def realkind(self):
        return 'surges_tarfile'

    def basename_info(self):
        return dict(
            fmt     = self.nativefmt,
            geo     = [self.geometry.area, self.geometry.rnice],
            radical = self.realkind,
            src     = self.model,
        )
