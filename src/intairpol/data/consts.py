#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

from common.data.consts import GenvModelResource
from vortex.data.outflow import StaticResource
from vortex.data.contents import JsonDictContent

#: No automatic export
__all__ = []


class StaticSurfaceEmissions(GenvModelResource):
    """
    Emissions files collected by international community.
    """
    _footprint = dict(
        info='Emissions files for sumo',
        attr=dict(
            kind=dict(
                values=['emiss_cst'],
            ),
            gvar=dict(
                default='surface_emissions_files'
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


class CfcScenario(GenvModelResource):
    """
     Fire constant file
    """
    _footprint = dict(
        info = 'Initial CFC concentration clim file',
        attr = dict(
            kind = dict(
                values = ['cfc_scenario'],
            ),
            gvar = dict(
                default = 'scenario_cfc'
            ),
        )
    )

    @property
    def realkind(self):
        return 'cfc_scenario'


class TopScenario(GenvModelResource):
    """
    Top model scenario.
    """
    _footprint = dict(
        info = 'Top model scenario',
        attr = dict(
            kind = dict(
                values  = ['top_scenario'],
            ),
            gvar = dict(
                default = 'scenario_topmodel'
            ),
        )
    )

    @property
    def realkind(self):
        return 'top_scenario'


class HybridLevels(GenvModelResource):
    """
    Hybrid levels description.
    """
    _footprint = dict(
        info='Hybrid levels',
        attr=dict(
            kind=dict(
                values=['hybrid_levels'],
            ),
            gvar=dict(
                default = 'lev_hybrid'
            ),
        )
    )

    @property
    def realkind(self):
        return 'hybrid_levels'


class SurfaceEmissionsProfilesTable(GenvModelResource):
    """
    Emissions profiles table.
    """
    _footprint = dict(
        info='Surface Emissions profiles table',
        attr=dict(
            kind=dict(
                values=['emiss_table'],
            ),
            gvar=dict(
                default='profilestable_surface'
            ),
        )
    )

    @property
    def realkind(self):
        return 'emiss_table'


class JsonConfig(GenvModelResource):
    """
    JSON Config File (used for assimilation in mocage)
    """
    _footprint = dict(
        info='JSON config file',
        attr=dict(
            kind=dict(
                values=['json_config'],
            ),
            gvar=dict(
                default='assimilation_config',
                optional=True,
            ),
            nativefmt=dict(
                values=['json',],
                default='json',
                optional=True,
            ),
            clscontents=dict(
                default=JsonDictContent,
                optional=True,
            )
        ),
    )

    @property
    def realkind(self):
        return 'assimilation_config'

        
class PalmConfig(GenvModelResource):
    """
    Compiled file for Open Palm coupler
    """
    _footprint = dict(
        info='Compiled file for Open Palm coupler',
        attr=dict(
            kind=dict(
                values=['palm_config'],
            ),
            gvar=dict(
                default='palm_config',
                optional=True,
            ),
            nativefmt=dict(
                values=['ascii',],
                default='ascii',
                optional=True,
            ),
        ),
    )

    @property
    def realkind(self):
        return 'palm_config'
            
