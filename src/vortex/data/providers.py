#!/bin/env python
# -*- coding: utf-8 -*-


#: No automatic export
__all__ = [ 'Provider' ]


import re, sys, os.path
import vortex  # @UnusedImport
from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface
from vortex.utilities.names import VNameBuilder
from vortex.tools import net


class Provider(BFootprint):

    _footprint = dict(
        info = 'Abstract root provider',
        attr = dict(
            vapp = dict(
                alias = ( 'application', ),
                optional = True,
                default = '[glove::vapp]'
            ),
            vconf = dict(
                alias = ( 'configuration', ),
                optional = True,
                default = '[glove::vconf]'
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract provider init %s', self.__class__)
        super(Provider, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
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
        return resource.pathinfo(self.realkind())

    def basename(self, resource):
        """Delegates to resource eponym method."""
        return resource.basename(self.realkind())

    def urlquery(self, resource):
        """Delegates to resource eponym method."""
        return resource.urlquery(self.realkind())

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
        return net.uriunparse((
            self.scheme(),
            self.domain(),
            os.path.normpath(self.pathname(resource) + '/' + self.basename(resource)),
            None,
            self.urlquery(resource),
            None
        ))


class Remote(Provider):

    _footprint = dict(
        info = 'Remote provider',
        attr = dict(
	        remote = dict(
		        alias = ( 'remfile', 'rempath' ),
                type = str
	        ),
            hostname = dict(
                optional = True,
                default = 'localhost'
            ),
            tube = dict(
                optional = True,
                values = [ 'scp', 'ftp', 'rcp', 'file' ],
                default = 'file'
            ),
            username = dict(
                optional = True,
                default = None,
                alias = ( 'user', 'logname' )
            )
	    )
    )

    def __init__(self, *args, **kw):
        logger.debug('Remote provider init %s', self)
        super(Remote, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'remote'

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
                type = int,
                optional = True,
            ),
            namespace = dict(
                optional = True,
                values = [ 'open.vortex.fr', 'vortex.cache.fr', 'vortex.archive.fr', 'multi.vortex.fr', 'open.cache.fr', 'open.archive.fr' ],
                default = 'open.cache.fr',
                remap = {
                    'vortex.cache.fr' : 'open.cache.fr',
                    'vortex.archive.fr' : 'open.archive.fr',
                    'multi.vortex.fr' : 'open.vortex.fr'
                }
            ),
            namebuild = dict(
                optional = True,
                type = VNameBuilder,
                default = VNameBuilder(),
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex experiment provider init %s', self)
        super(Vortex, self).__init__(*args, **kw)

    @classmethod
    def realkind(cls):
        return 'vortex'

    def scheme(self):
        """Default: ``vortex``."""
        return 'vortex'

    def domain(self):
        """Returns the current ``namespace``."""
        return self.namespace

    def pathname(self, resource):
        """Constructs pathname of the ``resource`` according to :func:`pathinfo`."""
        rinfo = self.pathinfo(resource)
        rdate = rinfo.get('date', '')
        if rdate:
            rdate = rdate.get_fmt_date('yyyymmddhhmn')
            rdate = re.sub(r'(\d{4})$', r'H\1', rdate)
            rdate = rdate + rinfo.get('cutoff', 'n')[0].upper()
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


class ProvidersCatalog(ClassesCollector):

    def __init__(self, **kw):
        logger.debug('Providers catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.providers'),
            classes = [ Provider ],
            itementry = Provider.realkind()
        )
        cat.update(kw)
        super(ProvidersCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'providers'


cataloginterface(sys.modules.get(__name__), ProvidersCatalog)
