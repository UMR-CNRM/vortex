# -*- coding: utf-8 -*-
"""
Wrappers above usual AlgoComponents.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

import footprints
from bronx.stdtypes import date

from vortex.algo.components import AlgoComponentDecoMixin, AlgoComponentError, BlindRun
from common.algo.oopstests import (OOPSObsOpTest, OOPSecma2ccma,
                                   OOPSTestEnsBuild, OOPSTest)
from common.algo.oopsroot import OOPSAnalysis
from common.algo.assim import (Screening, Minim, Canari)
from common.algo.odbtools import (Raw2ODBparallel)
from common.algo.forecasts import (Forecast, LAMForecast, DFIForecast,
                                   FullPosBDAP, FullPosGeo)
from common.algo.clim import (BuildPGD, BuildPGD_MPI)
from common.algo.coupling import (CouplingBaseDateNamMixin, Coupling, PrepMixin)
from common.tools.drhook import DrHookDecoMixin

#: No automatic export
__all__ = []


class _CrashWitnessDecoMixin(AlgoComponentDecoMixin):
    """
    Extend Algo Components to catch exceptions in the binary execution,
    notify it into the job summary (witness), and push it.
    """

    _MIXIN_EXTRA_FOOTPRINTS = (
        footprints.Footprint(
            info='The CrashWitness version of the Algo',
            attr=dict(
                crash_witness=dict(
                    type=bool,
                    optional=False,
                    values=[True, ]
                ),
            )
        ),
    )

    def crash_witness_fail_execute(self, e, rh, kw):  # @UnusedVariables
        from davai_tbx.expertise import task_status  # @UnresolvedImport
        from davai_tbx.util import context_info_for_task_summary  # @UnresolvedImport
        status = task_status['X']
        # check reference and mention if reference was crashed too
        ref_summary = [s for s in self.context.sequence.effective_inputs(role=('Reference',
                                                                               'ContinuityReference',
                                                                               'ConsistencyReference'))
                       if s.rh.resource.kind == 'taskinfo']
        if len(ref_summary) == 1:
            ref_summary = ref_summary[0].rh.contents.data  # slurp
            ref_status = ref_summary.get('Status')
            if ref_status['symbol'].startswith('X'):
                status = task_status['X=R']
        elif len(ref_summary) == 0:  # if reference crashed, the summary is not available in archive
            status = task_status.get('X:R?', task_status['X'])
        # then write summary in promise
        summary = {'Status': status,
                   'Context': context_info_for_task_summary(self.context),
                   'Exception': str(e),
                   'Updated': date.utcnow().isoformat().split('.')[0]}
        promise = [x for x in self.promises
                   if x.role == 'TaskSummary']
        if len(promise) == 1:
            self.system.json_dump(summary, promise[0].rh.container.localpath(), indent=4)
            promise[0].put(incache=True)
        elif len(promise) > 1:
            raise AlgoComponentError("There shouldn't be more than 1 promise here.")
        elif len(promise) == 0:
            raise AlgoComponentError("There should be a promise here.")

    _MIXIN_FAIL_EXECUTE_HOOKS = (crash_witness_fail_execute, )


# OOPS algos
class OOPSObsOpTest_CrashWitness(OOPSObsOpTest, _CrashWitnessDecoMixin):
    pass


class OOPSecma2ccma_CrashWitness(OOPSecma2ccma, _CrashWitnessDecoMixin):
    pass


class OOPSTestEnsBuild_CrashWitness(OOPSTestEnsBuild, _CrashWitnessDecoMixin):
    pass


class OOPSTest_CrashWitness(OOPSTest, _CrashWitnessDecoMixin):
    pass


class OOPSMinim_CrashWitness(OOPSAnalysis, _CrashWitnessDecoMixin):
    pass


# Legacy algos
class Screening_CrashWitness(Screening, _CrashWitnessDecoMixin):
    pass


class Minim_CrashWitness(Minim, _CrashWitnessDecoMixin):
    pass


class Raw2ODBparallel_CrashWitness(Raw2ODBparallel, _CrashWitnessDecoMixin):
    pass


class Forecast_CrashWitness(Forecast, _CrashWitnessDecoMixin):
    pass


class LAMForecast_CrashWitness(LAMForecast, _CrashWitnessDecoMixin):
    pass


class DFIForecast_CrashWitness(DFIForecast, _CrashWitnessDecoMixin):
    pass


class FullPosBDAP_CrashWitness(FullPosBDAP, _CrashWitnessDecoMixin):
    pass


class FullPosGeo_CrashWitness(FullPosGeo, _CrashWitnessDecoMixin):
    pass


class BuildPGD_CrashWitness(BuildPGD, _CrashWitnessDecoMixin):
    pass


class BuildPGD_MPI_CrashWitness(BuildPGD_MPI, _CrashWitnessDecoMixin):
    pass


class Prep_CrashWitness(BlindRun, _CrashWitnessDecoMixin,
                        PrepMixin, CouplingBaseDateNamMixin, DrHookDecoMixin):
    pass


class Coupling_CrashWitness(Coupling, _CrashWitnessDecoMixin):
    pass


class Canari_CrashWitness(Canari, _CrashWitnessDecoMixin):
    pass
