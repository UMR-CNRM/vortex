#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections

import footprints

from vortex.algo.components import AlgoComponent
from bronx.system.hash import HashAdapter

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


_GribInfosKey = collections.namedtuple('_GribInfosKey', ('vapp', 'vconf', 'member', 'domain'))


class GribInfos(AlgoComponent):
    """Loop on available grib files to compute their size and MD5 sum.

    The result is written in a JSON file.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['gribinfos'],
            ),
            engine = dict(
                default = 'algo',
                optional = True,
            ),
            jsonoutput = dict(
                optional = True,
                default = 'grib_infos.json'
            )
        )
    )

    @property
    def realkind(self):
        return 'gribinfos'

    @staticmethod
    def _gribkey(rh):
        return _GribInfosKey(rh.provider.vapp, rh.provider.vconf,
                             rh.provider.member, rh.resource.geometry.area)

    def execute(self, rh, opts):
        """Loop on the various Grib files."""

        gpsec = self.context.sequence.effective_inputs(role=('Gridpoint', ))
        gpsec.sort(lambda a, b: cmp(a.rh.resource.term, b.rh.resource.term))

        gribstack = collections.defaultdict(dict)
        hash_a = HashAdapter('md5')

        for sec in gpsec:
            rh = sec.rh
            gribstack[self._gribkey(rh)][rh.resource.term.fmthm] = dict(
                filesize=rh.container.totalsize,
                md5sum=hash_a.file2hash(rh.container.iotarget())
            )

        dumpable = list()
        for gribk, v in gribstack.items():
            entry = vars(gribk)
            entry['terms'] = v
            dumpable.append(entry)

        self.system.json_dump(dumpable, self.jsonoutput, indent=2)
