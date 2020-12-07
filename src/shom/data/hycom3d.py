#/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hycom3d files
"""

import vortex.data.executables as vde
from gco.syntax.stdattrs import gvar

from common.data.consts import GenvModelGeoResource
from vortex.data.geometries import hgeometry_deco
from vortex.data.resources import Resource
from vortex.data.flow import GeoFlowResource
from vortex.syntax.stddeco import namebuilding_append
# vortex.syntax.stdattrs.models


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


class Hycom3dMaskInterpWeights(Resource):
    _footprint = dict(
        info="Hycom3d mask interpolation weights nc file",
        attr=dict(
            kind=dict(
                values=["mask_interp_weights"],
            ),
            nativefmt=dict(
                values=['nc'],
            ),
        ),
    )

    @property
    def realkind(self):
        return "mask_interp_weights"


class Hycom3dAtmFrcInterpWeights(Resource):
    _footprint = dict(
        info="Hycom3d atmospheric forcing interpolation weights nc file",
        attr=dict(
            kind=dict(
                values=["atmfrc_interp_weights"],
            ),
            nativefmt=dict(
                values=['nc'],
            ),
        ),
    )

    @property
    def realkind(self):
        return "atmfrc_interp_weights"

# %% Binaries


class Hycom3dIBCRegridcdfBinary(vde.Binary):
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
                    values=["hycom3d_ibc_regridcdf_binary"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_regridcdf_binary"

    def command_line(self, **opts):
        varname = opts["varname"]
        method = opts.get("methode", 0)
        cstep = int(opts.get("cstep", 1))
        return f"{varname} {method} {cstep:03d}"


class Hycom3dIBCIniconBinary(vde.Binary):
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
                    values=["hycom3d_ibc_inicon_binary"],
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


class Hycom3dModelBinary(vde.Binary):
    """Binary of the 3d model"""

    _footprint = [
        gvar,
        dict(
            info="Binary of the model",
            attr= dict(
                gvar = dict(
                    default='hycom3d_model_binary',
                ),
                kind = dict(
                    values=['hycom3d_model_binary'],
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'hycom3d_model_binary'


# %% Pre-processing intermediate files

@namebuilding_append('geo', lambda self: self.field)
class Hycom3dRegridcdfOutputFile(GeoFlowResource):

    _footprint = [
        dict(
            info="Single variable netcdf file created by regridcdf",
            attr=dict(
                kind=dict(
                    values=["hycom3d_regridcdf_output"],
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

@namebuilding_append('src', lambda self: self.rivers)
class Hycom3dRiversIn(Resource):
    """Rivers input '.r' files for the Hycom3d model"""

    _footprint = [
        dict(
            info='Hycom Rivers (*.r) Files',
            attr=dict(
                kind=dict(
                    values = ['RiversIn'],
                ),
                nativefmt=dict(
                    values=['r','unknown'],
                    default='unknown',
                ),
                rivers=dict(
                    optional=True,
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'rivers'


@namebuilding_append('src', lambda self: self.field)
class Hycom3dAtmFrcIn(Resource):
    """Atmospheric forcing input files for the Hycom3d model"""

    _footprint = [
        dict(
            info="Hycom Atmospheric Forcing Input Files",
            attr=dict(
                kind=dict(
                    values=['AtmFrcIn']
                ),
                field=dict(
                    default=['shwflx', 'radflx','precip', 'preatm',
                             'airtmp','wndspd', 'tauewd', 'taunwd','vapmix'],
                ),
                nativefmt=dict(
                    values=['a','b'],
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'atmfrc'


# class Hycom3dAtmFrcIna(Hycom3dAtmFrcIn):
#     """Atmospheric forcing input '.a' files for the Hycom3d model"""

#     _footprint = [
#         dict(
#             info="Hycom Atmospheric Forcing Input 'a' Files",
#             attr=dict(kind=dict(values=['AtmosphericForcingIna']),
#                       nativefmt=dict(values=['binary','a',], ),
#             ),
#         )
#     ]


# class Hycom3dAtmFrcInb(Hycom3dAtmFrcIn):
#     """Atmospheric forcing input '.b' files for the Hycom3d model"""

#     _footprint = [
#         dict(
#             info="Hycom Atmospheric Forcing Input 'b' Files",
#             attr=dict(kind=dict(values=['AtmosphericForcingInb']),
#                       nativefmt=dict(values=['ascii','b','unknown'], default='unknown'),
#             ),
#         )
#     ]


@namebuilding_append('geo', lambda self: self.field)
class Hycom3dIBCField(GeoFlowResource):
    _footprint = [
        dict(
            info="Single variable IBC .a and .b files",
            attr=dict(
                kind=dict(
                    values=["gridpoint"],
                ),
                field=dict(
                    values=["s", "t", "u", "v", "h"],
                ),
                format=dict(values=["a", "b"]),
                nativefmt=dict(values=["a", "b"]),
                # actualfmt=dict(values=["a", "b"]),
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
                    values=["gridpoint"],
                ),
                field=dict(
                    values=["saln", "temp", "th3d", "u", "v", "h", "dpmixl"],
                ),
                format=dict(
                    values=["cdf", "res"]
                    ),
                nativefmt=dict(
                    values=["cdf", "res"],
                ),
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
                    values=["hycom3d_model_output"],
                ),
                domain=dict(
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


