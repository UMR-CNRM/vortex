#!/usr/bin/env python
# -*- coding: utf-8 -*-


import footprints


from vortex.data.flow     import FlowResource
from vortex.tools.date    import Month
from common.data.consts import GenvModelResource

#: Automatic export of Observations class
__all__ = [ ]

logger = footprints.loggers.getLogger(__name__)


class Monitoring(FlowResource):
    """Abstract monitoring resource."""

    _abstract  = True
    _footprint = dict(
        info = 'Observations monitoring file',
        attr = dict(
            kind = dict(
                values = ['monitoring', ],
            ),
            nativefmt = dict(
                values =['ascii', 'binary', 'txt', 'bin'],
                remap = dict(ascii='txt', binary='bin')
            ),
            stage = dict(
                values = ['can', 'surf', 'surface', 'atm', 'atmospheric'],
                remap = dict(can='surf', surface='surf', atmospheric='atm'),
                info = 'The processing stage of the ODB base.',
            ),
            obs = dict(
                values = ['all', 'used'],
                info = 'The processing part of the ODB base.',
            ),
        )
    )

    @property
    def realkind(self):
        return 'monitoring'

    def basename_info(self):
        """Generic information for names fabric, with style = ``obs``."""
        return dict(
            radical = self.realkind,
            fmt = self.nativefmt,
            src     = [self.stage, self.obs],
        )


class MntObsThreshold(GenvModelResource):
    """Observations threshold file.

    A GenvKey can be given.
    """

    _footprint = dict(
        info='Observations threshold',
        attr=dict(
            kind=dict(
                values=['obs_threshold']
            ),
            gvar=dict(
                default='monitoring_seuils_obs'
            ),
            source=dict(
            ),
        )
    )

    @property
    def realkind(self):
        return 'obs_threshold'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source


class MntCumulStat(Monitoring):
    """Accumulated statistics file."""

    _footprint = dict(
        info='Monthly accumulated statistics',
        attr=dict(
            kind=dict(
                values=['accumulated_stats']
            ),
            nativefmt=dict(
                values=['binary', 'bin'],
                default='bin',
                optional = True
            ),
            periodicity = dict(
                values = ['monthly',
                          'weekly_on_mondays'
                          'weekly_on_sundays'],
                default = 'monthly',
                optional =True
            )
        )
    )

    @property
    def realkind(self):
        return 'accumulated_stats'

    def basename_info(self):
        d = super(MntCumulStat, self).basename()
        d['period'] = self.periodicity
        return d


class MntDailyStat(Monitoring):
    """Daily statistics file."""

    _footprint = dict(
        info='Daily statistics',
        attr=dict(
            kind=dict(
                values=['daily_stats']
            ),
            nativefmt=dict(
                values=['ascii', 'txt'],
                default='txt',
                optional=True
            ),
            monitor=dict(
                values=['bias', 'analysis'],
                remap=dict(cy='analysis', deb='bias'),
            )
        )
    )

    @property
    def realkind(self):
        return 'daily_stats'

    def basename_info(self):
        d = super(MntCumulStat, self).basename()
        d['src'].append(self.monitor)
        return d


class MntGrossErrors(Monitoring):
    """Gross errors file."""

    _footprint = dict(
        info='Gross errors',
        attr=dict(
            kind=dict(
                values=['gross_errors']
            ),
            nativefmt = dict(
                values=['ascii', 'txt'],
                default='txt',
                optional=True
            ),
        )
    )

    @property
    def realkind(self):
        return 'gross_errors'


class MntNbMessages(Monitoring):
    """Number of messages for each observations type"""

    _footprint = dict(
        info='Obs messages',
        attr=dict(
            kind=dict(
                values=['nbmessages']
            ),
            nativefmt = dict(
                values=['ascii', 'txt'],
                default='txt',
                optional=True
            ),
        )
    )

    @property
    def realkind(self):
        return 'nbmessages'


class MntMissingObs(Monitoring):
    """Missing observations."""

    _footprint = dict(
        info='Missing observations',
        attr=dict(
            kind=dict(
                values=['missing_obs']
            ),
            nativefmt = dict(
                values=['ascii', 'txt'],
                default='txt',
                optional=True
            ),
        )
    )

    @property
    def realkind(self):
        return 'missing_obs'


class MntObsLocation(Monitoring):
    """Observations location."""

    _footprint = dict(
        info='Observations location',
        attr=dict(
            kind=dict(
                values=['obslocation']
            ),
            nativefmt = dict(
                values=['obslocationpack'],
                default='obslocationpack',
                optional=True
            ),
        )
    )

    @property
    def realkind(self):
        return 'obslocation'