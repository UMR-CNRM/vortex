#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Various Resources for executables used by the OOPS software.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

from vortex.data.executables import NWPModel
from gco.syntax.stdattrs import gvar, arpifs_cycle
from common.syntax.stdattrs import oops_run

#: No automatic export
__all__ = []


class OOPSBinary(NWPModel):
    """Yet an other OOPS Binary."""

    _footprint = [
        arpifs_cycle,
        gvar,
        oops_run,
        dict(
            info = 'OOPS Binary: an OOPS binary, dedicated to a task (a run in OOPS namespace).',
            attr = dict(
                kind = dict(
                    values = ['oopsbinary', ],
                ),
                gvar = dict(
                    default = 'binary_[run]',
                ),
                run = dict(
                    outcast = ['ootestcomponent', ]
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'oopsbinary'

    def command_line(self, configfile):
        """
        Build command line for execution as a single string.
        """
        cmdline = '{}'.format(configfile)
        return cmdline


class OOPSTestComponent(OOPSBinary):
    """Binary for OOPS Tests of components."""

    _footprint = dict(
        info = 'OOPS Component Test: can run a sub-test or a family of sub-tests',
        attr = dict(
            run = dict(
                values   = ['ootestcomponent', ],
                outcast  = [],
            ),
        ),
    )

    def command_line(self, configfile, test_type=None):
        """
        Build command line for execution as a single string.
        """
        cmdline = ''
        if test_type is not None:
            cmdline += '-t {} '.format(test_type)
        cmdline += super(OOPSTestComponent, self).command_line(configfile)
        return cmdline
