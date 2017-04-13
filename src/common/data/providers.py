#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import

import footprints

from vortex.data.providers import Provider
from vortex.util.config import GenericConfigParser
from vortex.syntax.stdattrs import Namespace, DelayedEnvValue, FmtInt, a_suite
from vortex.tools.date import Time
import os
from footprints.stdtypes import FPList

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class BdpeError(Exception):
    """Base for Bdpe errors."""
    pass


class BdpeConfigurationError(BdpeError):
    """Missing BDPE product description."""
    pass


class BdpeMismatchError(BdpeError):
    """BDPE product description does not match ressource description."""
    pass


class BdpeProvider(Provider):
    """
    Provider to resources stored in the BDPE database.

    The BDPE only knows about product ids, base datetime, and terms.
    A dedicated ini file describes the relation between such ids and
    Vortex resources. This link could be used to deduce the BDPE id
    from the resource (a la footprints). For now, we only check that
    the resource is compatible with the BDPE product description.

    Canvas of a complete url:
        bdpe://bdpe.archive.fr/EXPE/date/BDPE_num+term
    """

    _footprint = dict(
        info = 'BDPE provider',
        attr = dict(
            namespace = dict(
                type     = Namespace,
                optional = True,
                default  = Namespace('bdpe.archive.fr'),
                values   = ['bdpe.archive.fr'],
            ),
            bdpeid = dict(
                type    = str,
            ),
            prefered_target = dict(
                optional = True,
                default  = DelayedEnvValue('BDPE_CIBLE_PREFEREE', 'OPER'),
                values   = ['OPER', 'INT', 'SEC', 'DEV'],
            ),
            forbidden_target = dict(
                optional = True,
                default  = DelayedEnvValue('BDPE_CIBLE_INTERDITE', 'DEV'),
                values   = ['OPER', 'INT', 'SEC', 'DEV'],
            ),
            config = dict(
                optional = True,
                type     = GenericConfigParser,
                default  = GenericConfigParser('@bdpe-map-resources.ini')
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('BDPE provider init %s', self.__class__)
        super(BdpeProvider, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'bdpe'

    def scheme(self):
        """A dedicated scheme."""
        return 'bdpe'

    def netloc(self):
        """The actual netloc is the ``namespace`` attribute of the current provider."""
        return self.namespace.netloc

    def basename(self, resource):
        """Something like 'BDPE_num+term'."""
        myterm = getattr(resource, 'term', Time(0))
        return 'BDPE_{}+{!s}'.format(self.bdpeid, myterm)

    def pathname(self, resource):
        """Something like 'PREFEREDnoFORBIDDEN/date/'."""
        return '{}no{}/{}'.format(self.prefered_target, self.forbidden_target,
                                  resource.date.vortex())

    def uri(self, resource):
        """Overridden to check the resource attributes against
           the BDPE product description from the .ini file.
        """
        # check that the product is described in the configuration file
        if not self.config.has_section(self.bdpeid):
            fmt = 'Missing product n°{} in BDPE configuration file\n"{}"'
            raise BdpeConfigurationError(fmt.format(self.bdpeid, self.config.file))

        # resource description: rely on the footprint_export (it is also used to
        # JSONise resource).
        rsrcdict = {k: str(v)
                    for k, v in resource.footprint_export().iteritems()}

        # check the BDPE pairs against the resource's
        for (k, v) in self.config.items(self.bdpeid):
            if k not in rsrcdict:
                raise BdpeMismatchError('Missing key "{}" in resource'.format(k))
            if rsrcdict[k] != v:
                fmt = 'Bad value for key "{}": rsrc="{}" bdpe="{}"'
                raise BdpeMismatchError(fmt.format(k, rsrcdict[k], v))

        return super(BdpeProvider, self).uri(resource)


class BdapProvider(Provider):
    """
    Provider to resources stored in the BDAP database.

    Canvas of a complete url:
        bdap://bdap.archive.fr/vapp/vconf/oper/date/mb[member]/GRID_[geometry]+[term]
    """

    _footprint = dict(
        info = 'BDAP provider',
        attr = dict(
            namespace = dict(
                type     = Namespace,
                optional = True,
                default  = Namespace('bdap.cache.fr'),
                values   = ['bdap.multi.fr', 'bdap.cache.fr', 'bdap.archive.fr'],
            ),
            member = dict(
                type    = FmtInt,
                args    = dict(fmt = '03'),
                optional = True,
            ),
            suite = a_suite,
            quantity = dict(
                type    = FPList,
            ),
            level_kind = dict(
                type    = str,
                optional = True,
                default  = 'isobare',
            ),
            level = dict(
                type    = FPList,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('BDAP provider init %s', self.__class__)
        super(BdapProvider, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'bdap'

    def scheme(self):
        """Default: ``bdap``."""
        return self.realkind

    def netloc(self):
        """Returns the current ``namespace``."""
        return self.namespace.netloc

    def nice_member(self):
        """Nice formatting view of the member number, if any."""
        return 'mb' + str(self.member) if self.member is not None else ''

    def pathname(self, resource):
        rinfo = self.pathinfo(resource)
        rdate = rinfo.get('date', '')
        if rdate:
            rdate = rdate.vortex(rinfo.get('cutoff', 'X'))
        rpath = [
            self.vapp,
            self.vconf,
            self.suite,
            rdate
        ]
        if self.member is not None:
            rpath.append(self.nice_member())
        return os.path.join(*rpath)

    def basename(self, resource):
        return 'GRID_' + resource.geometry.area + '+' + resource.term.fmth
