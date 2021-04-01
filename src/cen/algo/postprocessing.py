#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Algo Components for S2M post processing.
"""

from __future__ import print_function, absolute_import, unicode_literals, division
from bronx.fancies import loggers
from bronx.stdtypes.date import Date
from bronx.syntax.externalcode import ExternalCodeImportChecker
from collections import defaultdict
import footprints
import six
import vortex.toolbox

from vortex.algo.components import AlgoComponent
logger = loggers.getLogger(__name__)

echecker = ExternalCodeImportChecker('snowtools')
with echecker:
    from snowtools.plots.pearps2m.postprocess import EnsemblePostproc, Ensemble


@echecker.disabled_if_unavailable
class S2m_ensemble_postprocessing(AlgoComponent):
    """
    S2M ensemble forecast postprocessing.

    Current use : Get ensemble median of "fresh snow" (12-hourly and daily accumulation for the Bulletin 4 saisons)
    """
    _footprint = dict(
        info = 'Algo component for post-processing of s2m ensemble simulations',
        attr = dict(
            kind = dict(
                values = ['s2m_postproc']),
            varnames = dict(
                info = "Variable names to be post-processed",
                type = list,
                optional = False
                ),
            engine = dict(
                optional    = True,
                default     = 's2m',
                values      = ['s2m']
                ),
            datebegin=dict(
                info="Date in the namelist to run PREP.",
                type=Date,
            ),
            dateend=dict(
                info="Date in the namelist to stop OFFLINE.",
                type=Date,
                default=None),
            ),
        )

    def execute(self, rh, opts):
        # get input resources
        avail_forcasts = self.context.sequence.effective_inputs()  # role="Crocus Forecast"
        # get list of file names
        listforcing = [am.rh.container.filename for am in avail_forcasts]
        # init ensemble postprocessing object
        ens = EnsemblePostproc(Ensemble(), self.varnames, listforcing, self.datebegin, self.dateend)
        # do postprocessing
        ens.postprocess()
