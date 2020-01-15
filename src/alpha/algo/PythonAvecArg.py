#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.algo.components  import Expresso

import iga.util.bpnames as bp

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

class PythonAvecArg(Expresso):

    _footprint = dict (
        attr = dict(
            kind = dict(
                values = ['python_avec_argument']
            ),
	        command_line = dict(
                default = ''
            ),            
            flypoll = dict(
                default = ['iopoll_alpha'],
            ),
            flyargs = dict(
                    values = ['JJ1','J2J3'],
            ),
        )
    )

    def spawn_command_options(self):
	return {'command_line' : self.command_line}

    def prepare(self, rh, opts):
        super(PythonAvecArg, self).prepare(rh, opts)

        if self.promises:
            self.io_poll_kwargs = dict(vconf=rh.resource.vconf.upper())
            print("DBUG1",self.io_poll_kwargs)
            self.flyput = True
        else:
            self.flyput = False


    def execute(self, rh, opts):
        super(PythonAvecArg, self).execute(rh, opts)

    def postfix(self, rh, opts):
        super(PythonAvecArg, self).postfix(rh, opts)



