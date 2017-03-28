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
        t.env.setvar("RD_GCOCACHE", headdir)



    def register_cycle(self, cycle):
        """Load and register a GCO cycle contents."""
        t = vortex.ticket()
        from gco.tools import genv
        if cycle in genv.cycles():
            logger.info('Cycle %s already registred', cycle)
        else:
            if t.env.RD_GCOCACHE:
                genvdef = t.sh.path.join(t.env.RD_GCOCACHE, 'genv', cycle + '.genv')
            else:
                logger.warning('CEN context without RD_GCOCACHE variable')
                genv.autofill(cycle)
            if t.sh.path.exists(genvdef):
                logger.info('Fill GCO cycle with file <%s>', genvdef)
                genv.autofill(cycle, t.sh.cat(genvdef, output=True))
            else:
                logger.error('No contents defined for cycle %s or bad opcycle path %s', cycle, genvdef)
                raise ValueError('Bad cycle value')
            print genv.as_rawstr(cycle=cycle)

