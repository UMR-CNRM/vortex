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
            )
        ),
    )


# %% Parameters

class Hycom3dConsts(_Hycom3dGeoResource):

    _footprint = dict(
        info="Hycom3d constant tar file",
        attr=dict(
            kind=dict(values=["hycom3d_consts"]),
            gvar=dict(default="hycom3d_consts_tar"),
            rank=dict(default=0, type=int, optional=True),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_consts"


# %% Binaries


class Hycom3dIBCIniconBinary(vde.Binary):
    """Binary that computes initial condictions for HYCOM"""

    _footprint = [
        gvar,
        #        hgeometry_deco,
        dict(
            info="Binary that computes initial condictions for HYCOM",
            attr=dict(
                gvar=dict(default="hycom3d_master_ibc_inicon"),
                kind=dict(values=["hycom3d_ibc_inicon_binary"],),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_inicon_binary"


class Hycom3dIBCRegridcdfBinary(vde.Binary):
    """Binary that regrids initial conditions netcdf files"""

    _footprint = [
        gvar,
        #        hgeometry_deco,
        dict(
            info="Binary that regrids initial conditions netcdf files",
            attr=dict(
                gvar=dict(default="hycom3d_master_ibc_regridcdf"),
                kind=dict(values=["hycom3d_ibc_regridcdf_binary"],),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_regridcdf_binary"


class Hycom3dModelBinary(vde.Binary):
    """Binary of the 3d model"""

    _footprint = [
        dict(
            info = "Binary of the model",
            attr = dict(
                kind = dict(
                    values = ['hycom3d_model'],
                ),
                nativefmt = dict(
                    values  = ['binary'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'hycom3d_model'


# %% Model inputs

class Hycom3dRiversInput(GeoFlowResource):
    _footprint = [
        dict(
            info = 'Rivers input',
            attr = dict(
                kind = dict(
                    values = ["RiversIn"],
                ),
                model=dict(
                    values=["cmems"],
                ),
                nativefmt = dict(
                    values  = ['tar.gz.tmp','unknown'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'riversinput'


class Hycom3dRiversr(Resource):
    _footprint = [
        dict(
            info = 'Hycom Rivers (*.r) Files',
            attr = dict(
                kind = dict(
                    values = ['RiversOut'],
                ),
                nativefmt = dict(
                    values  = ['r','unknown'],
                    default = 'unknown'
                ),
                rivers       = dict(
                    optional = True,
                    default = 'unknown'
                ),
            )
        )
    ]


    @property
    def realkind(self):
        return f'{self.rivers}'


class HycomAtmFrcOuta(Resource):
    _footprint = [
        dict(
            info = "Hycom Atmospheric Forcing 'a' Files",
            attr = dict(
                kind = dict(
                    values = ['ForcingOut'],
                ),
                nativefmt = dict(
                    values  = ['binary','a','unknown'],
                    default = 'unknown'
                ),
                fields       = dict(
                    values = ['shwflx', 'radflx',
                                    'precip', 'preatm', 'airtmp',
                                    'wndspd', 'tauewd', 'taunwd', 'vapmix'],
                    default = 'unknown'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return f'forcing.{self.fields}'


class HycomAtmFrcOutb(Resource):
    _footprint = [
        dict(
            info = "Hycom Atmospheric Forcing 'b' Files",
            attr = dict(
                kind = dict(
                    values = ['ForcingOut'],
                ),
                nativefmt = dict(
                    values  = ['ascii','b','unknown'],
                    default = 'b'
                ),
                fields       = dict(
                    values = ['shwflx', 'radflx',
                                    'precip', 'preatm', 'airtmp',
                                    'wndspd', 'tauewd', 'taunwd', 'vapmix'],
                    default = 'unknown'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return f'forcing.{self.fields}'


class Hycom3dMaskInterpWeights(_Hycom3dGeoResource):
    _footprint = dict(
        info="Hycom3d mask interpolation weights nc file",
        attr=dict(
            kind=dict(values=["mask_interp_weights"]),
            nativefmt=dict(values=['nc']),
        ),
    )

    @property
    def realkind(self):
        return "mask_interp_weights"


class Hycom3dAtmFrcInterpWeights(_Hycom3dGeoResource):
    _footprint = dict(
        info="Hycom3d atmospheric forcing interpolation weights nc file",
        attr=dict(
            kind=dict(values=["atmfrc_interp_weights"]),
            nativefmt=dict(values=['nc']),
        ),
    )

    @property
    def realkind(self):
        return "atmfrc_interp_weights"


# %% Model outputs
class Hycom3dModelOutput(_Hycom3dGeoResource):
    """Model output"""

    _footprint = [
        #        hgeometry_deco,
        dict(
            info="Model output",
            attr=dict(
                kind=dict(values=["hycom3d_model_output"],),
                domain=dict(type=str, default="3D"),
                cutoff=dict(
                    values=["production", "assim", "spnudge"],
                    default="production"
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_model_output"


