#!/usr/bin/env python
# -*- coding:Utf-8 -*-


"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import re

from bronx.fancies import loggers

from gco.syntax.stdattrs import gdomain
from common.data.consts import GenvModelResource
from vortex.data.contents import DataTemplate

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class GenvUsageModelResource(GenvModelResource):

    _abstract = True
    _footprint = dict(
        info = 'different use : model classic use for simulation or interpolation use '
               'for interpolation between grid of Hycom',
        attr = dict(
            usage = dict(
                values  = ['model', 'interpol'],
                optional = True,
            ),
        )
    )

    def genv_basename(self):
        """Just retrieve a potential gvar attribute + self.usage."""
        if self.usage is not None:
            if re.search('(_TGZ$)', self.gvar):
                usage_key = re.sub('(_TGZ$)', ('_' + self.usage + '_TGZ').upper(), self.gvar)
            else:
                usage_key = (self.gvar + '_' + self.usage).upper()
        else:
            usage_key = self.gvar
        return usage_key


class TidalHarmonic(GenvModelResource):
    """Class of Tidal Constant: Fortran binary data (unformatted).
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Set of tidal Harmonic, fortran binary data',
            attr = dict(
                kind = dict(
                    values  = ['coefMar']
                ),
                gvar = dict(
                    default = '[model]_forcing_tide_[gdomain]_tgz',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'coefMar'


class CteMaree(GenvModelResource):
    """Class of Tidal Characteristic: ascii list file.
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Tidal Characteristic',
            attr = dict(
                kind = dict(
                    values  = ['cteMaree']
                ),
                gvar = dict(
                    default  = '[model]_tide_list_[gdomain]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'cteMaree'


class SurgesNativeGrid(GenvModelResource):
    """
    Class of a grid  'depth' : grille bathy  ; 'grid' : grille modele ; 'angle' : angle local;
    on HYCOM curvilinear grid , Fortran binary data (unformatted) (*.a).
    & (Ascii file) min max values (*.b)
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Static grid forcing for a surges model and BottomFriction if variable',
            attr = dict(
                kind = dict(
                    values  = ['SurgesNativeGrid', 'SurgesForcingData', 'BottomFriction'],
                ),
                gvar = dict(
                    default = '[model]_[fields]_[gdomain]_tgz',
                ),
                fields = dict(
                    values  = ['regional', 'cb', 'cbar'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'NativeGrid'


class ConfSurges(GenvUsageModelResource):
    """Surges model static parameters on input file. (Ascii file).
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Surges model parameters files',
            attr = dict(
                kind = dict(
                    values  = ['ConfigSurges', 'ConfigRunSurges', 'BlkdatData'],
                ),
                gvar = dict(
                    default = '[model]_[param]_[gdomain]',
                ),
                param = dict(
                    values  = ['pts', 'savefield', 'ports', 'blkdat',
                               'blkdat_cmo', 'blkdat_shom', 'blkdat_ms', 'blkdat_full',
                               'patch', 'run', 'run_red'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ConfigSurges'


class BinProjSurges(GenvModelResource):
    """
    Interpolation factor file between Hycom curvilinear grid and MF regular grid
    format for BDAP archiving. Fortran binary data (unformatted).
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Interpolation factor file (from the surges model grid)',
            attr = dict(
                kind = dict(
                    values  = ['SurgesInterpFactor', 'BinHycomBdap']
                ),
                gvar = dict(
                    default  = '[model]_indices_mf_[gdomain]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'SurgesInterpFactor'


class ConfCouplingOasisSurges(GenvUsageModelResource):
    """Coupling description of OASIS between Hycom and WW3
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Coupling description of OASIS between Hycom and WW3, \
                    Mesh grid file description for ww3 model',
            attr = dict(
                kind = dict(
                    values  = ['meshWW3grid', 'ConfCouplingOasisSurges'],
                ),
                gvar = dict(
                    default = '[model]_[param]_[gdomain]',
                ),
                param = dict(
                    values  = ['namcouple', 'ww3_mesh', 'oasis_info'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ConfCouplingOasisSurges'


class CouplingGridOasis(GenvUsageModelResource):
    """Coupling grid file information for Oasis, for binaries coupled execution
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Coupling grid file information for Oasis, for binaries coupled execution',
            attr = dict(
                kind = dict(
                    values  = ['InterpWW3Model', 'CouplingGridOasis'],
                ),
                gvar = dict(
                    default = '[model]_[param]_[gdomain]_tgz',
                ),
                param = dict(
                    values  = ['grid', 'interpo'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'CouplingGridOasis'


class AltimetryPreproc(GenvModelResource):
    """Thresholds for altimeter preprocessing."""
    _footprint = dict(
        info = 'Thresholds for altimeter preprocessing',
        attr = dict(
            nativefmt = dict(
                values = ['ascii', 'foo', 'unknown'],
            ),
            kind = dict(
                values = ['preprocalti'],
            ),
            gvar = dict(
                default = '[model]_[fields]',
            ),
            fields = dict(
                values = ['filtrevalue', 'bathyref', 'fort_alti', 'cst_alti'],
                remap = {
                    'filtrevalue': 'fort_alti',
                    'bathyref': 'cst_alti',
                },
            )
        )
    )

    @property
    def realkind(self):
        return 'preprocalti'


class WamPreproc(GenvModelResource):
    """Constant files for MFWAM."""
    _footprint = dict(
        info = 'Constant files for MFWAM',
        attr = dict(
            nativefmt = dict(
                default = 'foo',
            ),
            kind = dict(
                values = ['wam_preproc'],
            ),
            gvar = dict(
                default = '[model]_preproc_tgz',
            ),
        )
    )

    @property
    def realkind(self):
        return 'wampreproc'


class WamGridPost(GenvModelResource):
    """Information on a grid for MFWAM post-processing."""
    _footprint = dict(
        info = 'Grid information for MFWAM post-processing',
        attr = dict(
            nativefmt = dict(
                default = 'foo',
            ),
            kind = dict(
                values = ['wam_grid_post'],
            ),
            gvar = dict(
                default = 'namelist_[model]_interp',
            ),
        )
    )

    @property
    def realkind(self):
        return 'wampreproc'

class WW3Preproc(GenvModelResource):
    """
    Class of a ww3 model constants
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'ww3 models const',
            attr = dict(
                kind = dict(
                    values  = ['ww3_preproc'],
                ),
                model = dict(
                    values  = ['ww3'],
                ),
                gvar = dict(
                    default = '[model]_preproc_tgz',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ww3preproc'

class InputConfWW3(GenvModelResource):
    """Config file for ww3 processes"""

    _footprint = dict(
        info = 'Config file for ww3',
        attr = dict(
            kind = dict(
                values = ['ww3dataconf']
            ),
            model = dict(
                values  = ['ww3'],
            ),
            binary = dict(
                values  = ['bound_ascii'],
                optional = False,
            ),
            field = dict(
                values  = ['const'],
                optional = False,
            ),
            gvar = dict(
                default  = '[field]_[model]_[binary]',
            ),
            clscontents = dict(
                default = DataTemplate
            ),

        )
    )
    @property
    def realkind(self):
        return 'inputconfww3'

class WW3InterpConst(GenvModelResource):
    """
    Class of a ww3 model results interpolation constant
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Interpolation constants',
            attr = dict(
                kind = dict(
                    values  = ['interpolateconst'],
                ),
                model = dict(
                    values  = ['ww3'],
                ),
                gvar = dict(
                    default = '[model]_interpolate_tgz',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'interpolateconst'

class WW3ConNctoGrib(GenvModelResource):
    """
    Class of a convertion from nc to grib constant
    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'convertion from nc to grib constant',
            attr = dict(
                kind = dict(
                    values  = ['const_ncgrb'],
                ),
                model = dict(
                    values  = ['ww3'],
                ),
                gvar = dict(
                    default = '[model]_nc_grb_tgz',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'const_ncgrb'

