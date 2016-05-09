#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = ['Provider']

import os.path

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.syntax.stdattrs import a_xpid, opsuites, Namespace, FmtInt
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

    def netloc(self):
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
        * ask for the netloc,
        * get the pathname,
        * get the basename.

        The different operations of the algorithm can be redefined by subclasses.
        """
        logger.debug(
            'scheme %s netloc %s normpath %s urlquery %s',
            self.scheme(),
            self.netloc(),
            os.path.normpath(self.pathname(resource) + '/' + self.basename(resource)),
            self.urlquery(resource)
        )

        return net.uriunparse((
            self.scheme(),
            self.netloc(),
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

    def netloc(self):
        """Fully qualified network location."""
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
    """Main provider of the toolbox, using a fix-size path and a dedicated name factory."""

    _abstract = True
    _footprint = dict(
        info = 'Vortex provider',
        attr = dict(
            experiment = a_xpid,
            block = dict(),
            member = dict(
                type    = FmtInt,
                args    = dict(fmt = '03'),
                optional = True,
            ),
            namespace = dict(
                type     = Namespace,
                optional = True,
                values   = [
                    'vortex.cache.fr', 'vortex.archive.fr', 'vortex.multi.fr',
                    'open.cache.fr',   'open.archive.fr',   'open.multi.fr',
                ],
                default  = Namespace('vortex.cache.fr'),
                remap    = {
                    'open.cache.fr'   : 'vortex.cache.fr',
                    'open.archive.fr' : 'vortex.archive.fr',
                    'open.multi.fr'   : 'vortex.multi.fr',
                }
            ),
            namebuild = dict(
                optional = True,
                type     = VortexNameBuilder,
                default  = VortexNameBuilder(),
            ),
            expected = dict(
                alias    = ('promised',),
                type     = bool,
                optional = True,
                default  = False,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex experiment provider init %s', self.__class__)
        super(Vortex, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'vortex'

    def footprint_export_namebuild(self):
        """Return the ``namebuild`` (class content type) attribute as a (module, name) tuple."""
        return (self.namebuild.__module__, self.namebuild.__class__.__name__)

    def _str_more(self):
        """Additional information to print representation."""
        try:
            return 'namespace=\'{0:s}\' block=\'{1:s}\''.format(self.namespace, self.block)
        except AttributeError:
            return super(Vortex, self)._str_more()

    def scheme(self):
        """Default: ``vortex``."""
        return 'x' + self.realkind if self.expected else self.realkind

    def netloc(self):
        """Returns the current ``namespace``."""
        return self.namespace.netloc

    def nice_member(self):
        """Nice formatting view of the member number, if any."""
        return 'mb' + str(self.member) if self.member is not None else ''

    def pathname(self, resource):
        """Constructs pathname of the ``resource`` according to :func:`pathinfo`."""
        rinfo = self.pathinfo(resource)
        rdate = rinfo.get('date', '')
        if rdate:
            rdate = rdate.vortex(rinfo.get('cutoff', 'X'))
        rpath = [
            self.vapp,
            self.vconf,
            self.experiment,
            rdate
        ]
        if self.member is not None:
            rpath.append(self.nice_member())
        rpath.append(self.block)
        return os.path.join(*rpath)

    def basename(self, resource):
        """
        Constructs basename according to current ``namebuild`` factory
        and resource :func:`basname_info`.
        """
        return self.namebuild.pack(resource.basename_info())


class VortexStd(Vortex):
    """Standard Vortex provider (any experiment without an op id)."""

    _footprint = dict(
        info = 'Vortex provider for casual experiments',
        attr = dict(
            experiment = dict(
                outcast = opsuites,
            ),
        )
    )


class VortexOp(Vortex):
    """Standard Vortex provider (any experiment without an op id)."""

    _footprint = dict(
        info = 'Vortex provider for op experiments',
        attr = dict(
            experiment = dict(
                alias  = ('suite',),
                values = opsuites,
            ),
        )
    )

    def netloc(self):
        """Vortex Special OP scheme, aka VSOP !"""
        return 'vsop.' + self.namespace.domain


# Activate the footprint's fasttrack on the resources collector
fcollect = footprints.collectors.get(tag='provider')
fcollect.fasttrack = ('namespace', )
del fcollect
