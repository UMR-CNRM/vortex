#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Abstract and generic classes provider for any "Provider". "Provider" objects,
describe where are stored the data.

Of course, the :class:`Vortex` abstract provider is a must see. It has three
declinations depending on the experiment indentifier type.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import os.path

from bronx.fancies import loggers
import footprints
from footprints import proxy as fpx

from vortex.syntax.stdattrs import xpid, legacy_xpid, free_xpid, opsuites, \
    demosuites, scenario, member, block
from vortex.syntax.stdattrs import namespacefp, Namespace, FmtInt
from vortex.tools import net, names

#: No automatic export
__all__ = ['Provider']

logger = loggers.getLogger(__name__)


class Provider(footprints.FootprintBase):
    """Abstract class for any Provider."""

    _abstract = True
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
            username = dict(
                info     = "The username that will be used whenever necessary.",
                optional = True,
                default  = None,
                alias    = ('user', 'logname')
            ),
        ),
        fastkeys = set(['namespace', ]),
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

    def netuser_name(self, resource):  # @UnusedVariable
        """Abstract method."""
        return self.username

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
        username = self.netuser_name(resource)
        fullnetloc = ('{:s}@{:s}'.format(username, self.netloc(resource)) if username
                      else self.netloc(resource))
        logger.debug(
            'scheme %s netloc %s normpath %s urlquery %s',
            self.scheme(resource),
            fullnetloc,
            os.path.normpath(self.pathname(resource) + '/' + self.basename(resource)),
            self.urlquery(resource)
        )

        return net.uriunparse((
            self.scheme(resource),
            fullnetloc,
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
            ),
            fastkeys = set(['magic', ]),
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
            vapp = dict(
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            vconf = dict(
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
        ),
        fastkeys = set(['remote', ]),
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

    _DEFAULT_NAME_BUILDER = names.VortexNameBuilder()
    _CUSTOM_NAME_BUILDERS = dict()

    _abstract = True
    _footprint = [
        block,
        member,
        scenario,
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
                        'open.cache.fr': 'vortex.cache.fr',
                        'open.archive.fr': 'vortex.archive.fr',
                        'open.multi.fr': 'vortex.multi.fr',
                    }
                ),
                namebuild = dict(
                    info           = "The object responsible for building filenames.",
                    optional       = True,
                    doc_visibility = footprints.doc.visibility.ADVANCED,
                ),
                expected = dict(
                    info        = "Is the resource expected ?",
                    alias       = ('promised',),
                    type        = bool,
                    optional    = True,
                    default     = False,
                    doc_zorder  = -5,
                ),
            ),
            fastkeys = set(['block', 'experiment']),
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('Vortex experiment provider init %s', self.__class__)
        super(Vortex, self).__init__(*args, **kw)
        if self.namebuild is not None:
            if self.namebuild not in self._CUSTOM_NAME_BUILDERS:
                builder = fpx.vortexnamebuilder(name=self.namebuild)
                if builder is None:
                    raise ValueError("The << {:s} >> name builder does not exists."
                                     .format(self.namebuild))
                self._CUSTOM_NAME_BUILDERS[self.namebuild] = builder
            self._namebuilder = self._CUSTOM_NAME_BUILDERS[self.namebuild]
        else:
            self._namebuilder = self._DEFAULT_NAME_BUILDER

    @property
    def namebuilder(self):
        return self._namebuilder

    @property
    def realkind(self):
        return 'vortex'

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

    def pathname(self, resource):
        """Constructs pathname of the ``resource`` according to :func:`namebuilding_info`."""
        rinfo = resource.namebuilding_info()
        rinfo.update(
            vapp=self.vapp,
            vconf=self.vconf,
            experiment=self.experiment,
            block=self.block,
            member=self.member,
            scenario=self.scenario,
        )
        return self.namebuilder.pack_pathname(rinfo)

    def basename(self, resource):
        """
        Constructs basename according to current ``namebuild`` factory
        and resource :func:`~vortex.data.resources.Resource.namebuilding_info`.
        """
        return self.namebuilder.pack_basename(resource.namebuilding_info())


class VortexStd(Vortex):
    """Standard Vortex provider (any experiment with an Olive id)."""

    _footprint = [
        legacy_xpid,
        dict(
            info = 'Vortex provider for casual experiments with an Olive XPID',
            attr = dict(
                experiment = dict(
                    outcast = opsuites | demosuites,
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
