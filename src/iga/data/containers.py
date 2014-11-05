#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger
from vortex.data.containers import Container


class Bidon(Container):

    _footprint = dict(
        info = 'Some bidon container',
        attr = dict(
            bidon = dict(
                alias = ( 'bidul', 'machine' )
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Bidon container init %s', self.__class__)
        super(Bidon, self).__init__(*args, **kw)

