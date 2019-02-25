#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Common interest classes to help setup the DrHook library environment.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import footprints
from bronx.fancies import loggers

from vortex.algo.components import AlgoComponentDecoMixin, Parallel

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class DrHookDecoMixin(AlgoComponentDecoMixin):
    """Handle DrHook settings in AlgoComponnents.

    This mixin class is intended to be used with AlgoComponnent classes. It will
    automatically add footprints' arguments related to DrHook (namely the
    drhookprof boolean attribute that is optional and False by default),
    and set up DrHook environment variables (:meth:`_drhook_varexport`) depending
    on the context (MPI run or not).
    """

    _MIXIN_EXTRA_FOOTPRINTS = [
        footprints.Footprint(
            attr = dict(
                drhookprof = dict(
                    info            = 'Activate the DrHook profiling.',
                    optional        = True,
                    type            = bool,
                    default         = False,
                    doc_zorder      = -50,
                ),
            ),
        )]

    def _drhook_varexport(self, rh, opts):  # @UnusedVariable
        """Export proper DrHook variables"""
        # Basic exports
        self.export('drhook{}'.format('prof' if self.drhookprof else ''))
        if not isinstance(self, Parallel):
            self.export('drhook_not_mpi')

    _MIXIN_PREPARE_HOOKS = (_drhook_varexport, )
