#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six

from bronx.fancies import loggers

from vortex.data.providers import Provider
from vortex.util.config import GenericConfigParser
from vortex.syntax.stdattrs import namespacefp, DelayedEnvValue, Namespace
from bronx.stdtypes.date import Time

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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

    When a resource has no ``date`` attribute, the most recent data
    is extracted from the BDPE (might be used for Alert Models).
    """

    _footprint = [
        namespacefp,
        dict(
            info = 'BDPE provider',
            attr = dict(
                namespace = dict(
                    default  = Namespace('bdpe.archive.fr'),
                    values   = ['bdpe.archive.fr'],
                ),
                bdpeid = dict(
                ),
                preferred_target = dict(
                    optional = True,
                    default  = DelayedEnvValue('BDPE_CIBLE_PREFEREE', 'OPER'),
                    values   = ['OPER', 'INT', 'SEC', 'DEV'],
                ),
                forbidden_target = dict(
                    optional = True,
                    default  = DelayedEnvValue('BDPE_CIBLE_INTERDITE', 'DEV'),
                    values   = ['OPER', 'INT', 'SEC', 'DEV'],
                ),
                allow_archive = dict(
                    info     = 'If True, sets the env. var. allowing the use of the archive'
                               ' version of the BDPE service',
                    optional = True,
                    type     = bool,
                    default  = False,
                ),
                config = dict(
                    info     = 'A ready to use configuration file object for this storage place.',
                    type     = GenericConfigParser,
                    optional = True,
                    default  = None,
                ),
                inifile = dict(
                    info     = ('The name of the configuration file that will be used (if ' +
                                '**config** is not provided.'),
                    optional = True,
                    default  = '@bdpe-map-resources.ini',
                ),
            ),
            fastkeys = set(['bdpeid']),
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('BDPE provider init %s', self.__class__)
        super(BdpeProvider, self).__init__(*args, **kw)
        self._actual_config = self.config
        if self._actual_config is None:
            self._actual_config = GenericConfigParser(inifile=self.inifile)

    @property
    def realkind(self):
        return 'bdpe'

    def scheme(self, resource):
        """A dedicated scheme."""
        return 'bdpe'

    def netloc(self, resource):
        """The actual netloc is the ``namespace`` attribute of the current provider."""
        return self.namespace.netloc

    def basename(self, resource):
        """Something like 'BDPE_num+term'."""
        myterm = getattr(resource, 'term', Time(0))
        return 'BDPE_{}+{!s}'.format(self.bdpeid, myterm)

    def pathname(self, resource):
        """Something like 'PREFERRED_FORBIDDEN_ARCHIVE/date/'."""
        try:
            requested_date = resource.date.vortex()
        except AttributeError:
            requested_date = 'most_recent'
        return '{}_{}_{}/{}'.format(self.preferred_target, self.forbidden_target,
                                    self.allow_archive, requested_date)

    def uri(self, resource):
        """
        Overridden to check the resource attributes against
        the BDPE product description from the .ini file.
        """
        # check that the product is described in the configuration file
        if not self._actual_config.has_section(self.bdpeid):
            fmt = 'Missing product n°{} in BDPE configuration file\n"{}"'
            raise BdpeConfigurationError(fmt.format(self.bdpeid, self.config.file))

        # resource description: rely on the footprint_export (it is also used to
        # JSONise resource).
        rsrcdict = {k: six.text_type(v)
                    for k, v in six.iteritems(resource.footprint_export())}

        # check the BDPE pairs against the resource's
        for (k, v) in self._actual_config.items(self.bdpeid):
            if k not in rsrcdict:
                raise BdpeMismatchError('Missing key "{}" in resource'.format(k))
            if rsrcdict[k] != v:
                fmt = 'Bad value for key "{}": rsrc="{}" bdpe="{}"'
                raise BdpeMismatchError(fmt.format(k, rsrcdict[k], v))

        return super(BdpeProvider, self).uri(resource)
