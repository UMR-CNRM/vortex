# -*- coding: utf-8 -*-
"""
DAVAI expertise AlgoComponents.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

from footprints import FPList, FPDict
from bronx.fancies import loggers

from vortex.syntax import stdattrs
from vortex.algo.components import (AlgoComponent, AlgoComponentDecoMixin,
                                    AlgoComponentError)
from davai import util
from davai.algo.mixins import context_info_for_task_summary

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class XPsetup(AlgoComponent):
    """Collect metadata about the experiment."""

    _footprint = [
        stdattrs.xpid,
        dict(
            info = "Save characteristics of the tested experiment.",
            attr = dict(
                kind = dict(
                    values   = ['xpsetup'],
                ),
                experiment = dict(
                    alias = ('xpid', )
                ),
            )
        )
    ]

    def execute(self, rh, kw):  # @UnusedVariable
        from davai_taskutil.experiment import XPMetadata  # @UnresolvedImport
        xpm = XPMetadata(self.experiment)
        xpm.write()


class CiboulaiXPsetup_mkjob(AlgoComponent):
    """Collect metadata about the experiment."""

    _footprint = [
        stdattrs.xpid,
        dict(
            info = "Save characteristics of the tested experiment.",
            attr = dict(
                kind = dict(
                    values   = ['ciboulai_xpsetup_mkjob'],
                ),
                experiment = dict(
                    alias = ('xpid', )
                ),
                conf = dict(
                    type = FPDict
                ),
            )
        )
    ]

    def execute(self, rh, kw):  # @UnusedVariable
        from davai_taskutil.experiment import gather_mkjob_xp_conf  # @UnresolvedImport
        gather_mkjob_xp_conf(self.experiment, self.conf)


class _FailedExpertiseDecoMixin(AlgoComponentDecoMixin):
    """
    Extend Expertise algo to catch exceptions in the parsing/summary/comparison,
    and process TaskSummary anyway; notifying an error in parsing/summary
    in that case.
    """

    def expertise_fail_execute(self, e, rh, kw):  # @UnusedVariables
        promise = [x for x in self.promises
                   if x.role == 'TaskSummary']
        if len(promise) == 1:
            if not self.system.path.exists(promise[0].rh.container.localpath()):
                # if file had been written, means that the comparison failed
                summary = {'Status': {'symbol': 'E!',
                                      'short': 'Ended ! Summary failed',
                                      'text': 'Task ended, but Expertise failed: no TaskSummary available !'},
                           'Exception': str(e)}
                self.system.json_dump(summary, promise[0].rh.container.localpath(), indent=4)
            promise[0].put(incache=True)
        elif len(promise) > 1:
            raise AlgoComponentError("There shouldn't be more than 1 promise here.")

    _MIXIN_FAIL_EXECUTE_HOOKS = (expertise_fail_execute, )


class Expertise(AlgoComponent, _FailedExpertiseDecoMixin):
    """
    Expertise an AlgoComponent, produces a summary of the task.
    """

    _footprint = [
        stdattrs.block, stdattrs.xpid,
        dict(
            info = "Expertise Algo output and produce a summary of task, with eventual comparison to a reference.",
            attr = dict(
                kind = dict(
                    values   = ['expertise'],
                ),
                experts = dict(
                    type = FPList,
                    info = "The list of footprints of Experts to be used to evaluate the Algo execution.",
                    optional = True,
                    default = [],
                ),
                ignore_reference = dict(
                    info = "Set to True if no comparison to be done.",
                    type = bool,
                    optional = True,
                    default = False,
                ),
                fatal_exceptions = dict(
                    info = "Raise parsing/summary/compare errors.",
                    type = bool,
                    optional = True,
                    default = False,
                ),
                lead_expert = dict(
                    info = "indicate whose Main metrics is to be selected from the experts panel",
                    type = FPDict,
                    optional = True,
                    default = None
                ),
                experiment = dict(
                    alias = ('xpid', )
                ),
            )
        )
    ]

    def prepare(self, rh, opts):  # @UnusedVariable
        from ial_expertise.task import ExpertBoard  # @UnresolvedImport
        # io_poll if needed
        for p in ('ICMSH', 'PF', 'GRIBPF'):
            if self.system.path.exists('io_poll.todo.{}'.format(p)):
                self.system.io_poll(p)
        for e in self.experts:
            e.setdefault('fatal_exceptions', self.fatal_exceptions)
        self._inner = ExpertBoard(self.experts, lead_expert=self.lead_expert)

    def execute(self, rh, kw):  # @UnusedVariable
        if self.ignore_reference:
            consistency_resources = None
            continuity_resources = None
        else:
            ref_resources = self.context.sequence.effective_inputs(
                role=('Reference', 'ContinuityReference', 'ConsistencyReference'))
            # split
            consistency_resources, continuity_resources = self._split_ref_resources(ref_resources)
            # prepare
            consistency_resources = self._prepare_ref_resources(consistency_resources, 'Consistency')
            continuity_resources = self._prepare_ref_resources(continuity_resources, 'Continuity')
        if hasattr(self._inner, 'remember_context'):
            self._inner.remember_context(context_info_for_task_summary(self.context))
        self._inner.remember_listings(self.promises, continuity_resources)
        self._inner.process(consistency_resources, continuity_resources)

    def postfix(self, rh, opts):  # @UnusedVariable
        # Dump result (TaskSummary)
        promises = [x for x in self.promises if x.role == 'TaskSummary']
        # Put
        for p in promises:
            p.put(incache=True)

    def _split_ref_resources(self, ref_resources):
        """Split resources in consistency_resources and continuity_resources."""
        consistency_resources = [s.rh for s in ref_resources
                                 if (s.role == 'ConsistencyReference' or  # explicitly mentioned as Consistency
                                     (s.rh.provider.experiment == self.experiment and  # same XPID
                                      s.rh.provider.block != self.block)  # different block
                                     )]
        continuity_resources = [s.rh for s in ref_resources
                                if (s.role == 'ContinuityReference' or  # explicitly mentioned as Continuity
                                    (s.rh.provider.experiment != self.experiment or  # different XPID
                                     s.rh.provider.block == self.block)  # and same block
                                    )]
        return consistency_resources, continuity_resources

    def _prepare_ref_resources(self, resource_handlers, refkind):
        """Prepare resources for what expert need."""
        if len(resource_handlers) == 0:
            return []
        else:
            xp = [rh.provider.experiment for rh in resource_handlers]
            block = [rh.provider.block for rh in resource_handlers]
            if len(set(xp)) > 1:
                raise AlgoComponentError(
                    refkind +
                    " reference resources must all come from the same 'experiment'.")  # continuity
            if len(set(block)) > 1:
                raise AlgoComponentError(
                    refkind +
                    " reference resources must all come from the same 'block'.")  # consistency
            if refkind == 'Continuity':
                ref_is = {'experiment': xp[0],
                          'task': '(same)'}
            elif refkind == 'Consistency':
                ref_is = {'experiment': '(same)',
                          'task': block[0]}
        return [{'rh': rh,
                 'ref_is': ref_is}
                for rh in resource_handlers]


class LoadStackInTrolley(AlgoComponent):
    """
    Gather all json of Stack into a single "trolley" tar file.
    """

    _footprint = [
        stdattrs.xpid,
        dict(
            info = 'Gather all json of Stack into a single "trolley" tar file.',
            attr = dict(
                kind = dict(
                    values   = ['load_stack_in_trolley'],
                ),
                vapp = dict(),
                vconf = dict(),
                experiment = dict(
                    alias = ('xpid', )
                ),
            )
        )
    ]

    def execute(self, rh, kw):  # @UnusedVariable
        stack = util.SummariesStack(ticket=self.ticket,
                                    vapp=self.vapp,
                                    vconf=self.vconf,
                                    xpid=self.experiment)
        if not (stack.load_trolleytar(fetch=True)):
            raise AlgoComponentError("Could not get the trolley tar file")
