#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
from bronx.stdtypes.date import Date

from vortex.data.outflow import ModelResource
from gco.syntax.stdattrs import gvar, gdomain
from previmar.data.contents import SurgeTemplate
from common.data.namelists import Namelist
from vortex.data.contents import DataTemplate

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class BlkdatNamFiles(ModelResource):
    """TODO: Class documentation."""

    _footprint = [
        gvar,
        gdomain,
        dict(
            info = "blkdat ascii files. list to tweak",
            attr = dict(
                kind = dict(
                    values = ["blkdat_nam_file"],
                ),
                gvar = dict(
                    default = "[model]_blkdat_[param]_[gdomain]",
                ),
                param = dict(
                    values  = ['full_prv', 'full_ana', 'ms', 'red', 'full'],
                ),
                forcage = dict(
                    values   = ['aro', 'cep', 'arp', 'aoc', ],
                    optional = True,
                    default  = '',
                ),
                date = dict(
                    type     = Date,
                    optional = True,
                ),
                clscontents = dict(
                    default = SurgeTemplate
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "blkdat_nam_file"


class NamelistWW3(Namelist):
    """Namelists of pre- and postprocessing of WW3.

    :note: (LFM) The need for this new class is not obvious to me. Why is it not
           enough to use the bare Namelist class?
    """

    _footprint = dict(
        info = 'Namelist of pre- and postprocessing of WW3',
        attr = dict(
            kind = dict(
                values   = ['ww3nam', ],
            ),
            binary = dict(
                values   = ['ww3_prnc', 'ww3_bound', 'spectra_mfwam_to_ww3', 'ww3',
                            'ww3_ounf', 'ww3_ounp', 'ww3_ncgrb'],
                optional = False,
            ),
            model = dict(
                values   = ['ww3', ],
            ),
            gvar = dict(
                values   = ['NAMELIST_' + x.upper() for x in ['ww3', 'ww3_prnc', 'ww3_bound',
                            'spectra_mfwam_to_ww3', 'ww3_ounf', 'ww3_ounp', 'ww3_ncgrb']],
            ),
        )
    )

    @property
    def realkind(self):
        return "ww3_nam_file"


class WW3ConfigFiles(Namelist):
    """TODO: Class documentation.

    :note: (LFM) These files are not namelist but they inherit from `Namelist`.
           I don't see the logic behind this. An alternative would be
           `common.data.configfiles.AsciiConfig`
    """

    _footprint = dict(
        info = " list to tweak",
        attr = dict(
            kind = dict(
                values = ["ww3config"]
            ),
            model = dict(
                values   = ['ww3', ],
            ),
            clscontents = dict(
                default = DataTemplate
            ),
            binary = dict(
                values   = ['ww3_shel', 'ww3_ounf', 'ww3_ounp'],
                optional = False,
            ),
            gvar = dict(
                values   = ['NAMELIST_' + x.upper() for x in ['ww3_shel', 'ww3_ounf', 'ww3_ounp']],
            ),

        )
    )

    @property
    def realkind(self):
        return "ww3_config_file"
