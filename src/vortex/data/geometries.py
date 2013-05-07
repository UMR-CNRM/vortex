#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger
from vortex.tools.config import GenericConfigParser


def geoset(inifile=None, _gc=dict()):
    if inifile:
        _gc[inifile] = GenericConfigParser(inifile + '.ini')
    return _gc

def defaultnames(fromset='geometries'):
    """Pre-defined geometries names in configuration file."""
    gs = geoset()
    if fromset.endswith('.ini'):
        fromset = fromset.rstrip('.ini')
    if fromset not in gs:
        geoset(fromset) 
    return gs[fromset].sections()

def getbyname(geoname, fromset='geometries'):
    """Return a geometry object according to default initialisation set."""
    if geoname not in defaultnames(fromset=fromset):
        logger.warning('Could not provide any geometry called %s', geoname)
        return None
    gs = geoset()
    desc = dict(gs[fromset].items(geoname))
    kind = desc['kind']
    del desc['kind']
    if kind in ('spectral', 'global'):
        return SpectralGeometry(**desc)
    else:
        return GridGeometry(**desc)

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
        self.nlon = None
        self.nlat = None
        self.resolution = None
        self.truncation = None
        self.stretching = None
        self.__dict__.update(kw)
        for k, v in self.__dict__.items():
            if v == 'none':
                self.__dict__[k] = None
        for item in ('nlon', 'nlat', 'truncation'):
            cv = getattr(self, item)
            if cv != None:
                setattr(self, item, int(cv))
        for item in ('stretching', 'resolution'):
            cv = getattr(self, item)
            if cv != None:
                setattr(self, item, float(cv))

    def idcard(self, indent=2):
        """
        Returns a multilines documentation string with a summary
        of the valuable information contained by this geometry.
        """
        indent = ' ' * indent
        card = "\n".join((
            '{0}Geometry {1!r}',
            '{0}{0}Id         : {2:s}',
            '{0}{0}Resolution : {3:s}',
            '{0}{0}Truncation : {4:s}',
            '{0}{0}Stretching : {5:s}',
            '{0}{0}Area       : {6:s}',
            '{0}{0}Local      : {7:s}',
            '{0}{0}NLon       : {8:s}',
            '{0}{0}NLat       : {9:s}',
        )).format(
            indent,
            self, self.id, str(self.resolution), str(self.truncation), str(self.stretching),
            str(self.area), str(self.lam()), str(self.nlon), str(self.nlat)
        )
        return card


class SpectralGeometry(Geometry):
    """
    Horizontal spectral geometry,
    mostly defined through its ``truncation`` and ``stretching`` attributes.
    """
    
    def __init__(self, **kw):
        logger.debug('Spectral Geometry init %s', self)
        kw.setdefault('truncation', 798)
        kw.setdefault('stretching', 2.4)
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
        kw.setdefault('nlon', 3200)
        kw.setdefault('nlat', 1600)
        super(GridGeometry, self).__init__(**kw)

    def lam(self):
        """Boolean: is it a local area model geometry?"""
        return self.truncation and not self.stretching
