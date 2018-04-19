#!/usr/bin/env python
# -*- coding: utf-8 -*-

from common.data.consts import GenvModelResource

#: No automatic export
__all__ = []


class StaticSurfaceEmissions(GenvModelResource):
    """
    Emissions files collected by international community.
    """
    _footprint = dict(
        info = 'Emissions files for sumo',
        attr = dict(
            kind = dict(
                values  = ['emiss_cst'],
            ),
            gvar = dict(
                default = 'surface_emissions_files'
            ),
        )
    )

    @property
    def realkind(self):
        return 'emiss_cst'


class Regrid(GenvModelResource):
    """
    Parameters for mocage grid transformation from 0.2 to 0.1 degree.
    """
    _footprint = dict(
        info = 'Parameters for mocage grid transformation',
        attr = dict(
            kind = dict(
                values  = ['regrid'],
            ),
            gvar = dict(
                default = 'regrid02to01'
            ),
        )
    )

    @property
    def realkind(self):
        return 'regrid'


class GribTemplate(GenvModelResource):
    """
    File constant for macc/mocage forecast.
    """
    _footprint = dict(
        info = 'Grib template for mocage forecast',
        attr = dict(
            kind = dict(
                values   = ['gribtpl'],
            ),
            edition = dict(
                optional = True,
                default  = 2,
            ),
            gvar = dict(
                default  = 'gribtpl_cams'
            ),
        )
    )

    @property
    def realkind(self):
        return 'gribtpl'


class ChemicalSurfaceScheme(GenvModelResource):
    """
     Chemical surface scheme.
    """
    _footprint = dict(
        info = 'Chemical surface scheme',
        attr = dict(
            kind = dict(
                values  = ['chemical_surf'],
            ),
            gvar=dict(
                default = 'table_chemscheme_surf'
            ),
        )
    )

    @property
    def realkind(self):
        return 'chemicalsurf'


class FireCst(GenvModelResource):
    """
     Fire constant file
    """
    _footprint = dict(
        info = 'Fire constant file',
        attr = dict(
            kind = dict(
                values  = ['firecst'],
            ),
            gvar = dict(
                default = 'config_fires'
            ),
        )
    )

    @property
    def realkind(self):
        return 'firecst'
