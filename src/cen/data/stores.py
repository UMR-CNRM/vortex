#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.stores     import Store, Finder
from vortex.syntax.stdattrs import DelayedEnvValue

from iga.data.stores import IgaGcoCacheStore


class CenGcoCacheStore(IgaGcoCacheStore):
    """Some kind of cache for GCO components in OP context."""

    _footprint = dict(
        info = 'CENGCO cache access',
        attr = dict(
            netloc = dict(
                values  = ['cengco.cache.fr'],
            ),
            rootdir = dict(
                default = DelayedEnvValue('rd_gcocache'),
            ),

        )
    )


