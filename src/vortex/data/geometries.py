#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.util.config import GenericConfigParser

# Module Interface

def get(**kw):
    """Return actual geometry object matching description."""
    return Geometry(**kw)

def keys():
    """Return the list of current names of geometries collected."""
    return Geometry.tag_keys()

def values():
    """Return the list of current values of geometries collected."""
    return Geometry.tag_values()

def items():
    """Return the items of the geometries table."""
    return Geometry.tag_items()

def load(inifile='geometries.ini', refresh=False, verbose=True):
    """Load a set of pre-defined geometries from a configuration file."""
    iniconf = GenericConfigParser(inifile)
    for item in iniconf.sections():
        gdesc = dict(iniconf.items(item))
        gkind = gdesc.get('kind')
        thisclass = [ x for x in Geometry.tag_classes() if x.__name__.lower().startswith(gkind.lower()) ].pop()
        if verbose:
            print '+ Load', item.ljust(16), 'as', thisclass
        if refresh:
            gdesc['new'] = True
        gnew = thisclass(tag=item, **gdesc)

def grep(**kw):
    """Grep items that match the set of attributes given as named arguments."""
    okmatch = list()
    for item in Geometry.tag_values():
        ok = True
        for k, v in kw.items():
            if not hasattr(item, k) or getattr(item, k) != v:
                ok = False
                break
        if ok:
            okmatch.append(item)
    return okmatch


class Geometry(footprints.util.GetByTag):
    """Abstract geometry."""

    def __init__(self, **kw):
        logger.debug('Abstract Geometry init %s %s', self, kw)
        self.info    = 'anonymous'
        self.inifile = None
        self.__dict__.update(kw)

    @classmethod
    def tag_clean(self, tag):
        """Geometries id tags are lower case."""
        return tag.lower()


class CombinedGeometry(Geometry):
    """Combine horizontal and vertical geometry."""

    _tag_topcls = False

    def __init__(self, **kw):
        logger.debug('Combined Geometry init %s %s', self, kw)
        self.info = 'anonymous'
        self.hgeo = None
        self.vgeo = None
        super(CombinedGeometry, self).__init__(**kw)


class VerticalGeometry(Geometry):
    """Handle vertical geometry description."""

    _tag_topcls = False

    def __init__(self, **kw):
        logger.debug('Abstract Vertital Geometry init %s %s', self, kw)
        super(VerticalGeometry, self).__init__(**kw)


class HorizontalGeometry(Geometry):
    """Handle abstract horizontal geometry description."""

    _tag_topcls = False

    def __init__(self, **kw):
        logger.debug('Abstract Horizontal Geometry init %s %s', self, kw)
        desc = dict(
            info = 'anonymous',
            area = None,
            nlon = None,
            nlat = None,
            resolution = 0.,
            truncation = None,
            stretching = None,
            lam = True,
        )
        desc.update(kw)
        super(HorizontalGeometry, self).__init__(**desc)
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
        return '{0:s}, {1:s}'.format(self.area, self.rnice)

    def __str__(self):
        """Very short presentation."""
        if self.info == 'anonymous':
            return '{0:s}({1:s})'.format(self.__class__.__name__, self.anonymous_info())
        else:
            return self.info

    def idcard(self, indent=2):
        """
        Returns a multilines documentation string with a summary
        of the valuable information contained by this geometry.
        """
        indent = ' ' * indent
        card = "\n".join((
            '{0}Geometry {1!r}',
            '{0}{0}Info       : {2:s}',
            '{0}{0}Resolution : {3:s}',
            '{0}{0}Truncation : {4:s}',
            '{0}{0}Stretching : {5:s}',
            '{0}{0}Area       : {6:s}',
            '{0}{0}Local      : {7:s}',
            '{0}{0}NLon       : {8:s}',
            '{0}{0}NLat       : {9:s}',
        )).format(
            indent,
            self, self.info, str(self.resolution), str(self.truncation), str(self.stretching),
            str(self.area), str(self.lam), str(self.nlon), str(self.nlat)
        )
        return card

    def strheader(self):
        """Return beginning of formatted print representation."""
        return '{0:s}.{1:s} | id=\'{2:s}\' area=\'{3:s}\''.format(
            self.__module__,
            self.__class__.__name__,
            self.info,
            self.area
        )


class SpectralGeometry(HorizontalGeometry):
    """
    Horizontal spectral geometry,
    mostly defined through its ``truncation`` and ``stretching`` attributes.
    """

    _tag_topcls = False

    def __init__(self, **kw):
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


class GridGeometry(HorizontalGeometry):
    """
    Horizontal grid points geometry,
    mostly defined through its ``nlon`` and ``nlat`` attributes.
    """

    _tag_topcls = False

    def __init__(self, *args, **kw):
        logger.debug('Grid Geometry init %s', self)
        kw.setdefault('nlon', 3200)
        kw.setdefault('nlat', 1600)
        kw.setdefault('runit', 'dg')
        super(GridGeometry, self).__init__(**kw)
        self.kind       = 'grid'
        self.truncation = None
        self.stretching = None

    def __str__(self):
        """Standard formatted print representation."""
        return '<{0:s} r=\'{1:s}\'>'.format(self.strheader(), self.rnice)

# Load default geometries
load(verbose=False)
