#!/bin/env python
# -*- coding:Utf-8 -*-

#: Automatic export of MiscGenv
__all__ = [ 'MiscGenv' ]


from vortex.data.outflow import NoDateResource
from gco.syntax.stdattrs import GenvKey


class MiscGenv(NoDateResource):
    """
    Base classe for genv-only kind of resources.
    
    Extended footprint:
    
    * gvar (type :class:`gco.syntax.stdattrs.GenvKey`)
    * kind (values: ``miscgenv``)
    """
    
    _footprint = dict(
        info = 'Miscellaneous genv constant',
        attr = dict(
            gvar = dict(
              	type = GenvKey,
              	optional = True,
            ),
            kind = dict(
                values = [ 'miscgenv' ]
            )
      	)
    )
 
    @property
    def realkind(self):
        """Default realkind is ``miscgenv``."""
        return 'miscgenv' 

