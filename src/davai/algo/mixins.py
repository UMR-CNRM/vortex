"""
Wrappers above usual AlgoComponents.
"""

import footprints
from bronx.stdtypes import date

from vortex.algo.components import AlgoComponentDecoMixin, AlgoComponentError
from common.algo.oopstests import (OOPSObsOpTest, OOPSecma2ccma,
                                   OOPSTestEnsBuild, OOPSTest)
from common.algo.oopsroot import OOPSAnalysis, OOPSAnalysisWithScreening
from common.algo.assim import (Screening, Minim, Canari)
from common.algo.odbtools import (Raw2ODBparallel)
from common.algo.forecasts import (Forecast, LAMForecast, DFIForecast,
                                   FullPosBDAP, FullPosGeo)
from common.algo.clim import (BuildPGD, BuildPGD_MPI)
from common.algo.coupling import Coupling, Prep
from common.algo.fpserver import FullPosServer

#: No automatic export
__all__ = []


def context_info_for_task_summary(context, jobname=None):
    """Get some infos from context for task summary."""
    info = {'rundir': context.rundir}
    for k in ('MTOOL_STEP_ABORT', 'MTOOL_STEP_DEPOT', 'MTOOL_STEP_SPOOL'):
        v = context.env.get(k, None)
        if v:
            info[k] = v
    if context.rundir and 'MTOOL_STEP_ABORT' in info and 'MTOOL_STEP_SPOOL' in info:
        abort_dir = context.system.path.join(info['MTOOL_STEP_ABORT'],
                                             context.rundir[len(info['MTOOL_STEP_SPOOL']) + 1:])
        info['(if aborted)'] = abort_dir
    if jobname is not None:
        info['jobname'] = jobname
    return info


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
                mkjob_jobname=dict(
                    info="Job name in mkjob context",
                    optional=True,
                ),
            )
        ),
    )

    @property
    def context_info_for_task_summary(self):
        return context_info_for_task_summary(self.context, jobname=self.mkjob_jobname)

    def crash_witness_fail_execute(self, e, rh, kw):  # @UnusedVariables
        from ial_expertise.task import task_status  # @UnresolvedImport
        status = task_status['X']
        # check reference and mention if reference was crashed too
        ref_summary = [s for s in self.context.sequence.effective_inputs(role=('Reference',
                                                                               'ContinuityReference',
                                                                               'ConsistencyReference'))
                       if s.rh.resource.kind in ('taskinfo', 'statictaskinfo')]
        if len(ref_summary) == 1:
            ref_summary = ref_summary[0].rh.contents.data  # slurp
            ref_status = ref_summary.get('Status')
            if ref_status['symbol'].startswith('X'):
                status = task_status['X=R']
        elif len(ref_summary) == 0:  # if reference crashed, the summary is not available in archive
            status = task_status.get('X:R?', task_status['X'])
        # then write summary in promise
        summary = {'Status': status,
                   'Context': self.context_info_for_task_summary,
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


class OOPSAnalysis_CrashWitness(OOPSAnalysis, _CrashWitnessDecoMixin):
    pass


class OOPSAnalysisWithScreening_CrashWitness(OOPSAnalysisWithScreening, _CrashWitnessDecoMixin):
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


class FullPosServer_CrashWitness(FullPosServer, _CrashWitnessDecoMixin):
    pass


class BuildPGD_CrashWitness(BuildPGD, _CrashWitnessDecoMixin):
    pass


class BuildPGD_MPI_CrashWitness(BuildPGD_MPI, _CrashWitnessDecoMixin):
    pass


class Prep_CrashWitness(Prep, _CrashWitnessDecoMixin):
    pass


class Coupling_CrashWitness(Coupling, _CrashWitnessDecoMixin):
    pass


class Canari_CrashWitness(Canari, _CrashWitnessDecoMixin):
    pass
