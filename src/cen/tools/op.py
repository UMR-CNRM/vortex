#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from tempfile import mkdtemp

import vortex  # @UnusedImport
import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.actions import actiond as ad
from iga.util import swissknife
from vortex.layout.jobs import JobAssistant


class CenJobAssistant(JobAssistant):

    _footprint = dict(
        info = 'Cen Job assistant.',
        attr = dict(
            kind = dict( 
                values = ['cen'],
            ),
        ),
    )


    def _env_setup(self, t, **kw):
        """OP session's environment setup."""
        super(CenJobAssistant, self)._env_setup(t, **kw)

        headdir = '/home/ext/dsi/mtti/vernaym/dev/'
        t.env.setvar("MTOOLDIR", '/scratch/vernaym/mtool')
        t.env.setvar("DATADIR", headdir + 'opdata')



    def register_cycle(self, cycle):
        """Load and register a cycle contents."""
        from gco.syntax.stdattrs import UgetId
        try:
            cycle = UgetId(cycle)
        except ValueError:
            return
        from gco.tools import uenv
        if cycle in uenv.cycles():
            logger.info('Cycle %s already registered', cycle)
        else:
            uenv.autofill(cycle)
            print(genv.as_rawstr(cycle=cycle))

