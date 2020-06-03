# -*- coding:Utf-8 -*-

"""
Resources to deal with MOCAGE.CFG used to define point source emission.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.outflow import StaticResource
from vortex.data.contents import AlmostListContent
from vortex.syntax.stddeco import namebuilding_append
from bronx.stdtypes.date import Date


class MocageCfgContent(AlmostListContent):
    """Content of MocageCfg.
    """

    @property
    def nbpolls(self):
        """Number of atomic release in MOCAGE.CFG."""
        return int(self._data[0].strip())

    @property
    def first_release_start_at(self):
        """Start of first release written in MOCAGE.CFG."""
        return Date(self._data[1].strip())

    @property
    def first_source_pos(self):
        """Tupple (latitude, longitude) of first source point in MOCAGE.CFG."""

        return (float(self._data[3].rstrip()), float(self._data[4].strip()))

    @property
    def type_simul(self):
        """Type of simulation as written in MOCAGE.CFG."""
        return self._data[10].strip()


@namebuilding_append("src", lambda s: s.status)
class MocageCfg(StaticResource):
    """Point source emission config file for MOCAGE."""

    # fmt: off
    _footprint = [
        dict(
            info = "Point source emission config file for MOCAGE",
            attr = dict(
                kind = dict(
                    values = ["mocage_cfg"]
                ),
                nativefmt = dict(
                    values  = ["ascii"],
                    default = "ascii"
                ),
                status = dict(
                    info   = "Ready for MOCAGE binary or with keywords",
                    values = ['complete', 'with_keywords']
                ),
                clscontents = dict(
                    default = MocageCfgContent
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "mocage_cfg"
