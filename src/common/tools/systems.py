#!/bin/env python
# -*- coding: utf-8 -*-

"""
This package handles some common system interfacesused at Meteo France.
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

    @classmethod
    def realkind(cls):
        return 'super-ux'

    def cp(self, source, destination):
        """
        Copy the ``source`` file to a safe ``destination``.
        The return value is produced by a raw compare of the two files.
        """
        if type(source) != str or type(destination) != str:
            return self.hybridcp(source, destination)
        if self.filecocoon(destination):
            self.spawn(['cp', source, destination], output=False)
            return bool(self.size(source) == self.size(destination))
        else:
            logger.error('Could not create cocoon for %s', destination)
            return False
