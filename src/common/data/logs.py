#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.flow import FlowResource
from vortex.syntax.stdattrs import FmtInt


class Listing(FlowResource):
    """Miscelanous application output from a task processing."""
    _footprint = [
        dict(
             info = 'Listing',
             attr = dict(
                task = dict(
                    optional = True,
                    default = 'anonymous'
                ),
                kind = dict(
                    values = [ 'listing' ]
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'listing'

    def basename_info(self):
        """Generic information, radical = ``listing``."""
        return dict(
            radical = 'listing',
            src     = [ self.model, self.task.split('/').pop() ],
        )


class ParallelListing(Listing):
    """Multi output for parallel MPI and/or OpenMP processing."""
    _footprint = [
        dict(
             attr = dict(
                kind = dict(
                    values = [ 'listing', 'plisting', 'mlisting' ],
                    remap = dict(
                        listing = 'plisting',
                        mlisting = 'plisting',
                    )
                ),
                mpi = dict(
                    optional = True,
                    default = None,
                    type = FmtInt,
                    args = dict( fmt = '03' ),
                ),
                openmp = dict(
                    optional = True,
                    default = None,
                    type = FmtInt,
                    args = dict( fmt = '02' ),
                ),
                seta = dict(
                    optional = True,
                    default = None,
                    type = FmtInt,
                    args = dict( fmt = '03' ),
                ),
                setb = dict(
                    optional = True,
                    default = None,
                    type = FmtInt,
                    args = dict( fmt = '02' ),
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
