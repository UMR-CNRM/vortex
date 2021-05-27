# -*- coding: utf-8 -*-
"""
Hycom3d files
"""

from bronx.stdtypes.date import Date
from vortex.data.flow import FlowResource
from common.data.modelstates import Analysis, InitialCondition
from vortex.data.flow import GeoFlowResource
from vortex.data.outflow import StaticGeoResource
from vortex.syntax.stddeco import namebuilding_append

__all__ = []


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
                    remap={"sal": "saln"},
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
                model=dict(
                    values=["hycom3d", "psy4"],
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
                            'wndspd','tauewd','taunwd','vapmix']
                ),
                nativefmt=dict(
                    values=["a", "b", "nc", "binary", "ascii", "netcdf"],
                    remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
                ),
                format=dict(
                    values=["a", "b", "nc"],
                ),
                model=dict(
                    values=["hycom3d"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_model_input"


class Hycom3dRiversModelInput(Hycom3dModelInput):
    """Rivers input files for the Hycom3d model"""

    _footprint = [
        dict(
            info='Hycom3d rivers input files',
            attr=dict(
                kind=dict(
                    values = ['observations'],
                ),
                field=dict(
                    values=["Adour", "Gironde", "Loire", "Seine",
                            "Rhone", "Nile", "Po", "Ebro", "Marma"],
                    optional=False,
                ),
                nativefmt=dict(
                    values=['r', 'nc', "ascii", "netcdf"],
                    remap={'r':'ascii','nc':'netcdf'}
                ),
                format=dict(
                    values=['r', 'nc'],
                ),
                model=dict(
                    values=["hycom3d"],
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
                            "h", "dpmixl", "restdate"],
                ),
                nativefmt=dict(
                    remap={"cdf": "netcdf", "res": "binary"},
                    values=["cdf", "res", "netcdf", "binary"],
                ),
                format=dict(
                    values=["cdf", "res", "netcdf", "binary"],
                    optional=True
                ),
                model=dict(
                    values=["hycom3d"],
                ), 
            ),
        ),
    ]


# %% Model outputs

@namebuilding_append('src', lambda self: [self.field, self.dim, self.filtering, 
                                          self.ppdate, self.source, self.interp])
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
                interp=dict(
                    values=["zlevel"],
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
                model=dict(
                    values=["hycom3d"],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_model_output"
