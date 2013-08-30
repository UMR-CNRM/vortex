#!/bin/env python
# -*- coding:Utf-8 -*-

#: Export Resource and associated Catalog classes.
__all__ = [ 'Resource', 'ResourcesCatalog' ]

import re, sys
from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.syntax.stdattrs import a_nativefmt, a_format, notinrepr
from vortex.utilities.catalogs import ClassesCollector, build_catalog_functions
from contents import DataContent, DataRaw


class Resource(BFootprint):

    _footprint = dict(
        info = 'Abstract NWP Resource',
        attr = dict(
            nativefmt = a_nativefmt,
            format = a_format,
            clscontents = dict(
                type = DataContent,
                isclass = True,
                optional = True,
                default = DataRaw
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Resource init %s', self)
        super(Resource, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'resource'

    @classmethod
    def classkind(cls):
        return cls.realkind.fget(cls)

    def addrepr(self):
        """Return a string representation of meaningful attributes for formatted output."""
        d = self.puredict()
        for xdel in [ x for x in notinrepr if x in d ]:
            del d[xdel]
        return '| ' + ' '.join([ '{0:s}=\'{1:s}\''.format(k, str(v)) for k, v in d.items() ])

    def vortex_pathinfo(self):
        """
        Returns anonymous dict with suitable informations from vortex point of view.
        Doomed to be overwritten.
        """
        return dict(
            nativefmt = self.nativefmt
        )

    def pathinfo(self, provider):
        """Proxy to the appropriate method prefixed by provider name."""
        actualpathinfo = getattr(self, provider + '_pathinfo', self.vortex_pathinfo)
        return actualpathinfo()

    def vortex_basename(self):
        """Abstract method."""
        pass

    def basename(self, provider):
        """Proxy to the appropriate method prefixed by provider name."""
        actualbasename = getattr(self, provider + '_basename', self.vortex_basename)
        return actualbasename()

    def basename_info(self):
        """
        Returns anonymous dict with suitable informations from vortex point of view.
        In real world, probably doomed to return an empty dict.
        """
        return dict()

    def vortex_urlquery(self):
        """Query to be binded to the resource's location in vortex space."""
        return None

    def urlquery(self, provider):
        """Proxy to the appropriate method prefixed by provider name."""
        actualurlquery = getattr(self, provider + '_urlquery', self.vortex_urlquery)
        return actualurlquery()    

    def gget_basename(self):
        return ''

    def genv_basename(self):
        return self.gget_basename()

    def gget_urlquery(self):
        return ''

    def genv_urlquery(self):
        return self.gget_urlquery()

    def contents_handler(self, **kw):
        """Returns class content handler according to attribute ``clscontents``."""
        cclass = self.clscontents
        return cclass(**kw)


class Unknown(Resource):

    _footprint = dict(
        info = 'Unknown assumed NWP Resource',
        attr = dict(
            unknown = dict(
                type = bool
            )
        )
    )

    @property
    def realkind(self):
        return 'unknown'


class ResourcesCatalog(ClassesCollector):

    def __init__(self, **kw):
        """
        Define defaults regular expresion for module search, list of tracked classes
        and the item entry name in pickled footprint resolution.
        """
        logger.debug('Resources catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*(?:resources|data)'),
            classes = [ Resource ],
            itementry = 'resource',
        )
        cat.update(kw)
        super(ResourcesCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        """The entry point for global catalogs table. -- Here: resources."""
        return 'resources'

build_catalog_functions(sys.modules.get(__name__), ResourcesCatalog)
