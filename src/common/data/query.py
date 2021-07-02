#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Resources for query files used for extractions in various databases.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import re

from bronx.fancies import loggers

from vortex.data.outflow import StaticResource
from gco.syntax.stdattrs import gvar
from vortex.data.contents import AlmostListContent, DataTemplate

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class Query(StaticResource):
    """Class to deal with queries."""

    _abstract = True
    _footprint = [
        gvar,
        dict(
            info = 'Abstract class for queries.',
            attr = dict(
                gvar = dict(
                    values  = ['extract_stuff'],
                    default = 'extract_stuff'
                ),
                source = dict(),
                origin = dict(),
            ),
        )
    ]

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source


class BDAPQuery(Query):
    """Class to deal with BDAP queries."""
    _footprint = dict(
        info = 'BDAP query',
        attr = dict(
            kind = dict(
                values = ['bdap_query']
            ),
            origin = dict(
                default = 'bdap',
                values = ['bdap'],
                optional = True
            )
        )
    )

    @property
    def realkind(self):
        return 'bdap_query'


class BDMPQuery(Query):
    """Class to deal with BDMP queries."""
    _footprint = dict(
        info = 'BDMP query',
        attr = dict(
            kind = dict(
                values = ['bdmp_query']
            ),
            origin = dict(
                default = 'bdmp',
                values = ['bdmp'],
                optional = True
            )
        )
    )

    @property
    def realkind(self):
        return 'bdmp_query'


class BDCPQuery(Query):
    """Class to deal with BDCP queries."""
    _footprint = dict(
        info = 'BDCP query',
        attr = dict(
            kind = dict(
                values = ['bdcp_query']
            ),
            origin = dict(
                default = 'bdcp',
                values = ['bdcp'],
                optional = True
            ),
        )
    )

    @property
    def realkind(self):
        return 'bdcp_query'


class BDMQueryContent(AlmostListContent):
    """Read the content of BDM query file."""

    _RE_OBSTYPE = re.compile(r"^(\s*)(OBS\s+TYPE\s*):(\s+)(\w+)$")

    def add_cutoff_info(self, cutoffs_dispenser):
        """
        Using a :class:`vortex.tools.listings.CutoffDispenser` object, add the
        cutoff related information in the BDM query.
        """
        if cutoffs_dispenser.max_cutoff is None:
            logger.warning("The cutoffs_dispenser is empty. No cutoff data can be retrieved")
        else:
            xdata = list()
            for line in self:
                xdata.append(line)
                l_match = self._RE_OBSTYPE.match(line)
                if l_match:
                    cutoff_fmt = '{0:s}{1:<' + str(len(l_match.group(2))) + 's}:{2:s}{3.ymdhms:s}\n'
                    cutoff_date = cutoffs_dispenser(l_match.group(4))
                    xdata.append(cutoff_fmt.format(l_match.group(1),
                                                   'CUTOFF',
                                                   l_match.group(3),
                                                   cutoff_date))
                    logger.info('CUTOFF=%s added for obstype < %s >.',
                                cutoff_date.ymdhms, l_match.group(4))
            self._data = xdata


class BDMQuery(Query):
    """Class to deal with BDM queries."""
    _footprint = dict(
        info = 'BDM query',
        attr = dict(
            kind = dict(
                values = ['bdm_query']
            ),
            origin = dict(
                default = 'bdm',
                values = ['bdm'],
                optional = True
            ),
            clscontents=dict(
                default = BDMQueryContent,
            ),
        )
    )

    @property
    def realkind(self):
        return 'bdm_query'


class MarsQuery(Query):
    """Class to deal with Mars queries"""

    _footprint = dict(
        info = 'Mars query',
        attr = dict(
            kind = dict(
                values = ['mars_query']
            ),
            origin = dict(
                default = "mars",
                values = ["mars", ],
                optional = True
            ),
            clscontents=dict(
                default = DataTemplate
            ),
        )
    )

    @property
    def realkind(self):
        return "mars_query"
