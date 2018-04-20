#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from vortex.syntax.stdattrs import DelayedEnvValue

from iga.data.stores import IgaGcoCacheStore

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


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
