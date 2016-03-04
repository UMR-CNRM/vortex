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
        try:
            thisclass = [x for x in Geometry.tag_classes()
                         if x.__name__.lower().startswith(gkind.lower())].pop()
        except IndexError:
            raise AttributeError('Kind={:s} is unknown (for geometry [{:s}])'.format(gkind, item))
        if verbose:
            print '+ Load', item.ljust(16), 'as', thisclass
        if refresh:
            gdesc['new'] = True
        thisclass(tag=item, **gdesc)


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
            ni = None,
            nj = None,
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
        for item in ('nlon', 'nlat', 'ni', 'nj', 'truncation'):
            cv = getattr(self, item)
            if cv is not None:
                setattr(self, item, int(cv))
        for item in ('stretching', 'resolution'):
            cv = getattr(self, item)
            if cv is not None:
                setattr(self, item, float(cv))
        self._check_attributes()

    def _check_attributes(self):
        if self.lam and (self.area is None):
            raise AttributeError("Some mandatory arguments are missing")

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
        # Basics...
        card = "\n".join((
            '{0}Geometry {1!r}',
            '{0}{0}Info       : {2:s}',
            '{0}{0}LAM        : {3:s}',
        )).format(indent, self, self.info, str(self.lam))
        # Optional infos
        for attr in [k for k in ('area', 'resolution', 'truncation',
                                 'stretching', 'nlon', 'nlat', 'ni', 'nj')
                     if getattr(self, k, False)]:
            card += "\n{0}{0}{1:10s} : {2!s}".format(indent, attr.title(),
                                                     getattr(self, attr))
        return card

    def strheader(self):
        """Return beginning of formatted print representation."""
        header = '{0:s}.{1:s} | tag=\'{2}\' id=\'{3:s}\''.format(
            self.__module__,
            self.__class__.__name__,
            self.tag,
            self.info,
        )
        if self.lam:
            header += ' area=\'{0:s}\''.format(self.area)
        return header


class GaussGeometry(HorizontalGeometry):
    """Gaussian grid (stretched or not, rotated or not)."""

    _tag_topcls = False

    def __init__(self, **kw):
        logger.debug('Gauss Geometry init %s', self)
        super(GaussGeometry, self).__init__(**kw)
        self.kind = 'gauss'

    def _check_attributes(self):
        self.lam = False  # Always false for gaussian grid
        if self.truncation is None or self.stretching is None:
            raise AttributeError("Some mandatory arguments are missing")

    def __str__(self):
        """Standard formatted print representation."""
        return '<{0:s} t={1:d} c={2:g}>'.format(self.strheader(), self.truncation, self.stretching)


class ProjectedGeometry(HorizontalGeometry):
    """Geometry defined by a geographical projection on a plane."""

    _tag_topcls = False

    def __init__(self, **kw):
        logger.debug('Projected Geometry init %s', self)
        kw.setdefault('runit', 'km')
        super(ProjectedGeometry, self).__init__(**kw)
        self.kind = 'projected'

    def _check_attributes(self):
        super(ProjectedGeometry, self)._check_attributes()
        if self.resolution is None:
            raise AttributeError("Some mandatory arguments are missing")

    def __str__(self):
        """Standard formatted print representation."""
        return '<{0:s} r=\'{1:s}\'>'.format(self.strheader(), self.rnice)


class LonlatGeometry(HorizontalGeometry):
    """Geometry defined by a geographical projection on plane."""

    _tag_topcls = False

    def __init__(self, **kw):
        logger.debug('Lon/Lat Geometry init %s', self)
        kw.setdefault('runit', 'dg')
        super(LonlatGeometry, self).__init__(**kw)
        self.kind = 'lonlat'

    def __str__(self):
        """Standard formatted print representation."""
        return '<{0:s} r=\'{1:s}\'>'.format(self.strheader(), self.rnice)


class UnstructuredGeometry(HorizontalGeometry):
    """Unstructured grid (curvlinear, finite-elements, ...)."""

    _tag_topcls = False

    def __init__(self, *args, **kw):
        logger.debug('Unstructured Geometry init %s', self)
        super(UnstructuredGeometry, self).__init__(**kw)
        self.kind = 'unstructured'

    def __str__(self):
        """Standard formatted print representation."""
        return '<{0:s}>'.format(self.strheader())


class CurvlinearGeometry(UnstructuredGeometry):

    _tag_topcls = False

    def _check_attributes(self):
        super(CurvlinearGeometry, self)._check_attributes()
        if self.ni is None or self.nj is None:
            raise AttributeError("Some mandatory arguments are missing")

# Load default geometries
load(verbose=False)
