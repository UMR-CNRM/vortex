#!/bin/env python
# -*- coding:Utf-8 -*-

import logging
from vortex.data.providers import Provider


class Bidon(Provider):

    _footprint = dict(
        info = 'Some bidon provider',
        attr = dict(
            bidon = dict(
                alias = ( 'bidul', 'machine' )
            )
        )
    )

    def __init__(self, *args, **kw):
        logging.debug('Bidon provider init %s', self)
        super(Bidon, self).__init__(*args, **kw)

    def realkind(self):
        return 'bidon'
