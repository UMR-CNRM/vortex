#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Algo Components for S2M post processing.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
from bronx.syntax.externalcode import ExternalCodeImportChecker
from footprints.stdtypes import FPList

from vortex.algo.components import AlgoComponent

logger = loggers.getLogger(__name__)

echecker = ExternalCodeImportChecker('snowtools')
with echecker:
    from snowtools.plots.pearps2m.postprocess import EnsemblePostproc, Ensemble


@echecker.disabled_if_unavailable
class S2m_ensemble_postprocessing(AlgoComponent):
    """S2M ensemble forecast postprocessing.

    Current use : Get ensemble deciles of "fresh snow" (12-hourly and daily accumulation for the Bulletin 4 saisons)
    """
    _footprint = [
        dict(
            info = 'Algo component for post-processing of s2m ensemble simulations',
            attr = dict(
                kind = dict(
                    values = ['s2m_postproc']
                ),
                varnames = dict(
                    info = "Variable names to be post-processed",
                    type = FPList,
                ),
                engine = dict(
                    optional    = True,
                    default     = 's2m',
                    values      = ['s2m']
                ),
            ),
        ),
    ]

    def execute(self, rh, opts):
        # get input resources
        avail_forecasts = self.context.sequence.effective_inputs(role="CrocusForecast")
        # get list of file names
        listforcing = [am.rh.container.filename for am in avail_forecasts]
        # init ensemble postprocessing object
        ens = EnsemblePostproc(Ensemble(), self.varnames, listforcing,
                               avail_forecasts[0].rh.resource.datebegin,
                               avail_forecasts[0].rh.resource.dateend)
        # do postprocessing
        ens.postprocess()
