#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Algo Components for S2M post processing.
"""

from __future__ import print_function, absolute_import, unicode_literals, division
from bronx.fancies import loggers
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
    from snowtools.utils import prosimu

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
            outfilename = dict(
                info = "output filename",
                optional    = False
                ),
            ),
        )

    def execute(self, rh, opts):
        # get input resources
        avail_forcasts = self.context.sequence.effective_inputs() #role="Crocus Forecast"
        print("output ", self.context.sequence.effective_outputs())
        # get list of file names
        listforcing = [am.rh.container.filename for am in avail_forcasts]
        # self.context.session.sh.cp(avail_forcasts[0].rh.container.filename, self.outfilename)

        #print("forcing", listforcing)
        ens = EnsemblePostproc(Ensemble(), self.varnames, listforcing,
                               vortex.proxy.container(filename=self.outfilename, mode='wb'))
        ens.postprocess()





