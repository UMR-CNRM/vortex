#/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hycom3d files
"""

import vortex.data.executables as vde
from gco.syntax.stdattrs import gvar

from common.data.consts import GenvModelGeoResource
from vortex.data.executables import Script, Binary, OceanographicModel
from vortex.data.geometries import hgeometry_deco
from vortex.data.resources import Resource
from vortex.data.flow import GeoFlowResource
from vortex.syntax.stddeco import namebuilding_append, namebuilding_insert
from vortex.syntax.stdattrs import model_deco

__all__ = []
# %% Generic

class _Hycom3dGeoResource(GenvModelGeoResource):

    _abstract = True
    _footprint = dict(
        attr=dict(
            model=dict(
                info="The model name (from a source code perspective).",
                alias=("turtle",),
                optional=False,
                values=["hycom3d"],
                default="hycom3d",
            ),
        ),
    )


# %% Parameters

class Hycom3dConsts(_Hycom3dGeoResource):

    _footprint = dict(
        info="Hycom3d constant tar file",
        attr=dict(
            kind=dict(
                values=["hycom3d_consts"],
            ),
            gvar=dict(
                default="hycom3d_consts_tar",
            ),
            rank=dict(
                default=0,
                type=int,
                optional=True
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_consts"


@namebuilding_append('src', lambda self: self.grids)
class Hycom3dAtmFrcInterpWeights(Resource):

    _footprint = [
        dict(
            info="Hycom3d atmfrc interpolation weights nc file",
            attr=dict(
                kind=dict(
                    values=["interp_weights"],
                ),
                nativefmt=dict(
                    values=['netcdf','nc'],
                ),
                grids=dict(
                    values=["atmfrc2hycom3d","mask2hycom3d"],
                    optional=False,
                    default='atmfrc2hycom3d',
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return "interp_weights"


# %% Binaries


class Hycom3dIBCRegridcdfBinary(Binary):
    """Binary that regrids initial conditions netcdf files"""

    _footprint = [
        gvar,
        #        hgeometry_deco,
        dict(
            info="Binary that regrids initial conditions netcdf files",
            attr=dict(
                gvar=dict(
                    default="hycom3d_ibc_regridcdf_binary",
                ),
                kind=dict(
                    values=["horizontal_regridder"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_regridcdf_binary"

    def command_line(self, **opts):
        varname = opts["varname"]
        method = opts.get("method", 0)
        cstep = int(opts.get("cstep", 1))
        return f"{varname} {method} {cstep:03d}"


class Hycom3dIBCIniconBinary(Binary):
    """Binary that computes initial condictions for HYCOM"""

    _footprint = [
        gvar,
        dict(
            info="Binary that computes initial conditions for HYCOM",
            attr=dict(
                gvar=dict(
                    default="hycom3d_ibc_inicon_binary",
                ),
                kind=dict(
                    values=["vertical_regridder"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_inicon_binary"

    def command_line(self, **opts):
        return ("{datadir} {sshfile} {tempfile} {salnfile} "
                "{nx} {ny} {nz} {cmoy} "
                "{sshmin} {cstep}").format(**opts)


class Hycom3dModelBinary(OceanographicModel):
    """Binary of the 3d model"""

    _footprint = [
        gvar,
        dict(
            info="Binary of the model",
            attr= dict(
                gvar = dict(
                    default='hycom3d_model_binary',
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'hycom3d_model_binary'

    def command_line(self, **opts):
        return ("{datadir} {tmpdir} {localdir} {rank}").format(**opts)


# %% Task-specific executable scripts

class Hycom3dIBCTimeScript(Script):

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_ibc_time_script"]))
        )

    def command_line(self, **opts):
        return "--ncout {ncout} {ncins} {dates}".format(**opts)


# %% Pre-processing intermediate files

@namebuilding_append('geo', lambda self: self.field)
class Hycom3dRegridcdfOutputFile(GeoFlowResource):

    _footprint = [
        dict(
            info="Single variable netcdf file created by regridcdf",
            attr=dict(
                kind=dict(
                    values=["boundary"],
                ),
                field=dict(
                    values=["saln", "temp", "thdd", "vaisa", "ssh"],
                ),
                nativefmt=dict(
                    values=["netcdf", "nc"],
                    default="netcdf",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_regridcdf_output"


# %% Model inputs

@namebuilding_append('src', lambda self: self.fields)
class Hycom3dAtmFrcInputFiles(Resource):
    """Atmospheric forcing input files for the Hycom3d model"""

    _footprint = [
        dict(
            info="Hycom Atmospheric Forcing Input Files",
            attr=dict(
                kind=dict(
                    values=['gridpoint', 'hycom3d_atmfrc_input']
                ),
                fields=dict(
                    values=['shwflx','radflx','precip','preatm','airtmp',
                            'wndspd','tauewd','taunwd','vapmix'],
                ),
                format=dict(values=["a", "b", "nc"]),
                nativefmt=dict(
                    values=["binary", "ascii", "netcdf"],
                    remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
                ),
                actualfmt=dict(
                    values=["binary", "ascii", "netcdf"],
                    remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'hycom3d_atmfrc_input'


@namebuilding_append('src', lambda self: self.rivers)
class Hycom3dRiversInputFiles(Resource):
    """Rivers input files for the Hycom3d model"""

    _footprint = [
        dict(
            info='Hycom Rivers Files',
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
        return 'hycom3d_rivers_input'


@namebuilding_append('geo', lambda self: self.field)
class Hycom3dIBCField(GeoFlowResource):
    _footprint = [
        dict(
            info="Single variable IBC .a and .b files",
            attr=dict(
                kind=dict(
                    values=["boundary"],
                ),
                field=dict(
                    values=["s", "t", "u", "v", "h"],
                ),
                format=dict(values=["a", "b"]),
                nativefmt=dict(
                    values=["binary", "ascii"],
                    remap={"a": "binary", "b": "ascii"}
                ),
                actualfmt=dict(
                    values=["binary", "ascii"],
                    remap={"a": "binary", "b": "ascii"}
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_field"


@namebuilding_append('geo', lambda self: self.field)
class Hycom3dRestartField(GeoFlowResource):

    _footprint = [
        dict(
            info="Single variable netcdf and restart file created by inicon",
            attr=dict(
                kind=dict(
                    values=["boundary"],
                ),
                field=dict(
                    values=["saln", "temp", "th3d", "u", "v", "h", "dpmixl"],
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

    @property
    def realkind(self):
        return "hycom3d_restart_field"


@namebuilding_append('geo', lambda self: "rest_new_head")
class Hycom3dRestartDate(GeoFlowResource):

    _footprint = [
        dict(
            info="Restart date in a binary file",
            attr=dict(
                kind=dict(
                    values=["restart_date"],
                ),
                format=dict(
                    values=["binary"]
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_restart_date"


# %% Model outputs
class Hycom3dModelOutput(_Hycom3dGeoResource):
    """Model output"""

    _footprint = [
        dict(
            info="Model output",
            attr=dict(
                kind=dict(
                    values=["gridpoint"],
                ),
                domain=dict(
                    values=["3D", "2D"],
                    type=str,
                    default="3D",
                ),
                cutoff=dict(
                    values=["production", "assim", "spnudge"],
                    default="production",
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_model_output"


