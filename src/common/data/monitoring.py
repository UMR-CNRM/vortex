#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: Automatic export of Observations class
__all__ = [ 'Monitoring' ]

import re
import itertools
from collections import namedtuple

import footprints

logger = footprints.loggers.getLogger(__name__)

from vortex.data.flow     import GeoFlowResource, FlowResource
from vortex.data.contents import TextContent, AlmostListContent
from vortex.syntax        import stdattrs
from vortex.tools.date    import Date
from vortex.util.structs  import ReadOnlyDict
from common.data.consts import GenvModelResource



from gco.syntax.stdattrs  import gvar, GenvKey


class Monitoring(FlowResource):
    """
    Abstract monitoring resource.
    """

    _abstract  = True
    _footprint = dict(
        info = 'Observations monitoring file',
        attr = dict(
            kind = dict(
                values   = ['monitoring', 'monitor'],
                remap    = dict(obs = 'monitoring'),
            ),
            nativefmt = dict(
                values=['ascii', 'binary'],
                alias    = ('format',),
            ),
            stage = dict(
                values=['can', 'surf', 'surface', 'atm', 'atmospheric'],
                remap= dict(surf='can',surface='can', atmospheric='atm'),
                info     = 'The processing stage of the ODB base.',
            ),
        )
    )

    @property
    def realkind(self):
        return 'monitoring'

    def basename_info(self):
        """Generic information for names fabric, with style = ``obs``."""
        return dict(
            style     = 'monitoring',
            nativefmt = self.nativefmt,
            stage     = self.stage,
        )


class MntObsThreshold(GenvModelResource):
    """
    Observations threshold file
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
                    values=[],
                ),
            )
        )

    @property
    def realkind(self):
        return 'obs_threshold'

    def gget_urlquery(self):
        """
        GGET specific query : ``extract``.
        """
        return 'extract=' + self.source






