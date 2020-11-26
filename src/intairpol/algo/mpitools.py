#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Customised MPI binaries for intairpol MPI AlgoComponents.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.algo import mpitools
from common.tools.partitioning import setup_partitioning_in_namelist

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class MpiMocage(mpitools.MpiBinaryBasic):
    """The kind of binaries used in Mocage's forecasts."""

    _footprint = dict(
        attr = dict(
            kind = dict(values = ['mocagebasic', ]),
        ),
    )

    def setup_namelist_delta(self, namcontents, namlocal):
        """Setup partitioning on local namelist ``namlocal`` with contents namcontents."""
        namw = setup_partitioning_in_namelist(namcontents,
                                              self.nprocs,
                                              self.options.get('openmp', 1),
                                              namlocal)
        return namw


def mocage_omplist_binarydeco(omp_variables):
    """Decorator for :class:`mpitools.MpiBinaryBasic` classes.

    Adds the number of OMP threads in the variables listed in omp_variables.
    """
    def mocage_omp_binarydeco(cls):
        """Export the appropriate OpenMP variables."""

        orig_setup_env = getattr(cls, 'setup_environment')

        def setup_environment(self, opts):
            orig_setup_env(self, opts)
            for omp_variable in omp_variables:
                if omp_variable not in self.env:
                    self.env[omp_variable] = self.options.get('openmp', 1)
                    logger.info("OpenMP settings: %s=%d", omp_variable, self.env[omp_variable])
                else:
                    logger.info("Variable %d already set : %d", omp_variable, self.env[omp_variable])

        if hasattr(orig_setup_env, '__doc__'):
            setup_environment.__doc__ = orig_setup_env.__doc__

        setattr(cls, 'setup_environment', setup_environment)
        return cls

    return mocage_omp_binarydeco


@mocage_omplist_binarydeco(('MOCAGE_OMP_NUM_THREADS',
                            'DAIMON_B_OMP_NUM_THREADS',
                            'DAIMON_H_OMP_NUM_THREADS'))
class MpiMocagePalm(MpiMocage):
    """The kind of binaries used in Mocage's Palm assimilation."""

    _footprint = dict(
        attr = dict(
            kind = dict(values = ['mocagepalm', ]),
        ),
    )
