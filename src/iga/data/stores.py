#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import logging

from vortex.data.stores import Finder

class IgaFinder(Finder):
    """
    Inline disk store for operational data resources produced outside
    of the vortex scope.
    """

    _footprint = dict(
        info = 'Iga file access',
        attr = dict(
            netloc = dict(
                values = [ 'oper.inline.fr', 'oper' ],
            ),
            rootdir = dict(
                alias = [ 'suitehome' ],
                optional = True,
                default = '/ch/mxpt/mxpt001'
            )
        )
    )

    def __init__(self, *args, **kw):
        logging.debug('IgaFinder store init %s', self.__class__)
        super(IgaFinder, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'igafinder'

    def hostname(self):
        return self.netloc

    def _realpath(self, remote):
        if remote['query'].get('relative', False):
            return remote['path'].lstrip('/')
        else:
            return self.rootdir  + remote['path']

