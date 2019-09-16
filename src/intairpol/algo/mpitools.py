#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

"""
Customised MPI binaries for intairpol MPI AlgoComponents.
"""

from bronx.fancies import loggers

from vortex.algo import mpitools

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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
                self.env[omp_variable] = self.options.get('openmp', 1)
                logger.info("OpenMP settings: %s=%d", omp_variable, self.env[omp_variable])

        if hasattr(orig_setup_env, '__doc__'):
            setup_environment.__doc__ = orig_setup_env.__doc__

        setattr(cls, 'setup_environment', setup_environment)
        return cls

    return mocage_omp_binarydeco


@mocage_omplist_binarydeco(('MOCAGE_OMP_NUM_THREADS',
                            'DAIMON_B_OMP_NUM_THREADS',
                            'DAIMON_H_OMP_NUM_THREADS'))
class MpiMocagePalm(mpitools.MpiBinaryBasic):
    """The kind of binaries used in Mocage's Palm assimilation."""

    _footprint = dict(
        attr = dict(
            kind = dict(values = ['mocagepalm', ]),
        ),
    )