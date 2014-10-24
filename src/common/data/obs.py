#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: Automatic export of Observations class
__all__ = [ 'Observations' ]

import re
from collections import namedtuple
from footprints  import FPDict

from vortex.autolog       import logdefault as logger
from vortex.data.flow     import GeoFlowResource, FlowResource
from vortex.data.contents import TextContent


class Observations(GeoFlowResource):

    _abstract  = True
    _footprint = dict(
        info = 'Observations file',
        attr = dict(
            kind = dict(
                values = ['observations', 'obs'],
                remap  = dict(obs = 'observations'),
            ),
            part = dict(),
            nativefmt = dict(
                alias  = ('format',),
            ),
            olivefmt = dict(
                type = FPDict,
                optional = True,
            )
        )
    )

    @property
    def realkind(self):
        return 'observations'

    def basename_info(self):
        """Generic information for names fabric, with style = ``obs``."""
        return dict(
            style     = 'obs',
            nativefmt = self.nativefmt,
            stage     = self.stage,
            part      = self.part,
        )


class ObsODB(Observations):

    _footprint = dict(
        info = 'Packed observations (ODB, CCMA, etc.)',
        attr = dict(
            nativefmt = dict(
                values   = ['odb', 'odb/split', 'odb/compressed'],
                remap    = {
                    'odb/split'      : 'odb',
                    'odb/compressed' : 'odb'
                },
            ),
            layout = dict(
                optional = True,
                default  = 'ecma',
                values   = ['ccma', 'ecma', 'ecmascr'],
            ),
            stage = dict(
                values   = ['void', 'screen', 'split', 'build', 'traj', 'min', 'complete', 'cans'],
                remap    = dict(split = 'build'),
            ),
        )
    )

    def basename_info(self):
        """Generic information for names fabric, with style = ``obs``."""
        d = super(ObsODB, self).basename_info()
        d.update(
            layout = self.layout,
        )
        return d

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return '_'.join((self.layout, self.stage, self.part)) + '.tar'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.part == 'full' and self.stage == 'void':
            return 'ecmascr.tar'
        elif self.part == 'full' and self.stage == 'screen':
            return 'odb_screen.tar'
        elif re.match(r'^(?:altitude|mix|full)$', self.part) and self.stage == 'traj':
            return 'odb_traj.tar'
        elif re.match(r'^(?:altitude|mix|full)$', self.part) and self.stage == 'min' and self.model == 'aladin':
            return 'odb_cpl.tar'
        elif re.match(r'^(?:altitude|mix|full)$', self.part) and self.stage == 'complete':
            return 'odb_cpl.tar'
        elif self.part == 'ground' and self.stage == 'cans':
            return 'odb_canari.tar'
        else:
            logger.error(
                'No archive basename defined for such observations (format=%s, part=%s, stage=%s)',
                self.nativefmt, self.part, self.stage
            )

    def archive_urlquery(self):
        """OP ARCHIVE special query for odb case."""
        if self.nativefmt.startswith('odb'):
            return 'extract=all'
        else:
            return ''


class ObsRaw(Observations):

    _footprint = dict(
        info = 'Raw observations set',
        attr = dict(
            nativefmt = dict(
                values  = ['obsoul', 'grib', 'bufr', 'ascii'],
                remap   = dict(
                    OBSOUL = 'obsoul',
                    GRIB   = 'grib',
                    BUFR   = 'bufr',
                    ASCII  = 'ascii',
                )
            ),
            stage = dict(
                values = ['void', 'extract', 'raw', 'std']
            ),
            olivefmt = dict(
                default = FPDict(
                    ascii  = 'ascii',
                    obsoul = 'obsoul',
                    grib   = 'obsgrib',
                    bufr   = 'obsbufr',
                )
            )
        )
    )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return '_'.join((
            self.olivefmt.get(self.nativefmt, 'obsfoo'),
            self.stage,
            self.part
        ))

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if re.match(r'^(?:bufr|obsoul|grib)$', self.nativefmt) and self.part != 'full' and self.stage == 'void':
            return '.'.join((self.nativefmt, self.part))
        elif re.match(r'^obsoul$', self.nativefmt) and self.part == 'full' and self.stage == 'void':
            return 'obsoul'
        else:
            logger.error(
                'No archive basename defined for such observations (format=%s, part=%s, stage=%s)',
                self.nativefmt, self.part, self.stage
            )


class Varbc(FlowResource):

    _footprint = dict(
        info = 'Varbc file',
        attr = dict(
            kind = dict(
                values   = ['varbc']
            ),
            nativefmt = dict(
                values   = ['ascii', 'txt'],
                default  = 'txt',
                remap    = dict(ascii = 'txt')
           ),
            stage = dict(
                optional = True,
                values   = ['merge', 'void'],
                default  = 'void'
            ),
        )
    )

    @property
    def realkind(self):
        return 'varbc'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``varbc``."""
        return dict(
            radical = self.kind,
            src     = [self.model, self.stage],
            fmt     = self.nativefmt,
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return self.realkind

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.stage == 'void':
            bname = 'VARBC' + '(varbc' + self.model + ':inout)'
        else:
            bname = 'VARBC.' + self.stage
        return bname


class BlackList(FlowResource):

    _footprint = dict(
        info = 'Blacklist file for observations',
        attr = dict(
            kind = dict(
                values  = ['blacklist'],
            ),
            clscontents = dict(
                default  = TextContent,
            ),
            nativefmt = dict(
                values  = ['txt'],
                default = 'txt'
            ),
            scope = dict(
                values  = ['loc', 'local', 'site', 'global', 'diap', 'diapason'],
                remap   = dict(
                    loc      = 'local',
                    site     = 'local',
                    diap     = 'global',
                    diapason = 'global',
                )
            ),
        )
    )

    @property
    def realkind(self):
        return 'blacklist'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``varbc``."""
        return dict(
            radical = self.kind,
            fmt     = self.nativefmt,
            src     = self.scope,
        )

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        return dict(
            model = self.model
        )


    def archive_map(self):
        """OP ARCHIVE specific naming convention."""
        return {
            'local'  : 'LISTE_LOC',
            'global' : 'LISTE_NOIRE_DIAP',
        }

    def archive_basename(self):
        """OP ARCHIVE local basename."""
        mapd = self.archive_map()
        return mapd.get(self.scope, 'LISTE_NOIRE_X')


ObsRefItem = namedtuple('ObsRefItem', ('data', 'fmt', 'instr', 'date', 'time'))

class ObsRefContent(TextContent):

    def append(self, item):
        """Append the specified ``item`` to internal data contents."""
        self._data.append(ObsRefItem(*item))

    def slurp(self, container):
        """Get data from the ``container``."""
        container.rewind()
        self.extend([ ObsRefItem(*x.split()[:5]) for x in container if not x.startswith('#') ])

    @classmethod
    def formatted_data(self, item):
        """Return a formatted string."""
        return '{0:8s} {1:8s} {2:16s} {3:8s} {4:s}'.format(
            item.data, item.fmt, item.instr,
            str(item.date), str(item.time)
        )


class Refdata(FlowResource):

    _footprint = dict(
        info = 'Refdata file',
        attr = dict(
            kind = dict(
                values   = ['refdata']
            ),
            clscontents = dict(
                default  = ObsRefContent,
            ),
            nativefmt = dict(
                values   = ['ascii', 'txt'],
                default  = 'txt',
                remap    = dict(ascii = 'txt')
            ),
            part = dict(
                optional = True,
                default  = 'all'
            ),
        )
    )

    @property
    def realkind(self):
        return 'refdata'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``refdata``."""
        return dict(
            radical = self.kind,
            fmt     = self.nativefmt,
            src     = [self.model, self.part],
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return self.realkind + self.part

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return self.realkind


ObsMapItem = namedtuple('ObsMapItem', ('odb', 'data', 'fmt', 'instr'))

class ObsMapContent(TextContent):

    def append(self, item):
        """Append the specified ``item`` to internal data contents."""
        self._data.append(ObsRefItem(*item))

    def slurp(self, container):
        """Get data from the ``container``."""
        container.rewind()
        self.extend([ ObsMapItem(*x.split()) for x in container if not x.startswith('#') ])

    @classmethod
    def formatted_data(self, item):
        """Return a formatted string."""
        return '{0:12s} {1:12s} {2:12s} {3:s}'.format(item.odb, item.data, item.fmt, item.instr)

    def odbset(self):
        """Return set of odb values."""
        return set([x.odb for x in self])

    def dataset(self):
        """Return set of data values."""
        return set([x.data for x in self])

    def fmtset(self):
        """Return set of format values."""
        return set([x.fmt for x in self])

    def instrset(self):
        """Return set of instrument values."""
        return set([x.instr for x in self])

    def datafmt(self, data):
        """Return format associated to specified ``data``."""
        l = [ x.fmt for x in self if x.data == data ]
        try:
            return l[0]
        except IndexError:
            logger.warning('Data "%s" not found in ObsMap contents', data)

    def getfmt(self, g, x):
        """
        Return format ``part`` of data defined in ``g`` or ``x``.
          * ``g`` stands for a guess dictionary.
          * ``x`` stands for an extra dictionary.

        These naming convention refer to the footprints resolve mechanism.
        """
        part = g.get('part', x.get('part', None))
        if part is None:
            return None
        else:
            return self.datafmt(part)


class ObsMap(FlowResource):

    _footprint = dict(
        info = 'Bator mapping file',
        attr = dict(
            kind = dict(
                values   = ['obsmap'],
            ),
            clscontents = dict(
                default  = ObsMapContent,
            ),
            nativefmt = dict(
                values   = ['ascii', 'txt'],
                default  = 'txt',
                remap    = dict(ascii = 'txt')
            ),
            stage = dict(
                optional = True,
                default  = 'void'
            ),
        )
    )

    @property
    def realkind(self):
        return 'obsmap'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'OBSMAP_' + self.stage

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'BATOR_MAP'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``obsmap``."""
        return dict(
            style   = 'obsmap',
            radical = self.kind,
            fmt     = self.nativefmt,
            stage   = self.stage,
        )


class Bcor(FlowResource):

    _footprint = dict(
        info = 'Bias correction parameters',
        attr = dict(
            kind = dict(
                values = ['bcor'],
            ),
            nativefmt = dict(
                values  = ['txt'],
                default = 'txt',
                remap   = dict(ascii = 'txt')
            ),
            satbias = dict(
                values = ['mtop', 'metop', 'noaa', 'ssmi'],
                remap  = dict(metop = 'mtop'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'bcor'

    def basename_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        return dict(
            radical = self.kind,
            fmt     = self.nativefmt,
            src     = self.satbias,
        )

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'bcor_' + self.satbias + '.dat'
