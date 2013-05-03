#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.providers import Provider


class MercatorArchive(Provider):

    _footprint = dict(
        info = 'Mercator archive provider',
        attr = dict(
            namespace = dict(
                optional = True,
                default = 'mercator.archive.fr'
            ),
        )
    )

    @property
    def realkind(self):
        return 'mercator'
    
    def scheme(self):
        return 'mercator'
    
    def domain(self):
        return self.namespace

    def pathname(self, resource):
        rinfo = self.pathinfo(resource)
        return '/'.join((
          'chains/oper/glo', 
          rinfo.get('grid', ''), 
          rinfo.get('path', '')
        ))
