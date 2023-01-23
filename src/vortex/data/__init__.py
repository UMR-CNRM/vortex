"""
Abstract classes involved in data management within VORTEX.

Actual resources and custom providers should be defined in dedicated packages.
"""

from . import handlers, resources, containers, contents, providers, \
    executables, stores, geometries

#: No automatic export
__all__ = []

__tocinfoline__ = 'Abstract classes involved in data management within VORTEX'
