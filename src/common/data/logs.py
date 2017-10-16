#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.flow import FlowResource
from vortex.syntax.stdattrs import FmtInt
from vortex.data.contents   import JsonDictContent, FormatAdapter


class Listing(FlowResource):
    """Miscelanous application output from a task processing."""
    _footprint = [
        dict(
            info = 'Listing',
            attr = dict(
                task = dict(
                    optional = True,
                    default  = 'anonymous'
                ),
                kind = dict(
                    values   = ['listing']
                ),
                part = dict(
                    optional = True,
                    default  = 'all',
                ),
                binary = dict(
                    optional = True,
                    default  = '[model]',
                ),
                clscontents = dict(
                    default = FormatAdapter,
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'listing'

    def basename_info(self):
        """Generic information, radical = ``listing``."""
        return dict(
            radical = self.realkind,
            src     = [self.binary, self.task.split('/').pop()],
            compute = self.part,
        )

    def olive_basename(self):
        """Fake basename for getting olive listings"""
        if hasattr(self, '_listingpath'):
            return self._listingpath
        else:
            return "NOT_IMPLEMENTED"

    def archive_basename(self):
        return "listing." + self.part


class ParallelListing(Listing):
    """Multi output for parallel MPI and/or OpenMP processing."""
    _footprint = [
        dict(
            attr = dict(
                kind = dict(
                    values = ['listing', 'plisting', 'mlisting'],
                    remap  = dict(
                        listing  = 'plisting',
                        mlisting = 'plisting',
                    )
                ),
                mpi = dict(
                    optional = True,
                    default  = None,
                    type     = FmtInt,
                    args     = dict(fmt = '03'),
                ),
                openmp = dict(
                    optional = True,
                    default  = None,
                    type     = FmtInt,
                    args     = dict(fmt = '02'),
                ),
                seta = dict(
                    optional = True,
                    default  = None,
                    type     = FmtInt,
                    args     = dict(fmt = '03'),
                ),
                setb = dict(
                    optional = True,
                    default  = None,
                    type     = FmtInt,
                    args     = dict(fmt = '02'),
                ),
            )
        )
    ]

    def basename_info(self):
        """From base information of ``listing`` add mpi and openmp values."""
        info = super(ParallelListing, self).basename_info()
        if self.mpi and self.openmp:
            info['compute'] = [{'mpi': self.mpi}, {'openmp': self.openmp}]
        if self.seta and self.setb:
            info['compute'] = [{'seta': self.seta}, {'setb': self.setb}]
        return info


class DrHookListing(Listing):
    """Output produced by DrHook"""
    _footprint = [
        dict(
            attr = dict(
                kind = dict(
                    values = ['drhook', ],
                ),
                mpi = dict(
                    optional = True,
                    default  = None,
                    type     = FmtInt,
                    args     = dict(fmt = '03'),
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'drhookprof'

    def basename_info(self):
        """From base information of ``listing``, add mpi."""
        info = super(DrHookListing, self).basename_info()
        if self.mpi:
            info['compute'] = [{'mpi': self.mpi}, ]
        return info


class Beacon(FlowResource):
    """Output indicating the end of a model run."""
    _footprint = [
        dict(
            info = 'Beacon',
            attr = dict(
                kind = dict(
                    values   = ['beacon']
                ),
                clscontents = dict(
                    default = JsonDictContent,
                ),
                nativefmt = dict(
                    default = 'json',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'beacon'

    def basename_info(self):
        """Generic information, radical = ``beacon``."""
        return dict(
            radical = self.realkind,
            src     = [self.model],
            fmt     = self.nativefmt
        )

