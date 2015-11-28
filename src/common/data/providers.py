#!/usr/bin/env python
# -*- coding: utf-8 -*-

import footprints

from vortex.data.providers import Provider
from vortex.util.config import GenericConfigParser

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
    from the resource (à la footprints). For now, we only check that
    the resource is compatible with the BDPE product description.

    Canvas of a complete url:
        bdpe://bdpe.archive.fr/EXPE/date/BDPE_num+term
    """

    _footprint = dict(
        info = 'BDPE provider',
        attr = dict(
            experiment = dict(),
            namespace = dict(
                optional = True,
                default  = 'bdpe.archive.fr',
                values   = ['bdpe.archive.fr'],
            ),
            bdpeid = dict(
                type    = str,
            ),
            config = dict(
                optional = True,
                type     = GenericConfigParser,
                default  = GenericConfigParser('bdpe-map-resources.ini')
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
        return self.namespace

    def basename(self, resource):
        """Something like 'BDPE_num+term'."""
        return 'BDPE_{}+{}'.format(self.bdpeid, resource.term)

    def pathname(self, resource):
        """Something like 'EXPE/date/'."""
        return '{}/{}'.format(self.experiment, resource.date.vortex())

    def uri(self, resource):
        """Overridden to check the resource attributes against
           the BDPE product description from the .ini file.
        """
        # check that the product is described in the configuration file
        if not self.config.has_section(self.bdpeid):
            fmt = 'Missing product n°{} in BDPE configuration file\n"{}"'
            raise BdpeConfigurationError(fmt.format(self.bdpeid, self.config.file))

        # resource description: replace GetByTag objects by their tag (e.g. for geometry)
        rsrcdict = {k: v.tag if isinstance(v, footprints.util.GetByTag)
                    else str(v)
                    for (k, v) in resource.footprint_as_shallow_dict().iteritems()
                    }

        # check the BDPE pairs against the resource's
        for (k, v) in self.config.items(self.bdpeid):
            if k not in rsrcdict:
                raise BdpeMismatchError('Missing key "{}" in resource'.format(k))
            if rsrcdict[k] != v:
                fmt = 'Bad value for key "{}": rsrc="{}" bdpe="{}"'
                raise BdpeMismatchError(fmt.format(k, rsrcdict[k], v))

        return super(BdpeProvider, self).uri(resource)
