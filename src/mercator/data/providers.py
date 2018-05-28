#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.providers import Provider
from vortex.syntax.stdattrs import namespacefp

#: No automatic export
__all__ = []


class MercatorArchive(Provider):

    _footprint = [
        namespacefp,
        dict(
            info = 'Mercator archive provider',
            attr = dict(
                namespace = dict(
                    optional = False,
                    default = 'mercator.archive.fr',
                    values = ['mercator.archive.fr', ]
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'mercator'

    def scheme(self, resource):
        return 'mercator'

    def netloc(self, resource):
        return self.namespace

    def pathname(self, resource):
        rinfo = self.pathinfo(resource)
        return '/'.join((
            'chains/oper/glo',
            rinfo.get('grid', ''),
            rinfo.get('path', '')
        ))
