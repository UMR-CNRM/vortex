#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AlgoComponents for OOPS elementary tests.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import io
import json

import footprints

from common.syntax.stdattrs import test_type, expected_target, select_expected_target
from .oopsroot import OOPSParallel, OOPSODB

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class _OOPSTestComponent(object):
    """
    Extend OOPSParallel Algo Components with OOPS Tests features.

    Algo footprint is supposed to include attribute *test_type*.
    """

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        options = super(_OOPSTestComponent, self).spawn_command_options()
        options['test_type'] = self.test_type
        return options

    def set_expected_target(self):
        """
        Set env variable EXPECTED_CONFIG according to a "dumps" of either:

        # Algo attribute 'expected_target'
        # JSON resource Role: Expected Target

        If provided, Algo attribute 'select_expected_target' is used to select
        inner trees from the expected target dict.
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
            self.env.update(EXPECTED_RESULT=json.dumps({'significant_digits':"10"}))

    def prepare(self, rh, opts):
        super(_OOPSTestComponent, self).prepare(rh, opts)
        self.set_expected_target()


class OOPSTest(_OOPSTestComponent, OOPSParallel):
    """OOPS Tests without ODB."""

    _footprint = [
        test_type,
        expected_target,
        select_expected_target,
        dict(
            info = "OOPS Test run.",
            attr = dict(
                kind = dict(
                    values   = ['ootest'],
                ),
            )
        )
    ]


class OOPSecma2ccma(_OOPSTestComponent, OOPSODB):
    """OOPS Test ECMA 2 CCMA completer."""

    _footprint = [
        test_type,
        dict(
            info = "OOPS ECMA 2 CCMA completer.",
            attr = dict(
                kind = dict(
                    values   = ['oo2ccma'],
                ),
                virtualdb = dict(
                    values = ['ecma'],
                ),
            )
        )
    ]

    def postfix(self, rh, opts):
        super(OOPSecma2ccma, self).postfix(rh, opts)
        self._mv_ecma2ccma()

    def _mv_ecma2ccma(self):
        """Make the appropriate renaming of files in ECMA to CCMA."""
        sh = self.system
        for e in self.lookupodb():
            edir = e.rh.container.localpath()
            for f in sh.ls(edir):
                if f in ('ECMA.dd', 'ECMA.flags'):
                    sh.mv(sh.path.join(edir, f), sh.path.join(edir, f.replace('ECMA', 'CCMA')))
                if f in ('ECMA.iomap', 'ECMA.sch', 'IOASSIGN'):
                    with io.open(sh.path.join(edir, f), 'r') as inodb:
                        content = inodb.readlines()
                    with io.open(sh.path.join(edir, f.replace('ECMA', 'CCMA')), 'w') as outodb:
                        for line in content:
                            outodb.write(line.replace('ECMA', 'CCMA'))
                    if f in ('ECMA.iomap', 'ECMA.sch'):
                        sh.rm(sh.path.join(edir,f))
            sh.mv(edir, edir.replace('ECMA', 'CCMA'))


class OOPSObsOpTest(_OOPSTestComponent, OOPSODB):
    """OOPS Obs Operators Tests."""

    _footprint = [
        test_type,
        expected_target,
        select_expected_target,
        dict(
            info = "OOPS Obs Operators Tests.",
            attr = dict(
                kind = dict(
                    values   = ['ootestobs'],
                ),
            )
        )
    ]
