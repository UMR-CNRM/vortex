#!/usr/bin/env python
# -*- coding:Utf-8 -*-
"""
DAVAI expertise AlgoComponents.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

import json

from footprints import FPList, FPDict
from bronx.fancies import loggers
from bronx.stdtypes import date

from vortex.algo.components import (AlgoComponent, AlgoComponentDecoMixin,
                                    AlgoComponentError)
from gco.tools import uenv, genv

from davai import util

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class XpidRegister(AlgoComponent):
    """
    Save metadata about the experiment.
    """

    _footprint = dict(
        info = "Save characteristics of the testing experiment.",
        attr = dict(
            kind = dict(
                values   = ['xpid_register'],
            ),
            xpid = dict(
                info = "Identifier of the Experiment"
            ),
            ref_xpid = dict(
                info = "Identifier of the Reference Experiment",
                optional = True,
                default = None
            ),
            cycle = dict(
                info = "genv or uenv cycle used. Default tries to access from env variable CYCLE.",
                optional = True,
                default = None,
                access = 'rwx'
            ),
            input_store = dict(
                info = "The store in which to pick initial resources"
            ),
            usecase = dict(
                info = """Usecase: ELP vs. NRV // Exploration and Localization of Problems vs. Non-Regression Validation.
                          Default tries to access from env variable USECASE.""",
                optional = True,
                default = None,
                access = 'rwx'
            ),
        )
    )

    def prepare(self, rh, opts):  # @UnusedVariable
        if self.usecase is None:
            self.usecase = self.env.get('USECASE')
        if self.cycle is None:
            self.cycle = self.env.get('CYCLE')
        if self.ref_xpid == self.xpid:
            self.ref_xpid = None

    def execute(self, rh, kw):  # @UnusedVariable
        metadata = {'initial_time_of_launch':date.utcnow().iso8601(),
                    'xpid':self.xpid,
                    'ref_xpid':self.ref_xpid,
                    'cycle':self.cycle,
                    'input_store':self.input_store,
                    'cycle_detail':self._get_cycle_env(),
                    'git_branch':self.env.get('GIT_BRANCH'),
                    'usecase':self.usecase}
        with open('xpinfo.json', 'w') as out:
            json.dump(metadata, out, indent=4, sort_keys=True)

    def _get_cycle_env(self, linesep='<br>'):
        if any([self.cycle.startswith(scheme) for scheme in ('uget:', 'uenv:')]):
            details = uenv.nicedump(self.cycle,
                                    scheme='uget',
                                    netloc='uget.multi.fr')
        else:
            details = ['%s="%s"' % (k,v)
                       for (k,v) in genv.autofill(self.cycle).items()]
        return linesep.join(details)


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
                # if file has been written, means that the comparison failed
                summary = {'Status':'Expertise failed',
                           'Exception':str(e)}
                with open(promise[0].rh.container.localpath(), 'w') as out:
                    json.dump(summary, out)
            promise[0].put(incache=True)
        elif len(promise) > 1:
            raise AlgoComponentError("There shouldn't be more than 1 promise here.")

    _MIXIN_FAIL_EXECUTE_HOOKS = (expertise_fail_execute, )


class Expertise(AlgoComponent, _FailedExpertiseDecoMixin):
    """
    Expertise an AlgoComponent, produces a summary of the task.
    """

    _footprint = dict(
        info = "Expertise Algo output and produce a summary of task, with eventual comparison to a reference.",
        attr = dict(
            kind = dict(
                values   = ['expertise'],
            ),
            experts = dict(
                type = FPList,
                info = "The list of footprints of Experts to be used to evaluate the Algo execution.",
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
        )
    )

    def prepare(self, rh, opts):  # @UnusedVariable
        import davai_tbx  # @UnresolvedImport
        for e in self.experts:
            e.setdefault('fatal_exceptions', self.fatal_exceptions)
        self._inner = davai_tbx.expertise.ExpertBoard(self.experts,
                                                      lead_expert=self.lead_expert)

    def execute(self, rh, kw):  # @UnusedVariable
        if self.ignore_reference:
            consistency_resources = None
            continuity_resources = None
        else:
            ref_resources = self.context.sequence.effective_inputs(
                role=('Reference', 'ContinuityReference', 'ConsistencyReference'))
            consistency_resources, continuity_resources = self._split_ref_resources(ref_resources)
            consistency_resources = self._prepare_ref_resources(consistency_resources, 'Consistency')
            continuity_resources = self._prepare_ref_resources(continuity_resources, 'Continuity')
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
                                     (s.rh.provider.experiment == self.env.XPID and  # same XPID
                                      s.rh.provider.block != util.block_from_olive_tree())  # different block
                                     )]
        continuity_resources = [s.rh for s in ref_resources
                                if (s.role == 'ContinuityReference' or  # explicitly mentioned as Continuity
                                     (s.rh.provider.experiment != self.env.XPID or  # different XPID
                                      s.rh.provider.block == util.block_from_olive_tree())  # and same block
                                    )]
        return consistency_resources, continuity_resources

    def _prepare_ref_resources(self, resource_handlers, refkind):
        """Prepare resources for what expert need."""
        if len(resource_handlers) == 0:
            return []
        else:
            xp = [r.provider.experiment for r in resource_handlers]
            block = [r.provider.block for r in resource_handlers]
            if len(set(xp)) > 1:
                raise AlgoComponentError(refkind + " reference resources must all come from the same 'experiment'.")  # continuity
            if len(set(block)) > 1:
                raise AlgoComponentError(refkind + " reference resources must all come from the same 'block'.")  # consistency
            if refkind == 'Continuity':
                ref_is = {'Reference is':{'experiment':xp[0],
                                          'task':'(same)'}}
            elif refkind == 'Consistency':
                ref_is = {'Reference is':{'experiment':'(same)',
                                          'task':block[0]}}
        return [{'localpath':rh.container.localpath(),
                 'kind':rh.resource.kind,
                 'reference_info':ref_is}
                for rh in resource_handlers]


class LoadStackInTrolley(AlgoComponent):
    """
    Gather all json of Stack into a single "trolley" tar file.
    """

    _footprint = dict(
        info = 'Gather all json of Stack into a single "trolley" tar file.',
        attr = dict(
            kind = dict(
                values   = ['load_stack_in_trolley'],
            ),
            xpid = dict(),
            vapp = dict(),
            vconf = dict(),
        )
    )

    def execute(self, rh, kw):  # @UnusedVariable
        stack = util.SummariesStack(vapp=self.vapp,
                                    vconf=self.vconf,
                                    xpid=self.xpid)
        stack.load_trolleytar(self.ticket)
        # and get it back for archiving
        self.system.cp(stack.trolleytar_abspath, stack.trolleytar)
