#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.executables import Script, SurfaceModel


class Safran(SurfaceModel):
    """Base class for the Safran model executables."""

    _abstract  = True
    _footprint = [
        dict(
            info = 'Safran module',
            attr = dict(
                model = dict(
                    values = ['safran'],
                ),
                gvar = dict(
                    optional = True,
                    default = '[kind]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'safran_module'

    def command_line(self, **opts):
        return ''


class Safrane(Safran):
    """Base class for the Safrane executable."""

    _footprint = [
        dict(
            info = 'Safrane executable',
            attr = dict(
                kind = dict(
                    values = ['safrane']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'safrane'


class Syrpluie(Safran):
    """Base class for the Syrpluie executable."""

    _footprint = [
        dict(
            info = 'Syrpluie executable',
            attr = dict(
                kind = dict(
                    values = ['syrpluie']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'syrpluie'


class Syrmrr(Safran):
    """Base class for the Syrmrr executable."""

    _footprint = [
        dict(
            info = 'Syrmrr executable',
            attr = dict(
                kind = dict(
                    values = ['syrmrr']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'syrmrr'


class Sytist(Safran):
    """Base class for the Sytist executable."""

    _footprint = [
        dict(
            info = 'Sytist executable',
            attr = dict(
                kind = dict(
                    values = ['sytist']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'sytist'


class Syvapr(Safran):
    """Base class for the Sytist executable."""

    _footprint = [
        dict(
            info = 'Syvapr executable',
            attr = dict(
                kind = dict(
                    values = ['syvapr']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'syvapr'


class Syrper(Safran):
    """Base class for the Sytist executable."""

    _footprint = [
        dict(
            info = 'Syrper executable',
            attr = dict(
                kind = dict(
                    values = ['syrper']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'syrper'


class Syvafi(Safran):
    """Base class for the Sytist executable."""

    _footprint = [
        dict(
            info = 'Syvafi executable',
            attr = dict(
                kind = dict(
                    values = ['syvafi']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'syvafi'


class Sypluie(Safran):
    """Base class for the Sytist executable."""

    _footprint = [
        dict(
            info = 'Sypluie executable',
            attr = dict(
                kind = dict(
                    values = ['sypluie']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'sypluie'


class SafranGribFiltering(Script):
    """Base class for the creation of P files used by SAFRAN."""

    _footprint = [
        dict(
            info = 'Prepare the input files for SAFRAN',
            attr = dict(
                kind = dict(
                    values = ['s2m_filtering_grib']
                ),
                cpl_vconf = dict(
                    values = ['pearp', 'pearome', 'arpege', 'arome'],
                    optional = True,
                ),
                gvar = dict(
                    optional = True,
                    default = '[kind]',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'gribfiltering'
