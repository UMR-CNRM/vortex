#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

from vortex.syntax.stdattrs import month
from common.data.consts import GenvModelResource
from common.data.climfiles import GenericClim

#: No automatic export
__all__ = []


class ChemicalBackup(GenvModelResource):
    """
    Pseudo-climatological file for chemical boundary conditions.
    Backup values for missing values.
    """
    _footprint = dict(
        info = 'Climatological backup for chemical boundary conditions',
        attr = dict(
            kind = dict(
                values   = ['chemical_bkup'],
            ),
            gvar = dict(
                default  = 'cams_bc_backup'
            ),
            nativefmt = dict(
                optional = True,
                default  = 'netcdf',
            )
        )
    )

    @property
    def realkind(self):
        return 'chemical_bkup'


class MonthClimMisc(GenericClim):
    """
     Monthly miscellaneous climatological files
    """
    _footprint = [
        month,
        dict(
            info = 'Monthly climatological files',
            attr = dict(
                kind = dict(
                    values  = ['clim_misc'],
                ),
                gvar = dict(
                    default = 'clim_[model]_[source]'
                ),
                source = dict(
                    type =str,
                ),
                 model = dict(
                    values  = ['mocage'],
                    default = 'mocage',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'clim_misc'
