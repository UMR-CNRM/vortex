#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)
from gco.syntax.stdattrs import gdomain

from common.data.consts import GenvModelResource


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


class SurgesForcingData(GenvModelResource):
    """
    Class of a grid  'depth' : grille mere  ; 'grid' : grille fille ; 'angle' : angle local;
    on HYCOM curvilinear grid , Fortran binary data (unformatted) (*.a).
    & (Ascii file) min max values (*.b)

    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Static forcing data for a surges model',
            attr = dict(
                kind = dict(
                    values  = ['SurgesForcingData']
                ),
                gvar = dict(
                    default = '[model]_regional_[gdomain]_tgz',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ForcingInData'


class BlkdatData(GenvModelResource):
    """
    Class of a grid  'depth' : grille mere  ; 'grid' : grille fille ; 'angle' : angle local;
    on HYCOM curvilinear grid , Fortran binary data (unformatted) (*.a).
    & (Ascii file) min max values (*.b)

    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Set of ...',
            attr = dict(
                kind = dict(
                    values  = ['BlkdatData']
                ),
                gvar = dict(
                    default = '[model]_blkdat_[gdomain]_tgz',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'BlkdatData'


class ConfSurgesModel(GenvModelResource):
    """Surges model static parameters file. (Ascii file).

    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Surges model parameters files',
            attr = dict(
                kind = dict(
                    values  = ['ConfigSurges'],
                ),
                gvar = dict(
                    default = '[model]_[param]_[gdomain]',
                ),
                param = dict(
                    values  = ['pts', 'savefield', 'ports', 'patch'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ConfigSurgesModel'


class ConfRunSurgesModel(GenvModelResource):
    """Surges model run input for forecast and restart. (Ascii file).

    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Surges model run input for forecast and restart',
            attr = dict(
                kind = dict(
                    values  = ['ConfigRunSurges'],
                ),
                gvar = dict(
                    default = '[model]_run_[gdomain]_tgz',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'ConfigSurgesModel'


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
                    values  = ['BinHycomBdap']
                ),
                gvar = dict(
                    default  = '[model]_indices_mf_[gdomain]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'BinHycomBdap'


class CbData(GenvModelResource):
    """Bottom Friction file (fortran binary data) on HYCOM curvilinear grid.

    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Bottom Friction file on HYCOM curvilinear grid',
            attr = dict(
                kind = dict(
                    values  = ['BottomFriction']
                ),
                gvar = dict(
                    default = '[model]_cb_[gdomain]_tgz',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'BottomFriction'