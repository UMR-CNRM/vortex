# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import absolute_import, print_function, division, unicode_literals

from common.data.consts import GenvModelResource, GenvModelGeoResource

#: No automatic export
__all__ = []


class StaticSurfaceEmissions(GenvModelGeoResource):
    """Emissions files collected by international community."""

    _footprint = dict(
        info = 'Emissions files for sumo',
        attr = dict(
            kind = dict(
                values  = ['emiss_cst'],
            ),
            gvar = dict(
                default = 'surface_emissions_[geometry::area]'
            ),
        )
    )

    @property
    def realkind(self):
        return 'emiss_cst'


class Regrid(GenvModelResource):
    """Parameters for mocage grid transformation from 0.2 to 0.1 degree."""

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


class GribTemplate(GenvModelGeoResource):
    """File constant for mocage post."""

    _footprint = dict(
        info = 'Grib template for mocage post',
        attr = dict(
            kind = dict(
                values   = ['gribtpl'],
            ),
            edition = dict(
                optional = True,
                default  = 2,
            ),
            source = dict(
                values   = ['PREVAIR', 'CAMS'],
                default = 'PREVAIR',
                optional = True,
            ),
            gvar = dict(
                default  = 'GRIB_TEMPLATE_[source]_[geometry::area]'
            ),
        )
    )

    @property
    def realkind(self):
        return 'gribtpl'


class ChemicalSurfaceScheme(GenvModelResource):
    """Chemical surface scheme."""

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
    """Fire constant file."""

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
    """Fire constant file."""

    _footprint = dict(
        info = 'Initial CFC concentration clim file',
        attr = dict(
            kind = dict(
                values  = ['cfc_scenario'],
            ),
            gvar = dict(
                default = 'scenario_cfc'
            ),
        )
    )

    @property
    def realkind(self):
        return 'cfc_scenario'


class CfcScenarioComplement(CfcScenario):
    """WMO CFC Clim"""
    _footprint = dict(
        info = 'Initial CFC concentration clim file',
        attr = dict(
            kind = dict(
                values  = ['cfc_scenario_complement'],
            ),
            gvar = dict(
                default = 'scenario_cfc_complement'
            ),
        )
    )

    @property
    def realkind(self):
        return 'cfc_scenario_complement'


class TopScenario(GenvModelResource):
    """Top model scenario."""

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
    """Hybrid levels description."""

    _footprint = dict(
        info='Hybrid levels',
        attr=dict(
            kind=dict(
                values=['hybrid_levels'],
            ),
            gvar=dict(
                default='lev_hybrid'
            ),
        )
    )

    @property
    def realkind(self):
        return 'hybrid_levels'


class SurfaceEmissionsProfilesTable(GenvModelResource):
    """Emissions profiles table."""

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
