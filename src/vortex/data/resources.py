#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: Export Resource and associated Catalog classes.
__all__ = [ 'Resource' ]

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.syntax.stdattrs import a_nativefmt, notinrepr
from contents import DataContent, UnknownContent


class Resource(footprints.FootprintBase):

    _abstract  = True
    _collector = ('resource',)
    _footprint = dict(
        info = 'Abstract NWP Resource',
        attr = dict(
            nativefmt = a_nativefmt,
            clscontents = dict(
                type     = DataContent,
                isclass  = True,
                optional = True,
                default  = UnknownContent,
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Resource init %s', self.__class__)
        super(Resource, self).__init__(*args, **kw)
        self._mailbox = footprints.util.LowerCaseDict()

    @property
    def realkind(self):
        return 'resource'

    def _str_more(self):
        """Return a string representation of meaningful attributes for formatted output."""
        d = self.footprint_as_dict()
        for xdel in [ x for x in notinrepr if x in d ]:
            del d[xdel]
        return ' '.join([ '{0:s}=\'{1:s}\''.format(k, str(v)) for k, v in d.items() ])

    @property
    def mailbox(self):
        """A nice cocoon to store miscellaneous information."""
        return self._mailbox

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
        """Duck typing: return an empty string by default."""
        return ''

    def genv_basename(self):
        """Proxy to :meth:`gget_basename`."""
        return self.gget_basename()

    def gget_urlquery(self):
        """Duck typing: return an empty string by default."""
        return ''

    def genv_urlquery(self):
        """Proxy to :meth:`gget_urlquery`."""
        return self.gget_urlquery()

    def contents_args(self):
        """Returns default arguments value to class content constructor."""
        return dict()

    def contents_handler(self, **kw):
        """Returns class content handler according to attribute ``clscontents``."""
        this_args = self.contents_args()
        this_args.update(kw)
        return self.clscontents(**this_args)


class Unknown(Resource):

    _footprint = dict(
        info = 'Unknown assumed NWP Resource',
        attr = dict(
            unknown = dict(
                type = bool
            )
        )
    )


