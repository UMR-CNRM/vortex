# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from gco.syntax.stdattrs import gdomain

from common.data.consts import GenvModelResource

from vortex.data.outflow import ModelResource

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class AlphaElevation(GenvModelResource):
    """Some kind of elevation data for ALPHA.

    A Genvkey can be given.
    """
    _footprint = [
        gdomain,
        dict(
            info = 'Some kind of elevation data for ALPHA.',
            attr = dict(
                kind = dict(
                    values  = ['elevation']
                ),
                format = dict(
                    values  = ['grib']
                ),
                gvar = dict(
                    default = 'ALPHA_RELIEF_CONSTANT_[gdomain]',
                ),
                model = dict(
                    values  = ['alpha']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'relief'


class AlphaConfig(GenvModelResource):
    """Some kind configuration file for ALPHA.

    A Genvkey can be given.
    """
    _footprint = [
        dict(
            info = 'Some kind configuration file for ALPHA.',
            attr = dict(
                kind = dict(
                    values  = ['config']
                ),
                format = dict(
                    values  = ['json']
                ),
                gvar = dict(
                    default = 'ALPHA_CONF_MOD_[vconf]',
                ),
                model = dict(
                    values  = ['alpha']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'config'


class AlphaVersion(GenvModelResource):
    """Some kind configuration file for ALPHA.

    A Genvkey can be given.
    """
    _footprint = [
        dict(
            info = 'Some kind configuration file for ALPHA.',
            attr = dict(
                kind = dict(
                    values  = ['version']
                ),
                format = dict(
                    values  = ['ini']
                ),
                gvar = dict(
                    default = 'ALPHA_CONF_VERSION',
                ),
                model = dict(
                    values  = ['alpha']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'version'


