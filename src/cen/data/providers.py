#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import os

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.util.config     import GenericConfigParser
from vortex.syntax.stdattrs import a_suite, member, namespacefp
from iga.data.providers  import SopranoProvider
from gco.data.providers import GEnv

from common.tools.igastuff import IgakeyFactoryInline

import iga.util.bpnames as bp



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


