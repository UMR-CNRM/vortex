#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from vortex.syntax.stdattrs import a_nativefmt, notinrepr
from .contents import DataContent, UnknownContent, FormatAdapter

#: Export Resource and associated Catalog classes.
__all__ = [ 'Resource' ]

logger = footprints.loggers.getLogger(__name__)


class Resource(footprints.FootprintBase):

    _abstract  = True
    _collector = ('resource',)
    _footprint = dict(
        info = 'Abstract NWP Resource',
        attr = dict(
            nativefmt = a_nativefmt,
            clscontents = dict(
                info            = "The class instantiated to read the container's content",
                type            = DataContent,
                isclass         = True,
                optional        = True,
                default         = UnknownContent,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            )
        ),
        fastkeys = set(['kind', 'nativefmt', ]),
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
        d = self.footprint_as_shallow_dict()
        for xdel in [ x for x in notinrepr if x in d ]:
            del d[xdel]
        return ' '.join(['{0:s}=\'{1!s}\''.format(k, v) for k, v in d.items()])

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

    def uget_basename(self):
        """Proxy to :meth:`gget_basename`."""
        return self.gget_basename()

    def genv_basename(self):
        """Just retrieve a potential gvar attribute."""
        return getattr(self, 'gvar', '')

    def uenv_basename(self):
        """Proxy to :meth:`genv_basename`."""
        return self.genv_basename()

    def cendev_basename(self):
        """Basename for the CEN Soprano provider."""
        raise NotImplementedError('This resource is not CENdev ready.')

    def gget_urlquery(self):
        """Duck typing: return an empty string by default."""
        return ''

    def uget_urlquery(self):
        """Proxy to :meth:`gget_urlquery`."""
        return self.gget_urlquery()

    def genv_urlquery(self):
        """Proxy to :meth:`gget_urlquery`."""
        return self.gget_urlquery()

    def uenv_urlquery(self):
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
        info = 'Unknown assumed NWP Resource (development only !)',
        attr = dict(
            unknown = dict(
                info = "Activate the unknown resource.",
                type = bool
            ),
            nickname = dict(
                info = "The string that serves the purpose of Vortex's basename radical",
                optional = True,
                default = 'unknown'
            ),
            clscontents = dict(
                default = FormatAdapter,
            ),
        ),
        fastkeys = set(['unknown', ]),
    )

    def basename_info(self):
        """Keep the Unknown resource unknown."""
        bdict = dict(radical=self.nickname, )
        if self.nativefmt not in ('auto', 'autoconfig', 'foo', 'unknown'):
            bdict['fmt'] = self.nativefmt
        return bdict


# Activate the footprint's fasttrack on the resources collector
fcollect = footprints.collectors.get(tag='resource')
fcollect.fasttrack = ('kind', )
del fcollect
