#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger
from vortex.tools.config import GenericConfigParser

_gc = dict()

def geonames(inifile='geometries.ini'):
    """Pre-defined geometries names in configuration file."""
    if not inifile in _gc:
        _gc[inifile] = GenericConfigParser(inifile)
    return _gc[inifile].sections()


class HGeometry(object):
    """Abstract horizontal geometry."""
    
    def __init__(self, **kw):
        logger.debug('Abstract Horizontal Geometry init %s %s', self, kw)
        self.id = 'abstract'
        self.__dict__.update(kw)


class Geometry(object):
    """Abstract geometry."""
    
    def __init__(self, **kw):
        logger.debug('Abstract Geometry init %s %s', self, kw)
        self.id = 'abstract'
        self.area = None
        self.resolution = None
        self.__dict__.update(kw)


class SpectralGeometry(Geometry):
    """
    Horizontal spectral geometry,
    mostly defined through its ``truncation`` and ``stretching`` attributes.
    """
    
    def __init__(self, **kw):
        logger.debug('Spectral Geometry init %s', self)
        self.truncation = 798
        self.stretching = 2.4
        kw.setdefault('area', 'auto')
        super(SpectralGeometry, self).__init__(**kw)

    def lam(self):
        """Boolean: is it a local area model geometry?"""
        return bool(self.resolution)


class GridGeometry(Geometry):
    """
    Horizontal grid points geometry,
    mostly defined through its ``nlon`` and ``nlat`` attributes.
    """

    def __init__(self, **kw):
        logger.debug('Grid Geometry init %s', self)
        self.nlon = 3200
        self.nlat = 1600
        super(GridGeometry, self).__init__(**kw)

    def lam(self):
        """Boolean: is it a local area model geometry?"""
        return False
