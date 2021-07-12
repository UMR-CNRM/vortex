# -*- coding: utf-8 -*-
"""
Hycom3d files.
"""

from bronx.stdtypes.date import Date
from vortex.data.flow import FlowResource
from common.data.modelstates import Analysis, InitialCondition
from vortex.data.flow import GeoFlowResource
# from vortex.data.outflow import StaticGeoResource
from vortex.syntax.stddeco import namebuilding_append

__all__ = []


class CmemsRivers(FlowResource):
    """Rivers file from cmems in 'tar' format."""

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

# Note LFM: This is un-acceptable & and won't enter an official branch.
#           In the "HycomAtmFrc" operational task, this resource is fetch,
#           then archived. Since it has no date/cutoff attributes it overwrites
#           itself from one day to another

# @namebuilding_append('src', lambda self: self.grids)
# class Hycom3dAtmFrcInterpWeights(StaticGeoResource):
#     """TODO Class Documentation."""
#
#     _footprint = [
#         dict(
#             info="Hycom3d atmfrc interpolation weights nc file",
#             attr=dict(
#                 kind=dict(values=["interp_weights"]),
#                 nativefmt=dict(values=['netcdf','nc']),
#                 grids=dict(values=["a2o","o2a"], optional=False, default='a2o'),
#             ),
#         )
#     ]
#
#     @property
#     def realkind(self):
#         return self.kind


# %% Pre-processing intermediate files

@namebuilding_append('geo', lambda self: [self.field, self.interp])
class Hycom3dInterpOutput(GeoFlowResource):
    """TODO Class Documentation."""

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


# %% Model inputs

@namebuilding_append('src', lambda self: self.field)
class Hycom3dModelInput(GeoFlowResource):
    """Hycom3d model input."""

    _footprint = dict(
        info="Model Input .a and .b files",
        attr=dict(
            kind=dict(
                values=["gridpoint"],
            ),
            field=dict(
                values=["s", "t", "h", "rmu", "u", "v",
                        'shwflx', 'radflx', 'precip', 'preatm', 'airtmp',
                        'wndspd', 'tauewd', 'taunwd', 'vapmix']
            ),
            nativefmt=dict(
                values=["a", "b", "nc", "binary", "ascii", "netcdf"],
                remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
            ),
            model=dict(
                values=["hycom3d"],
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_model_input"


class Hycom3dRiversModelInput(Hycom3dModelInput):
    """Rivers input files for the Hycom3d model."""

    _footprint = dict(
        info='Hycom3d rivers input files',
        attr=dict(
            kind=dict(
                values = ['observations'],
            ),
            field=dict(
                values=["Adour", "Gironde", "Loire", "Seine",
                        "Rhone", "Nile", "Po", "Ebro", "Marma"],
            ),
            nativefmt=dict(
                values=['r', 'nc', "ascii", "netcdf"],
                remap={'r': 'ascii', 'nc': 'netcdf'}
            ),
        ),
    )


# %% Initial conditions

@namebuilding_append('src', lambda self: self.field)
class Hycom3dInitialCondition(InitialCondition):

    _footprint = dict(
        info="Single variable netcdf and restart file created by inicon",
        attr=dict(
            field=dict(
                values=["saln", "temp", "th3d", "u", "v", "ut", "vt",
                        "h", "dpmixl", "restdate"],
            ),
            nativefmt=dict(
                remap={"cdf": "netcdf", "res": "binary"},
                values=["cdf", "res", "netcdf", "binary"],
            ),
            model=dict(
                values=["hycom3d"],
            ),
        ),
    )


# %% Model outputs

@namebuilding_append('src', lambda self: [self.field, self.dim])
# Note LFM: self.area (and others) may not be defined (it is optional) consequently
# none_discard=True needs to be define to avoid crashes
@namebuilding_append('src', lambda self: [self.filtering, self.ppdate, self.source, self.interp],
                     none_discard=True)
@namebuilding_append('geo', lambda self: [self.area], none_discard=True)
class Hycom3dModelOutput(Analysis):
    """Model output."""

    _footprint = dict(
        info="Model output",
        attr=dict(
            kind=dict(
                values=["modelstate"],
            ),
            field=dict(
                values=["ssh", "sss", "sst", "u", "v", "ubavg", "vbavg",
                        "h", "saln", "sigma", "temp", "tempis", "all",
                        "t", "s"],
            ),
            dim=dict(
                values=["3D", "2D"],
                default="3D",
            ),
            ppdate=dict(
                type=Date,
                optional=True,
            ),
            filtering=dict(
                values=["none", "mean", "demerliac", "godin", "spectral"],
                optional=True
            ),
            interp=dict(
                values=["zlevel"],
                optional=True
            ),
            area=dict(
                # Note LFM: There is already a geometry attribute. Consequently the area
                #           attribute makes no sense to me (and should not exists).
                values=["MANGA", "BretagneSud"],
                optional=True,
            ),
            source=dict(
                values=["hycom3d", "mercator"],
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

    @property
    def realkind(self):
        return "hycom3d_model_output"
