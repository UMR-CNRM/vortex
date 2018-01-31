#!/usr/bin/env python
# -*- coding: utf-8 -*-

from common.data.consts import GenvModelResource

#: No automatic export
__all__ = []


class EmisSumo(GenvModelResource):
    """
    Emissions files
    """
    _footprint = dict(
        info='Emissions files for sumo',
        attr=dict(
            kind=dict(
                values=['emissumo'],
            ),
            gvar=dict(
                default='mocage_emis_sumo02'
            ),
        )
    )

    @property
    def realkind(self):
        return 'emissumo'


class Regrid(GenvModelResource):
    """
    File constant for macc/mocage forecast
    """
    _footprint = dict(
        info='File constant for mocage forecast',
        attr=dict(
            kind=dict(
                values=['regrid'],
            ),
            gvar=dict(
                default='regrid_macc'
            ),
        )
    )

    @property
    def realkind(self):
        return 'regrid'


class Template(GenvModelResource):
    """
    File constant for macc/mocage forecast
    """
    _footprint = dict(
        info='Template file for mocage forecast',
        attr=dict(
            kind=dict(
                values=['template'],
            ),
            gvar=dict(
                default='template_mfm'
            ),
        )
    )

    @property
    def realkind(self):
        return 'template'


class ChemSurf(GenvModelResource):
    """
     Chemical surface scheme
    """
    _footprint = dict(
        info='Chemical surface scheme',
        attr=dict(
            kind=dict(
                values=['chemsurf'],
            ),
            gvar=dict(
                default='chemscheme_surf'
            ),
        )
    )

    @property
    def realkind(self):
        return 'chemsurf'


class FireCst(GenvModelResource):
    """
     Fire constant file - EN COURS DE DEV ne pas utiliser
    """
    _footprint = dict(
        info='Fire constant file',
        attr=dict(
            kind=dict(
                values=['firecst'],
            ),
            gvar=dict(
                default='auxi_sumo2_embb_macc'
            ),
        )
    )

    @property
    def realkind(self):
        return 'firecst'
