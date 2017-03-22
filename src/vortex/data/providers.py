#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = ['Provider']

import os.path

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.syntax.stdattrs import xpid, legacy_xpid, free_xpid, opsuites, member, block
from vortex.syntax.stdattrs import namespacefp, Namespace, FmtInt
from vortex.util.names import VortexNameBuilder
from vortex.tools import net


class Provider(footprints.FootprintBase):

    _abstract  = True
    _collector = ('provider',)
    _footprint = dict(
        info = 'Abstract root provider',
        attr = dict(
            vapp = dict(
                info        = "The application's identifier.",
                alias       = ('application',),
                optional    = True,
                default     = '[glove::vapp]',
                doc_zorder  = -10
            ),
            vconf = dict(
                info        = "The configuration's identifier.",
                alias       = ('configuration',),
                optional    = True,
                default     = '[glove::vconf]',
                doc_zorder  = -10
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

    def scheme(self, resource):
        """Abstract method."""
        pass

    def netloc(self, resource):
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
            self.scheme(resource),
            self.netloc(resource),
            os.path.normpath(self.pathname(resource) + '/' + self.basename(resource)),
            self.urlquery(resource)
        )

        return net.uriunparse((
            self.scheme(resource),
            self.netloc(resource),
            os.path.normpath(self.pathname(resource) + '/' + self.basename(resource)),
            None,
            self.urlquery(resource),
            None
        ))


class Magic(Provider):

    _footprint = [
        xpid,
        dict(
            info = 'Magic provider that always returns the same URI.',
            attr = dict(
                fake = dict(
                    info     = "Enable this magic provider.",
                    alias    = ('nowhere', 'noprovider'),
                    type     = bool,
                    optional = True,
                    default  = True,
                ),
                magic = dict(
                    info     = "The URI returned by this provider."
                ),
                experiment = dict(
                    optional = True,
                    doc_visibility  = footprints.doc.visibility.ADVANCED,
                ),
                vapp = dict(
                    doc_visibility  = footprints.doc.visibility.GURU,
                ),
                vconf = dict(
                    doc_visibility  = footprints.doc.visibility.GURU,
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'magic'

    def uri(self, resource):
        """URI is supposed to be the magic value !"""
        return self.magic


class Remote(Provider):

    _footprint = dict(
        info = 'Provider that manipulates data given a real path',
        attr = dict(
            remote = dict(
                info        = 'The path to the data.',
                alias       = ('remfile', 'rempath'),
                doc_zorder  = 50
            ),
            hostname = dict(
                info     = 'The hostname that holds the data.',
                optional = True,
                default  = 'localhost'
            ),
            tube = dict(
                info     = "The protocol used to access the data.",
                optional = True,
                values   = ['scp', 'ftp', 'rcp', 'file', 'symlink'],
                default  = 'file',
            ),
            username = dict(
                info     = "The username that will be used to connect to *hostname*.",
                optional = True,
                default  = None,
                alias    = ('user', 'logname')
            ),
            vapp = dict(
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            vconf = dict(
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
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

    def scheme(self, resource):
        """The Remote scheme is its tube."""
        return self.tube

    def netloc(self, resource):
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
    _footprint = [
        block,
        member,
        namespacefp,
        xpid,
        dict(
            info = 'Vortex provider',
            attr = dict(
                member = dict(
                    type    = FmtInt,
                    args    = dict(fmt = '03'),
                ),
                namespace = dict(
                    values   = [
                        'vortex.cache.fr', 'vortex.archive.fr', 'vortex.multi.fr',
                        'open.cache.fr', 'open.archive.fr', 'open.multi.fr',
                    ],
                    default  = Namespace('vortex.cache.fr'),
                    remap    = {
                        'open.cache.fr'   : 'vortex.cache.fr',
                        'open.archive.fr' : 'vortex.archive.fr',
                        'open.multi.fr'   : 'vortex.multi.fr',
                    }
                ),
                namebuild = dict(
                    info           = "The object responsible for building filenames.",
                    optional       = True,
                    type           = VortexNameBuilder,
                    default        = VortexNameBuilder(),
                    doc_visibility = footprints.doc.visibility.GURU,
                ),
                expected = dict(
                    info        = "Is the resource expected ?",
                    alias       = ('promised',),
                    type        = bool,
                    optional    = True,
                    default     = False,
                    doc_zorder  = -5,
                ),
            )
        )
    ]

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

    def scheme(self, resource):
        """Default: ``vortex``."""
        return 'x' + self.realkind if self.expected else self.realkind

    def netloc(self, resource):
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
    """Standard Vortex provider (any experiment with an Olive id)."""

    _footprint = [
        legacy_xpid,
        dict(
            info = 'Vortex provider for casual experiments with an Olive XPID',
            attr = dict(
                experiment = dict(
                    outcast = opsuites,
                ),
            ),
        ),
    ]


class VortexFreeStd(Vortex):
    """Standard Vortex provider (any experiment with an user-defined id)."""

    _footprint = [
        free_xpid,
        dict(
            info = 'Vortex provider for casual experiments with a user-defined XPID',
        ),
    ]

    def netloc(self, resource):
        """Vortex Free scheme (for archiving data)"""
        return 'vortex-free.' + self.namespace.domain


class VortexOp(Vortex):
    """Standard Vortex provider (any experiment without an op id)."""

    _footprint = [
        legacy_xpid,
        dict(
            info = 'Vortex provider for op experiments',
            attr = dict(
                experiment = dict(
                    alias  = ('suite',),
                    values = opsuites,
                ),
            ),
        ),
    ]

    def netloc(self, resource):
        """Vortex Special OP scheme, aka VSOP !"""
        return 'vsop.' + self.namespace.domain


# Activate the footprint's fasttrack on the resources collector
fcollect = footprints.collectors.get(tag='provider')
fcollect.fasttrack = ('namespace', )
del fcollect
