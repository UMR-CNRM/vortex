#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Time, Period

from vortex.data.resources import Resource
from vortex.data.flow import FlowResource, GeoFlowResource
from common.data.modelstates import InitialCondition, Historic
from common.data.gridfiles import GridPoint
from vortex.syntax.stddeco import namebuilding_delete, namebuilding_insert, namebuilding_append
from .contents import AltidataContent

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


@namebuilding_insert('radical', lambda s: s.fields)
@namebuilding_delete('src')
@namebuilding_delete('fmt')
class SolutionPoint(FlowResource):
    """Class for port solutions of the HYCOM model i.e s*pts (ascii file)."""
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


class SolutionPointIMB(SolutionPoint):
    """Class for port solutions of the HYCOM model i.e s*pts (ascii file)."""
    _footprint = dict(
        info = 'Surges model point solution',
        attr = dict(
            kind = dict(
                values = ['PtsImb'],
            ),
            fields = dict(
	      values = ['s_pts'],
            ),
	    modele_imbrique = dict(
	      values = ['reunion','mayotte'],
	    ),
        )
    )

    @property
    def realkind(self):
        return 'pts'

    def basename_info(self):
        return dict(
            radical = self.fields + '.' + self.modele_imbrique,
        )


@namebuilding_insert('radical', lambda s: s.fields)
@namebuilding_insert('geo', lambda s: [s.geometry.area, s.geometry.rnice])
@namebuilding_delete('src')
class SolutionMaxGrid(GeoFlowResource):
    """Class for solutions interpolated on MF grid, i.e s*max (ascii file)."""
    _footprint = dict(
        info = 'Surges model 24h - max solution',
        attr = dict(
            kind = dict(
                values = ['surges_max'],
            ),
            nativefmt = dict(
                values  = ['ascii'],
                default = 'ascii',
            ),
            fields = dict(
                values = ['s_max', 's_uvpmax', 'surcote_max', 'uvp_max'],
                remap = {
                    'surcote_max': 's_max',
                    'uvp_max': 's_uvpmax',
                },
            ),
        )
    )

    @property
    def realkind(self):
        return 'smax'


@namebuilding_insert('radical', lambda s: s.fields)
@namebuilding_delete('src')
@namebuilding_delete('fmt')
class CouplingWw3Write(GeoFlowResource):
    """Class for Nested solutions of the HYCOM model (coupling file)."""
    _footprint = dict(
        info = 'Coupling Surges model (H, u, v) solution on WW3 grid (binary data file)',
        attr = dict(
            kind = dict(
                values = ['SurgesWw3coupling'],
            ),
            nativefmt = dict(
                values  = ['foo', 'unknown'],
                default = 'foo',
            ),
            fields = dict(
                values = ['Hauteur', 'UV_current', 'level.ww3', 'current.ww3'],
                remap = {
                    'Hauteur': 'level.ww3',
                    'UV_current': 'current.ww3',
                },
            ),
        )
    )

    @property
    def realkind(self):
        return 'SurgesWw3coupling'


@namebuilding_insert('radical', lambda s: s.fields)
@namebuilding_delete('src')
@namebuilding_delete('fmt')
class SurgesResultNative(GeoFlowResource):
    """Class for grid solutions of the HYCOM model (netcdf file)."""
    _footprint = dict(
        info = '(H, u, v) parameters data projected in native geometry grid HYCOM with/without forcing (netcdf data file)',
        attr = dict(
            kind = dict(
                values = ['SurgesResultNative'],
            ),
            nativefmt = dict(
                values  = ['netcdf'],
                default = 'netcdf',
            ),
            fields = dict(
                values = ['HUV_ltideonly_forcing', 'lssh_global_ms.nc',
                          'HUV_ltide_wind_forcing', 'lssh_global_full.nc',
                          'HUV_tideonly_forcing', 'HUV_tide_wind_forcing',
                          'ssh_global_full.nc', 'ssh_global_ms.nc',
                          'ssh_global.nc', 'maree_global.nc'],
                remap = {
                    'HUV_ltideonly_forcing': 'lssh_global_ms.nc',
                    'HUV_tideonly_forcing': 'ssh_global_ms.nc',
                    'HUV_ltide_wind_forcing': 'lssh_global_full.nc',
                    'HUV_tide_wind_forcing': 'ssh_global_full.nc',
                },
            ),
        )
    )

    @property
    def realkind(self):
        return 'SurgesResultNative'


@namebuilding_delete('fmt')
@namebuilding_insert('period', lambda s: [{'endtime': s.timeslot + Period('PT24H')},
                                          {'begintime': s.timeslot}, ])
class BufrPoint(FlowResource):
    """Class for point solutions of the HYCOM model i.e bufr."""
    _footprint = dict(
        info = ('Surges model temporal solution bufr (for 24h period) (2d current (u,v) ' +
                'Pmer, U10, V10, surcote and (Hauteur d eau Maree))'),
        attr = dict(
            kind = dict(
                values = ['bufr_surges'],
            ),
            nativefmt = dict(
                values  = ['bufr'],
                default = 'bufr',
            ),
            timeslot = dict(
                type = Time,
                default = 0,
            ),
        )
    )

    @property
    def realkind(self):
        return 'bufr'


@namebuilding_insert('radical', lambda s: s.realkind + '.' + s.fields)
@namebuilding_insert('geo', lambda s: [s.geometry.area, s.geometry.rnice])
class ForcingOutData(InitialCondition):
    """Class of a Stress, wind and pressure forcing interpolated on native grid Hycom
    and min max values."""
    _footprint = dict(
        info = 'Stress, wind and pressure forcing interpolated on native grid Hycom and min max values.',
        attr = dict(
            kind = dict(
                values  = ['ForcingOut']
            ),
            nativefmt = dict(
                values  = ['ascii', 'unknown'],
            ),
            fields = dict(
                values  = ['preatm', 'tauewd', 'taunwd',
                           'windx', 'windy', 'mslprs',
                           'wndnwd', 'wndewd'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'ForcingOut'


@namebuilding_insert('radical', lambda s: s.realkind + '.' + s.fields)
@namebuilding_insert('geo', lambda s: [s.geometry.area, s.geometry.rnice])
@namebuilding_insert('src', lambda s: [s.model, ])
class TideOnlyOut(InitialCondition):
    """."""
    _footprint = dict(
        info = '',
        attr = dict(
            kind = dict(
                values  = ['TideOnlyOut']
            ),
            nativefmt = dict(
                values  = ['ascii', 'unknown'],
            ),
            fields = dict(
                values  = ['pts', 'nat', 'native', 'txt', 'info'],
                remap = {
                    'info': 'txt',
                    'native': 'nat',
                },
            ),
        )
    )

    @property
    def realkind(self):
        return 'TideOnlyOut'


class ConfigData(Resource):
    """Class of a simple file that contains configuration data for HYCOM/MFWAM."""
    _footprint = dict(
        info = 'Configuration data for HYCOM/MFWAM',
        attr = dict(
            nativefmt = dict(
                default = 'ascii',
                values = ['ascii'],
            ),
            kind = dict(
                values = ['dataconf'],
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


@namebuilding_insert('geo', lambda s: [s.geometry.area, s.geometry.rnice])
class TarResult(GeoFlowResource):
    """Class of tarfile for surges result"""
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


@namebuilding_append('src', lambda s: s.fields)
class InitWave(Historic):
    """Class of"""
    _footprint = dict(
        info = 'WaveInitialCondition LAW and Spectrum data BLS on native grid',
        attr = dict(
            kind = dict(
                values = ['InitWave'],
            ),
            fields = dict(
                values = ['LAW', 'guess', 'BLS', 'spectre'],
                remap = {
                    'guess': 'LAW',
                    'spectre': 'BLS',
                },
            ),
            nativefmt = dict(
                default = 'unknown',
            ),
        )
    )

    @property
    def realkind(self):
        return 'historic'

    def basename_info(self):
        lgeo = [self.geometry.area, self.geometry.rnice]
        return dict(
            fmt     = self.nativefmt,
            geo     = lgeo,
            radical = self.realkind + '.' + self.fields,
            src     = self.model,
            term    = self.term.fmthm,
        )

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.fields == 'BLS':
            return '(icmshfix:modelkey)'
	else:
	    return '(histfix:modelkey)'


class OutputWave(GridPoint):
    """Class of"""
    _footprint = dict(
        info = 'forecast output MPP and analyse next assimilation APP',
        attr = dict(
            kind = dict(
                values = ['OutputWave'],
            ),
            origin = dict(
                values = ['fcst', 'ana', 'assim'],
                remap = {
                    'assim': 'ana',
                },
            ),
            nativefmt = dict(
                default = 'unknown' # grille irreguliere
            ),
        )
    )

    @property
    def realkind(self):
        return 'WaveOutput'


class INITWAM(GeoFlowResource):

    _footprint = dict(
        info = 'file for Extraction grb',
        attr = dict(
            nativefmt = dict(
                default = ['foo'],
            ),
            kind = dict(
                values = ['INITWAM'],
            ),
        )
    )


#class WAMGRIDINFO(GeoFlowResource):

    #_footprint = dict(
        #info = 'file for Extraction grb',
        #attr = dict(
            #nativefmt = dict(
                #default = ['foo'],
            #),
            #kind = dict(
                #values = ['WAM', 'wam_info'],
            #),
        #)
    #)


class AltidataWave(FlowResource):

    _footprint = dict(
        info = 'Altimetric data file',
        attr = dict(
            nativefmt = dict(
                default = 'ascii',
            ),
#            scope = dict(
#                optional = True,
#                default = 'assim',
#            ),
            satellite = dict(
                values = ['jason2','cryosat2','saral','allsat',
                          'altidata', 'obs_alti', 'sentinel3',
                          'S3al3','cfosat'],
                optional = True,
                default = 'allsat',
                remap = {
                    'allsat': 'altidata',
                    'sentinel3': 'S3al3',
                },
            ),
            kind = dict(
                values = ['AltidataWave','altidata'],
            ),
            clscontents=dict(
                    default = AltidataContent
            ),
        )
    )

    @property
    def realkind(self):
        return 'AltidataWave'

    def basename_info(self):
        return dict(
            fmt     = self.nativefmt,
            radical = self.realkind + '_' + self.satellite,
            src     = self.model,
        )

class SARdataWave(FlowResource):

    _footprint = dict(
        info = 'Spectral data file',
        attr = dict(
            nativefmt = dict(
                default = 'ascii',
            ),
#            scope = dict(
#                optional = True,
#                default = 'assim',
#            ),
            satellite = dict(
                values = ['sentinel1','cfosat','allsat'],
                optional = True,
                default = 'allsat',
            ),
            kind = dict(
                values = ['SARdataWave'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'SARdataWave'

    def basename_info(self):
        return dict(
            fmt     = self.nativefmt,
            radical = self.realkind + '_' + self.satellite,
            src     = self.model,
        )


class DiagAlti(AltidataWave):

    _footprint = dict(
        info = 'diagnostic file next altimetric filtering',
        attr = dict(
            kind = dict(
                values = ['DiagAlti'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'diagalti'


class WaveCurrent(FlowResource):

    _footprint = dict(
        info = '',
        attr = dict(
            kind = dict(
                values = ['WaveCurrent'],
            ),
            nativefmt = dict(
                default = 'grib',
            ),
        )
    )

    @property
    def realkind(self):
        return 'WaveCurrent'
