#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import re

from bronx.fancies import loggers

from common.data.consts import GenvModelResource

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class Relief(GenvModelResource):
    """
    A Genvkey can be given.
    """
    _footprint = [
        #gdomain,
        dict(
            info = 'My comment about this resource...',
            attr = dict(
                kind = dict(
                    values  = ['relief']
                ),
                format = dict(
                    values = ['grib']
                ),
                gvar = dict(
                    default = 'ALPHA_RELIEF_CONSTANT_[geometry]',
                ),
                model = dict(
                    values = ['alpha']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'relief'

class Directive(GenvModelResource):
    """
    A Genvkey can be given.
    """
    _footprint = [
        #gdomain,
        dict(
            info = 'My comment about this resource...',
            attr = dict(
                kind = dict(
                    values  = ['config']
                ),
                format = dict(
                    values = ['json']
                ),
                gvar = dict(
                    default = 'ALPHA_CONF_MOD_[vconf]',
                ),
                model = dict(
                    values = ['alpha']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'config'
