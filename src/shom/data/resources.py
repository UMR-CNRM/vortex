# -*- coding: utf-8 -*-
"""
Hycom3d files
"""

from bronx.stdtypes.date import Date
from common.data.gridfiles import GridPoint
from common.data.boundaries import LAMBoundary
from vortex.data.flow import FlowResource
from common.data.modelstates import Analysis, InitialCondition
from vortex.data.flow import GeoFlowResource
from vortex.data.outflow import StaticGeoResource
from vortex.syntax.stddeco import namebuilding_append

__all__ = []


class MeteoFranceInput(GridPoint):
    """MeteoFrance Forecast and Analyse run files"""

    _footprint = [
        dict(
            info="MeteoFrance Forecast and Analyse run files",
            attr=dict(
                origin=dict(
                    values=["ana","fcst"]
                ),
                cumul=dict(
                    values=["cumul","insta"]
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "gridpoint"


class MercatorDailyForecast(LAMBoundary):

    _footprint = [
        dict(
            info="Mercator daily forecast run",
            attr=dict(
                kind=dict(values=["boundary"]),
                nativefmt=dict(values=["netcdf", "nc"], default="netcdf"),
                cutoff=dict(values=['production']),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "mercator_daily_forecast"


class CmemsRivers(FlowResource):
    """Rivers file from cmems in 'tar' format"""

    _footprint = [
        dict(
            info='Rivers tar file from cmems',
            attr=dict(
                kind=dict(
                    values=["observations"]
                ),
                nativefmt=dict(
                    values=['tar']
                ),
                model=dict(
                    values=['cmems']
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return 'rivers'
    

@namebuilding_append('src', lambda self: self.grids)
class Hycom3dAtmFrcInterpWeights(StaticGeoResource):

    _footprint = [
        dict(
            info="Hycom3d atmfrc interpolation weights nc file",
            attr=dict(
                kind=dict(values=["interp_weights"]),
                nativefmt=dict(values=['netcdf','nc']),
                grids=dict(values=["a2o","o2a"], optional=False, default='a2o'),
            ),
        )
    ]

    @property
    def realkind(self):
        return self.kind


# %% Pre-processing intermediate files

@namebuilding_append('geo', lambda self: [self.field, self.interp])
class Hycom3dInterpOutput(GeoFlowResource):

    _footprint = [
        dict(
            info="Single variable netcdf file created by regridcdf",
            attr=dict(
                kind=dict(
                    values=["boundary"],
                ),
                field=dict(
                    values=["saln", "temp", "thdd", "vaisa", "ssh"],
                    optional=True
                ),
                nativefmt=dict(
                    values=["netcdf", "nc"],
                    default="netcdf",
                ),
                interp=dict(
                    values=["time", "space"],
                    optional=True
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_interp"


#%% Model inputs

@namebuilding_append('src', lambda self: self.field)
class Hycom3dModelInput(GeoFlowResource):
    """Hycom3d model input"""
    
    _footprint = [
        dict(
            info="Model Input .a and .b files",
            attr=dict(
                kind=dict(
                    values=["gridpoint"],
                ),
                field=dict(
                    values=["s", "t", "h", "rmu", "u", "v",
                            'shwflx','radflx','precip','preatm','airtmp',
                            'wndspd','tauewd','taunwd','vapmix'],
                    optional=True,
                ),
                format=dict(values=["a", "b", "nc", "r"]),
                nativefmt=dict(
                    values=["binary", "ascii", "netcdf"],
                    remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
                ),
                actualfmt=dict(
                    values=["binary", "ascii", "netcdf"],
                    remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_model_input"


@namebuilding_append('src', lambda self: self.rivers)
class Hycom3dRiversModelInput(Hycom3dModelInput):
    """Rivers input files for the Hycom3d model"""

    _footprint = [
        dict(
            info='Hycom3d rivers input files',
            attr=dict(
                kind=dict(
                    values = ['observations'],
                ),
                rivers=dict(
                    optional=False,
                ),
                format=dict(
                     values=['r','nc']
                ),
                nativefmt=dict(
                    values=['ascii','netcdf'],
                    remap={'r':'ascii','nc':'netcdf'}
                ),
                actualfmt=dict(
                    values=['ascii','netcdf'],
                    remap={'r':'ascii','nc':'netcdf'}
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'hycom3d_model_input'


#%% Initial conditions

@namebuilding_append('src', lambda self: self.field)
class Hycom3dInitialCondition(InitialCondition):

    _footprint = [
        dict(
            info="Single variable netcdf and restart file created by inicon",
            attr=dict(
                kind=dict(
                    values=["ic", "initial_condition"],
                ),
                field=dict(
                    values=["saln", "temp", "th3d", "u", "v", "ut", "vt", 
                            "h", "dpmixl"],
                ),
                format=dict(
                    values=["cdf", "res"],
                ),
                nativefmt=dict(
                    remap={"cdf": "netcdf", "res": "binary"},
                    values=["binary", "netcdf"],
                ),
                actualfmt=dict(
                    remap={"cdf": "netcdf", "res": "binary"},
                    values=["binary", "netcdf"],
                )
            ),
        ),
    ]


@namebuilding_append('src', lambda self: self.field)
class Hycom3dInitialConditionDate(InitialCondition):

    _footprint = [
        dict(
            info="Restart date in a binary file",
            attr=dict(
                kind=dict(
                    values=["ic", "initial_condition"],
                ),
                field=dict(
                    values=["restdate"],
                ),
                nativefmt=dict(
                    values=["binary"]
                ),
            ),
        ),
    ]
    

# %% Model outputs

@namebuilding_append('src', lambda self: [self.field, self.dim, self.filtering, 
                                          self.ppdate, self.source])
@namebuilding_append('geo', lambda self: [self.area])
class Hycom3dModelOutput(Analysis):
    """Model output"""

    _footprint = [
        dict(
            info="Model output",
            attr=dict(
                kind=dict(
                    values=["modelstate"],
                ),
                field=dict(
                    values=["ssh", "sss", "sst", "u", "v", "ubavg", "vbavg",
                            "h", "saln", "sigma", "temp", "tempis", "all",
                            "t", "s"],
                    optional=False,
                ),
                dim=dict(
                    values=["3D", "2D"],
                    type=str,
                    default="3D",
                ),
                ppdate=dict(
                     type=Date,
                     optional=True,
                ),
                filtering=dict(
                    values=["none", "mean", "demerliac", "godin", "spectral"],
                    type=str,
                    optional=True
                ),
                area=dict(
                    values=["MANGA", "BretagneSud"],
                    type=str,
                    optional=True,
                ),
                source=dict(
                    values=["hycom3d", "mercator"],
                    type=str,
                    optional=True
                ),
                nativefmt=dict(
                    values=["netcdf", "nc"],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_model_output"
