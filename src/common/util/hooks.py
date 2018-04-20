#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Some useful hooks.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

#: No automatic export
__all__ = []


def update_namelist(t, rh, *completive_rh):
    """Update namelist with resource handler(s) given in **completive_rh**."""
    for crh in completive_rh:
        print('Merging: {!r} :\n{:s}'.format(crh.container, rh.contents.dumps()))
        rh.contents.merge(crh.contents)
    rh.save()
