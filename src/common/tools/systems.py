#!/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common system interfaces used at Meteo France.
"""

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger

from vortex.tools.systems import OSExtended


class SuperUX(OSExtended):
    """NEC Operating System."""

    _footprint = dict(
        info = 'NEC operating system',
        attr = dict(
            sysname = dict(
                values = [ 'SUPER-UX' ]
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('SuperUX system init %s', self.__class__)
        self._psopts = kw.setdefault('psopts', ['-f'])
        del kw['psopts']
        super(SuperUX, self).__init__(*args, **kw)
        if self.hostname == 'unix':
            hl = self.spawn(['hostname'])
            if len(hl) > 0:
                self._attributes['hostname'] = hl[0]

    @property
    def realkind(self):
        return 'super-ux'

    def rawcp(self, source, destination):
        """NEC SX raw copy is a spawn of the shell cp."""
        self.spawn(['cp', source, destination], output=False)
        return bool(self.path.isfile(destination) and self.size(source) == self.size(destination))
