#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Some useful hooks.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import footprints

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


def update_namelist(t, rh, *completive_rh):
    """Update namelist with resource handler(s) given in **completive_rh**."""
    for crh in completive_rh:
        if not isinstance(crh, (list, tuple)):
            crh = [crh, ]
        for arh in crh:
            logger.info('Merging: {!r} :\n{:s}'.format(arh.container,
                                                       arh.contents.dumps()))
            rh.contents.merge(arh.contents)
    rh.save()
