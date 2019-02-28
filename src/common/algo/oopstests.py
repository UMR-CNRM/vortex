#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AlgoComponents for OOPS elementary tests.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import io
import json

import footprints

from vortex.algo.components import AlgoComponentDecoMixin
from common.syntax.stdattrs import oops_test_type, oops_expected_target, oops_select_expected_target
from .oopsroot import OOPSParallel, OOPSODB, OOPSMembersTermsDecoMixin, OOPSMemberDetectDecoMixin

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class _OOPSTestDecoMixin(AlgoComponentDecoMixin):
    """Extend OOPSParallel Algo Components with OOPS Tests features.

    This mixin class is intended to be used with AlgoComponnent classes. It will
    automatically add the ``test_type`` footprints' attribute and extend the
    the dictionary that is used to build the binary' command line.
    """

    _MIXIN_EXTRA_FOOTPRINTS = (oops_test_type, )

    def _ooptest_cli_opts_extend(self, prev):
        """Prepare options for the resource's command line."""
        prev['test_type'] = self.test_type
        return prev

    _MIXIN_CLI_OPTS_EXTEND = (_ooptest_cli_opts_extend, )


class _OOPSTestExpTargetDecoMixin(AlgoComponentDecoMixin):
    """Extend OOPSParallel Algo Components with OOPS Tests verification features.

    This mixin class is intended to be used with AlgoComponnent classes. It will
    automatically add the ``expected_target`` and ``select_expected_target``
    footprints' attributes and use them to setup the associatied environement
    variable (see :meth:`set_expected_target`
    """

    _MIXIN_EXTRA_FOOTPRINTS = (oops_expected_target,
                               oops_select_expected_target)

    def set_expected_target(self):
        """Set env variable EXPECTED_CONFIG.

        It will create it using a JSON "dump" of either:

            * The Algo Component's attribute ``expected_target``;
            * The JSON resource of role "Expected Target".

        :note: If provided, the Algo Component's attribute '`select_expected_target'`
            is used to select inner trees from the expected target dictionary.
        """
        target = None
        select = None
        # if attribute 'expected_target' is attribute and given to the algo, use it
        if hasattr(self, 'expected_target'):
            target = self.expected_target
        # else, go find JSON in effective inputs
        if target is None:
            expected = self.context.sequence.effective_inputs(role=('ExpectedTargets',))
            if len(expected) > 0:
                expectedfile = expected[0].rh.container.localpath()
                with io.open(expectedfile, 'r') as cf:
                    target = json.load(cf)
        # now either we found it in input or in attribute, or no target is defined
        # if defined, filter it with keys of attribute 'select_expected_target'
        if hasattr(self, 'select_expected_target'):
            select = self.select_expected_target
        if target is not None:
            if select is not None:
                for k in select:
                    target = target[k]  # will raise an error if key not present in dict
        # so in the end, if an expected result has been defined, export it
        if target is not None:
            print("Expected Target for Test:", target)
            self.env.update(EXPECTED_RESULT=json.dumps(target))
        else:
            self.env.update(EXPECTED_RESULT=json.dumps({'significant_digits': "10"}))

    def _ooptest_exptarget_prepare_hook(self, rh, opts):
        """Call set_expected_target juste after prepare."""
        self.set_expected_target()

    _MIXIN_PREPARE_HOOKS = (_ooptest_exptarget_prepare_hook, )


class OOPSTest(OOPSParallel, _OOPSTestDecoMixin, _OOPSTestExpTargetDecoMixin,
               OOPSMemberDetectDecoMixin):
    """OOPS Tests without ODB."""

    _footprint = dict(
        info = "OOPS Test run.",
        attr = dict(
            kind = dict(
                values = ['ootest'],
            ),
            test_type = dict(
                outcast = ['ensemble/build', ]
            ),
        )
    )


class OOPSTestEnsBuild(OOPSParallel, _OOPSTestDecoMixin, OOPSMembersTermsDecoMixin):
    """OOPS Tests without ODB: ensemble/build specific case"""

    _footprint = dict(
        info = "OOPS Test run.",
        attr = dict(
            kind = dict(
                values = ['ootest'],
            ),
            test_type = dict(
                values = ['ensemble/build', ]
            ),
        )
    )


class OOPSObsOpTest(OOPSODB, _OOPSTestDecoMixin, _OOPSTestExpTargetDecoMixin,
                    OOPSMemberDetectDecoMixin):
    """OOPS Obs Operators Tests."""

    _footprint = dict(
        info = "OOPS Obs Operators Tests.",
        attr = dict(
            kind = dict(
                values = ['ootestobs'],
            ),
            virtualdb = dict(
                default  = 'ccma',
            ),
        )
    )


class OOPSecma2ccma(OOPSODB, _OOPSTestDecoMixin):
    """OOPS Test ECMA 2 CCMA completer."""

    _footprint = dict(
        info = "OOPS ECMA 2 CCMA completer.",
        attr = dict(
            kind = dict(
                values = ['ootest2ccma'],
            ),
            virtualdb = dict(
                values = ['ecma'],
            ),
        )
    )

    def postfix(self, rh, opts):
        """Rename the ECMA database once OOPS has run."""
        super(OOPSecma2ccma, self).postfix(rh, opts)
        self._mv_ecma2ccma()

    def _mv_ecma2ccma(self):
        """Make the appropriate renaming of files in ECMA to CCMA."""
        for e in self.lookupodb():
            edir = e.rh.container.localpath()
            self.odb.change_layout('ECMA', 'CCMA', edir)
            self.system.mv(edir, edir.replace('ECMA', 'CCMA'))
