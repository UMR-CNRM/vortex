#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re
import types

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
    desc.setdefault('id', geoname)
    if kind in ('spectral', 'global'):
        return SpectralGeometry(**desc)
    else:
        return GridGeometry(**desc)


class Geometry(object):
    """Abstract geometry."""

    def __init__(self, **kw):
        logger.debug('Abstract Geometry init %s %s', self, kw)
        self.id = 'anonymous'
        self.hgeo = None
        self.vgeo = None
        self.__dict__.update(kw)


class HGeometry(object):
    """Abstract horizontal geometry."""

    def __new__(cls, *args, **kw):
        if args:
            hg = getbyname(args[0].lower())
            hg.initialised = True
        else:
            hg = super(HGeometry, cls).__new__(cls)
            hg.initialised = False
        return hg

    def __init__(self, *args, **kw):
        logger.debug('Abstract Horizontal Geometry init %s %s', self, kw)
        if not self.initialised:
            self.id = 'anonymous'
            self.area = None
            self.nlon = None
            self.nlat = None
            self.resolution = 0.
            self.truncation = None
            self.stretching = None
            self.lam = True
            self.__dict__.update(kw)
            for k, v in self.__dict__.items():
                if isinstance(v, basestring) and re.match('none', v, re.IGNORECASE):
                    self.__dict__[k] = None
                if isinstance(v, basestring) and re.match('true', v, re.IGNORECASE):
                    self.__dict__[k] = True
                if isinstance(v, basestring) and re.match('false', v, re.IGNORECASE):
                    self.__dict__[k] = False
            for item in ('nlon', 'nlat', 'truncation'):
                cv = getattr(self, item)
                if cv is not None:
                    setattr(self, item, int(cv))
            for item in ('stretching', 'resolution'):
                cv = getattr(self, item)
                if cv is not None:
                    setattr(self, item, float(cv))

    @property
    def gam(self):
        return not self.lam

    @property
    def rnice(self):
        if self.runit == 'km':
            res = '{0:05.2f}'.format(self.resolution)
        else:
            res = '{0:06.3f}'.format(self.resolution)
        return re.sub(r'\.', self.runit, res, 1)

    def anonymous_info(self, *args):
        """Try to build a meaningful information from an anonymous geometry."""
        return '{0:s}, {1:s}'.format( self.area, self.rnice)

    def __str__(self):
        """Very short presentation."""
        if self.id == 'anonymous':
            return '{0:s}({1:s})'.format(self.__class__.__name__, self.anonymous_info())
        else:
            return self.id

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
            str(self.area), str(self.lam), str(self.nlon), str(self.nlat)
        )
        return card

    def strheader(self):
        """Return beginning of formatted print representation."""
        return '{0:s}.{1:s} | id=\'{2:s}\' area=\'{3:s}\''.format(self.__module__,
                                                                  self.__class__.__name__,
                                                                  self.id, self.area)


class SpectralGeometry(HGeometry):
    """
    Horizontal spectral geometry,
    mostly defined through its ``truncation`` and ``stretching`` attributes.
    """

    def __init__(self, *args, **kw):
        logger.debug('Spectral Geometry init %s', self)
        kw.setdefault('runit', 'km')
        super(SpectralGeometry, self).__init__(**kw)
        self.kind = 'spectral'

    def __str__(self):
        """Standard formatted print representation."""
        if self.lam:
            return '<{0:s} r=\'{1:s}\'>'.format(self.strheader(), self.rnice)
        else:
            return '<{0:s} t={1:d} c={2:g}>'.format(self.strheader(), self.truncation, self.stretching)


class GridGeometry(HGeometry):
    """
    Horizontal grid points geometry,
    mostly defined through its ``nlon`` and ``nlat`` attributes.
    """

    def __init__(self, *args, **kw):
        logger.debug('Grid Geometry init %s', self)
        kw.setdefault('nlon', 3200)
        kw.setdefault('nlat', 1600)
        kw.setdefault('runit', 'dg')
        super(GridGeometry, self).__init__(**kw)
        self.kind = 'grid'
        self.truncation = None
        self.stretching = None

    def __str__(self):
        """Standard formatted print representation."""
        return '<{0:s} r=\'{1:s}\'>'.format(self.strheader(), self.rnice)
