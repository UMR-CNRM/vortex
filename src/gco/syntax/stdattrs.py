#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`vortex.syntax.footprint.Footprint` syntax.
"""

import re
 
#: Export some new class for attributes in footprint objects, eg : GenvKey
__all__ = [ 'GenvKey', 'GenvDomain' ]

domain_remap = dict(
    caledonie = 'NCAL'
)

def lowerattr(matchobj):
    return matchobj.group(0).lower()
    
class GenvKey(str):
    """
    Attribute for a GEnv cycle name.
    Implicit attributes inside brackets are translated to lower case.
    See also :mod:`gco.tools.genv`.
    """

    def __new__(cls, value):
        return str.__new__(cls, re.sub('\[\w+\]', lowerattr, value.upper()))

class GenvDomain(str):
    """
    Remap plain area names to specific Genv short domain names.
    See also :mod:`gco.tools.genv`.
    """
    
    def __new__(cls, value):
        return str.__new__(cls, domain_remap.get(value, value))