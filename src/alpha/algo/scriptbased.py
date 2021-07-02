# -*- coding: utf-8 -*-

"""
Add some args when the script shell is executed.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.algo.components import Expresso

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class AlphaScript(Expresso):
    """Run the main Alpha script."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['alphascript'],
            ),
            command_line = dict(
                default = '',
            ),
            flypoll = dict(
                values = ['iopoll_alpha'],
                optional = True,
            ),
            flyargs = dict(
                default = ('alpha',),
            ),
        )
    )

    def spawn_command_options(self):
        """The command line is simply taken in the footprint."""
        return {'command_line': self.command_line}

    def prepare(self, rh, opts):
        """Setup things prior to run"""
        super(AlphaScript, self).prepare(rh, opts)
        if self.promises:
            self.io_poll_kwargs = dict(domain=rh.provider.vconf)
            self.flyput = True
        else:
            self.flyput = False
