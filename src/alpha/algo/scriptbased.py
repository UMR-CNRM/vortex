#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.algo.components import Expresso

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class AlphaScript(Expresso):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['alphascript'],
            ),
            command_line = dict(
                default = '',
            ),
            flypoll = dict(
                default = ['iopoll_alpha'],
            ),
            flyargs = dict(
                values = ['JJ1', 'J2J3'],
            ),
        )
    )

    def spawn_command_options(self):
        return {'command_line': self.command_line}

    def prepare(self, rh, opts):
        super(AlphaScript, self).prepare(rh, opts)

        if self.promises:
            self.io_poll_kwargs = dict(vconf=rh.resource.vconf.upper())
            self.flyput = True
        else:
            self.flyput = False
