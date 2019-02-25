#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Common AlgoComponents for OOPS.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import footprints
from bronx.stdtypes.date import Date

from vortex.algo.components import Parallel
from vortex.tools import grib
from common.tools import odb, satrad

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class OOPSParallel(Parallel, grib.EcGribDecoMixin, satrad.SatRadDecoMixin):
    """Commons for OOPS."""
    _abstract = True
    _footprint = dict(
        info = "OOPS Run.",
        attr = dict(
            kind = dict(
                values          = ['oorun'],
            ),
            date = dict(
                info            = 'The current run date.',
                access          = 'rwx',
                type            = Date,
                doc_zorder      = -50,
            ),
            config_macros = dict(
                info            = "Macros to be set up in config before run",
                optional        = True,
                type            = footprints.FPDict,
                default         = footprints.FPDict()
            ),
        )
    )

    def prepare(self, rh, opts):
        super(OOPSParallel, self).prepare(rh, opts)
        self.set_macros_in_config()
        self.boost_defaults()

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        config = self.context.sequence.effective_inputs(role=('Config',))
        configfile = config[0].rh.container.localpath()
        options = {'configfile': configfile}
        return options

    def set_macros_in_config(self):
        """Set adequate macros in config file."""
        config = self.context.sequence.effective_inputs(role=('Config',))[0].rh
        incfg = config.contents
        for k, v in self.config_macros.items():
            incfg.set_macro(k, v)
        incfg.set_macro_dates({'__now__': self.date.iso8601()})
        config.save()

    def boost_defaults(self):
        """
        Set defaults for BOOST environment variables.
        Do not overwrite pre-initialised ones.
        """
        defaults = {
            'BOOST_TEST_CATCH_SYSTEM_ERRORS': 'no',
            'BOOST_TEST_DETECT_FP_EXCEPTIONS': 'yes',
            'BOOST_TEST_LOG_FORMAT': 'XML',
            'BOOST_TEST_LOG_LEVEL': 'message',
            'BOOST_TEST_OUTPUT_FORMAT': 'XML',
            'BOOST_TEST_REPORT_FORMAT': 'XML',
            'BOOST_TEST_RESULT_CODE': 'yes'}
        self.env.default(**defaults)


class OOPSODB(OOPSParallel, odb.OdbComponentDecoMixin):
    """Commons for OOPS using ODB observations."""
    _abstract = True
    _footprint = dict(
        info = "OOPS ObsOperator Test run.",
        attr = dict(
            kind = dict(
                values      = ['oorunodb'],
            ),
        )
    )

    def prepare(self, rh, opts):
        """ODB stuff."""
        super(OOPSODB, self).prepare(rh, opts)
        sh = self.system

        # Looking for input observations
        allodb  = self.lookupodb()
        allcma = [ x for x in allodb if x.rh.resource.layout.lower() == self.virtualdb ]
        cma = allcma.pop()
        cma_path = sh.path.abspath(cma.rh.container.localpath())

        # Set ODB environment
        self.odb.fix_db_path(self.virtualdb, cma_path)
        self.odb.ioassign_gather(cma_path)
        if self.virtualdb == 'ecma':
            self.odb.shuffle_setup(self.slots, mergedirect=True, ccmadirect=False)

        # Look for extras ODB raw
        self.odb_handle_raw_dbs()

        # Look for channels namelists and set appropriate links
        self.setchannels(opts)


class OOPSVar(OOPSODB):
    """Commons for OOPS Test using ODB observations."""

    _footprint = dict(
        info = "OOPS Variational minimization.",
        attr = dict(
            kind = dict(
                values   = ['oovar'],
            ),
        )
    )
