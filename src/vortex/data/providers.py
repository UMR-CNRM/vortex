#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = [ 'Provider' ]

import os.path

import footprints

from vortex.autolog import logdefault as logger
from vortex.util.names import VortexNameBuilder
from vortex.tools import net


class Provider(footprints.FootprintBase):

    _abstract  = True
    _collector = ('provider',)
    _footprint = dict(
        info = 'Abstract root provider',
        attr = dict(
            vapp = dict(
                alias    = ('application',),
                optional = True,
                default  = '[glove::vapp]'
            ),
            vconf = dict(
                alias    = ('configuration',),
                optional = True,
                default  = '[glove::vconf]'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract provider init %s', self.__class__)
        super(Provider, self).__init__(*args, **kw)

    def _str_more(self):
        """Additional information to print representation."""
        try:
            return 'namespace=\'{0:s}\''.format(self.namespace)
        except AttributeError:
            return super(Provider, self)._str_more()

    @property
    def realkind(self):
        return 'provider'

    def scheme(self):
        """Abstract method."""
        pass

    def domain(self):
        """Abstract method."""
        pass

    def pathname(self, resource):
        """Abstract method."""
        pass

    def pathinfo(self, resource):
        """Delegates to resource eponym method."""
        return resource.pathinfo(self.realkind)

    def basename(self, resource):
        """Delegates to resource eponym method."""
        return resource.basename(self.realkind)

    def urlquery(self, resource):
        """Delegates to resource eponym method."""
        return resource.urlquery(self.realkind)

    def uri(self, resource):
        """
        Create an uri adapted to a vortex resource so as to allow the element
        in charge of retrieving the real resource to be able to locate and
        retreive it. The method used to achieve this action:

        * obtain the proto information,
        * ask for the domain,
        * get the pathname,
        * get the basename.

        The different operations of the algorithm can be redefined by subclasses.
        """
        logger.debug(
            'scheme %s domain %s normpath %s urlquery %s',
            self.scheme(), self.domain(),
            os.path.normpath(self.pathname(resource) + '/' +
            self.basename(resource)),
            self.urlquery(resource)
        )

        return net.uriunparse((
            self.scheme(),
            self.domain(),
            os.path.normpath(self.pathname(resource) + '/' + self.basename(resource)),
            None,
            self.urlquery(resource),
            None
        ))


class Magic(Provider):

    _footprint = dict(
        info = 'Magic provider',
        attr = dict(
            fake = dict(
                alias    = ('nowhere', 'noprovider'),
                type     = bool,
                optional = True,
                default  = True,
            ),
            magic = dict()
        )
    )

    @property
    def realkind(self):
        return 'magic'

    def uri(self, resource):
        """URI is supposed to be the magic value !"""
        return self.magic


class Remote(Provider):

    _footprint = dict(
        info = 'Remote provider',
        attr = dict(
            remote = dict(
                alias    = ('remfile', 'rempath'),
            ),
            hostname = dict(
                optional = True,
                default  = 'localhost'
            ),
            tube = dict(
                optional = True,
                values   = ['scp', 'ftp', 'rcp', 'file'],
                default  = 'file',
            ),
            username = dict(
                optional = True,
                default  = None,
                alias    = ('user', 'logname')
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Remote provider init %s', self.__class__)
        super(Remote, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'remote'

    def _str_more(self):
        """Additional information to print representation."""
        return 'path=\'{0:s}\''.format(self.remote)

    def scheme(self):
        """The Remote scheme is its tube."""
        return self.tube

    def domain(self):
        """Fully qualified network domain."""
        if self.username:
            return self.username + '@' + self.hostname
        else:
            return self.hostname

    def pathname(self, resource):
        """OS dirname of the ``remote`` attribute."""
        return os.path.dirname(self.remote)

    def basename(self, resource):
        """OS basename of the ``remote`` attribute."""
        return os.path.basename(self.remote)

    def urlquery(self, resource):
        """Check for relative path or not."""
        if self.remote.startswith('/'):
            return None
        else:
            return 'relative=1'


class Vortex(Provider):

    _footprint = dict(
        info = 'Vortex provider',
        attr = dict(
            experiment = dict(),
            block = dict(),
            member = dict(
                type     = int,
                optional = True,
            ),
            namespace = dict(
                optional = True,
                values   = ['vortex.cache.fr', 'vortex.archive.fr', 'vortex.multi.fr',
                            'open.cache.fr', 'open.archive.fr'],
                default  = 'vortex.cache.fr',
                remap    = {
                    'open.cache.fr': 'vortex.cache.fr',
                    'open.archive.fr': 'vortex.archive.fr',
                }
            ),
            namebuild = dict(
                optional = True,
                type     = VortexNameBuilder,
                default  = VortexNameBuilder(),
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex experiment provider init %s', self.__class__)
        super(Vortex, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'vortex'

    def _str_more(self):
        """Additional information to print representation."""
        try:
            return 'namespace=\'{0:s}\' block=\'{1:s}\''.format(self.namespace, self.block)
        except AttributeError:
            return super(Provider, self)._str_more()

    def scheme(self):
        """Default: ``vortex``."""
        return self.realkind

    def domain(self):
        """Returns the current ``namespace``."""
        return self.namespace

    def pathname(self, resource):
        """Constructs pathname of the ``resource`` according to :func:`pathinfo`."""
        rinfo = self.pathinfo(resource)
        rdate = rinfo.get('date', '')
        if rdate:
            rdate = rdate.vortex(rinfo.get('cutoff', 'n'))
        return '/'.join((
            self.vapp,
            self.vconf,
            self.experiment,
            rdate,
            self.block
        ))

    def basename(self, resource):
        """
        Constructs basename according to current ``namebuild`` factory
        and resource :func:`basname_info`.
        """
        return self.namebuild.pack(resource.basename_info())

