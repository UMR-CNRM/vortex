#!/bin/env python
# -*- coding:Utf-8 -*-

#: Export Resource and associated Catalog classes.
__all__ = [ 'Resource', 'ResourcesCatalog' ]

import logging, re, sys

from vortex.syntax import BFootprint
from vortex.syntax.stdattrs import a_nativefmt
from vortex.utilities.catalogs import ClassesCollector, cataloginterface
from contents import DataContent, DataRaw


class Resource(BFootprint):

    _footprint = dict(
        info = 'Abstract NWP Resource',
        attr = dict(
            nativefmt = a_nativefmt,
            clscontents = dict(
                type = DataContent,
                isclass = True,
                optional = True,
                default = DataRaw
            )
        )
    )

    def __init__(self, *args, **kw):
        logging.debug('Resource init %s', self)
        super(Resource, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'resource'

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

    def contents_handler(self):
        """Returns class content handler according to attribute ``clscontents``."""
        cclass = self.clscontents
        return cclass()


class ResourcesCatalog(ClassesCollector):

    def __init__(self, **kw):
        logging.debug('Resources catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*(?:resources|data)'),
            classes = [ Resource ],
            itementry = Resource.realkind()
        )
        cat.update(kw)
        super(ResourcesCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        """The entry used in the global catalogs table, eg: ``resources``."""
        return 'resources'

cataloginterface(sys.modules.get(__name__), ResourcesCatalog)
