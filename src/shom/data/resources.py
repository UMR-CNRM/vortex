"""
Hycom3d files.
"""

from vortex.data.flow import FlowResource, GeoFlowResource
from vortex.syntax.stddeco import namebuilding_append
from vortex.syntax.stdattrs import term_deco
from common.data.modelstates import InitialCondition, Analysis3D

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
        return "interp"


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
            format=dict(
                values=["a", "b", "nc"],
            ),
            model=dict(
                values=["hycom3d"],
            ),
        ),
    )

    @property
    def realkind(self):
        return "model_input"


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
                        "Rhone", "Nile", "Po", "Ebro", "Marma",
                        "Narmada", "Indus", "Shatt-al-Arab"],
            ),
            nativefmt=dict(
                values=['r', 'nc', 'ascii', 'netcdf'],
                remap={'r': 'ascii', 'nc': 'netcdf'}
            ),
            format=dict(
                values=['r', 'nc'],
            ),
            model=dict(
                values=["hycom3d"],
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
                        "h", "dpmixl", "restdate", "umbbiais", "vmbbiais", "ptide"],
            ),
            nativefmt=dict(
                remap={"cdf": "netcdf", "res": "binary"},
                values=["cdf", "res", "netcdf", "binary"],
            ),
            format=dict(
                values=["cdf", "res", "binary"],
            ),
            model=dict(
                values=["hycom3d"],
            ),
        ),
    )


# %% Model outputs

@namebuilding_append('src', lambda self: [self.field, self.filtering])
@namebuilding_append('src', lambda self: [self.source, self.interp],
                     none_discard=True)
class Hycom3dModelOutput(Analysis3D):
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
            filling=dict(
                values=["3D", "2D"],
                default="3D",
            ),
            filtering=dict(
                values=["none", "mean", "demerliac", "godin", "spectral"],
                optional=True
            ),
            interp=dict(
                values=["zlevel"],
                optional=True
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


class Hycom3dPostprodOutput(Hycom3dModelOutput):
    """Postprod outputs."""

    _footprint = [
        term_deco,
        dict(
            info="Model output",
            attr=dict(
                kind=dict(
                    values=["postprod"],
                )
            )
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_output"
