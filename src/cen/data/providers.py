#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from gco.data.providers import GEnv


class CenGEnvProvider(GEnv):
    """Almost identical to base, except for the specific netloc value."""

    _footprint = dict(
        info = 'GCO provider in CEN context',
        attr = dict(
            gnamespace = dict(
                values = ['cengco.cache.fr'],
                default = 'cengco.cache.fr',
            ),
        )
    )
