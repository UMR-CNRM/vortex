#!/usr/bin/env python
# -*- coding: utf-8 -*-
from vortex.util.structs import ReadOnlyDict

#: Automatic export of Observations class
__all__ = [ 'Observations' ]

import re
from collections import namedtuple

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.flow     import SpectralGeoFlowResource, FlowResource
from vortex.data.contents import TextContent, AlmostListContent
from vortex.syntax        import stdattrs
from vortex.tools.date    import Date

from gco.syntax.stdattrs  import GenvKey


class Observations(SpectralGeoFlowResource):
    """
    Abstract observation resource.
    """

    _abstract  = True
    _footprint = dict(
        info = 'Observations file',
        attr = dict(
            kind = dict(
                values   = ['observations', 'obs'],
                remap    = dict(obs = 'observations'),
            ),
            part = dict(),
            nativefmt = dict(
                alias    = ('format',),
            ),
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
    """
    TODO.
    """

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
                values   = [
                    'ccma', 'ecma', 'ecmascr',
                    'CCMA', 'ECMA', 'ECMASCR',
                    'rstbias', 'countryrstrhbias', 'sondetyperstrhbias',
                    'RSTBIAS', 'COUNTRYRSTRHBIAS', 'SONDETYPERSTRHBIAS',
                ],
                remap    = dict(
                    CCMA = 'ccma', ECMA = 'ecma', ECMASCR = 'ecmascr',
                    RSTBIAS = 'rstbias',
                    COUNTRYRSTRHBIAS = 'countryrstrhbias',
                    SONDETYPERSTRHBIAS = 'sondetyperstrhbias',
                )
            ),
            stage = dict(
                values   = [
                    'void', 'avg', 'average', 'screen', 'screening', 'split', 'build',
                    'traj', 'min', 'minim', 'complete', 'matchup',
                    'canari', 'cans'
                ],
                remap    = dict(
                    avg    = 'average',
                    min    = 'minim',
                    cans   = 'canari',
                    split  = 'build',
                    screen = 'screening',
                ),
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
        elif self.part == 'full' and self.stage == 'screening':
            return 'odb_screen.tar'
        elif re.match(r'^(?:altitude|mix|full)$', self.part) and self.stage == 'traj':
            return 'odb_traj.tar'
        elif re.match(r'^(?:altitude|mix|full)$', self.part) and self.stage == 'minim' and self.model == 'aladin':
            return 'odb_cpl.tar'
        elif re.match(r'^(?:altitude|mix|full)$', self.part) and self.stage == 'complete':
            return 'odb_cpl.tar'
        elif self.part == 'ground' and self.stage == 'canari':
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
    """
    TODO.
    """

    _footprint = dict(
        info = 'Raw observations set',
        attr = dict(
            nativefmt = dict(
                values  = ['obsoul', 'grib', 'bufr', 'ascii', 'netcdf'],
                remap   = dict(
                    OBSOUL = 'obsoul',
                    GRIB   = 'grib',
                    BUFR   = 'bufr',
                    ASCII  = 'ascii',
                    NETCDF = 'netcdf',
                )
            ),
            stage = dict(
                values  = ['void', 'extract', 'raw', 'std']
            ),
            olivefmt = dict(
                type     = footprints.FPDict,
                optional = True,
                default = footprints.FPDict(
                    ascii  = 'ascii',
                    obsoul = 'obsoul',
                    grib   = 'obsgrib',
                    bufr   = 'obsbufr',
                    netcdf = 'netcdf',
                ),
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
        if re.match(r'^(?:bufr|obsoul|grib|netcdf)$', self.nativefmt) and self.part != 'full' and self.stage == 'void':
            return '.'.join((self.nativefmt, self.part))
        elif re.match(r'^obsoul$', self.nativefmt) and self.part == 'full' and self.stage == 'void':
            return 'obsoul'
        else:
            logger.error(
                'No archive basename defined for such observations (format=%s, part=%s, stage=%s)',
                self.nativefmt, self.part, self.stage
            )


class VarBCContent(AlmostListContent):

    def slurp(self, container):
        """Get data from the ``container`` and find the metadata."""
        super(VarBCContent, self).slurp(container)
        mdata = {}
        # First we look for the version of the VarBC file
        mobj = re.match('\w+\.version(\d+)', self.data[0])
        if mobj:
            mdata['version'] = int(mobj.group(1))
            # Then we fetch the date of the file
            mobj = re.match('\s*\w+\s+(\d{8})\s+(\d+)', self.data[1])
            if mobj:
                mdata['date'] = Date('{:s}{:06d}'.format(mobj.group(1),
                                                         int(mobj.group(2))))
                # The metadata are updated only if both version and data are here
                self._metadata = ReadOnlyDict(mdata)


class VarBC(FlowResource):
    """
    VarBC file ressource. Contains all the coefficients for the VarBC bias correction scheme.
    """

    _footprint = dict(
        info = 'Varbc file',
        attr = dict(
            kind = dict(
                values   = ['varbc']
            ),
            clscontents = dict(
                default  = VarBCContent,
            ),
            nativefmt = dict(
                values   = ['ascii', 'txt'],
                default  = 'txt',
                remap    = dict(ascii = 'txt'),
            ),
            stage = dict(
                optional = True,
                values   = ['void', 'merge', 'screen', 'screening', 'minim', 'traj'],
                remap    = dict(screen = 'screening'),
                default  = 'void'
            ),
            mixmodel = dict(
                optional = True,
                default  = None,
                values   = stdattrs.models,
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
        olivestage_map = {'screening': 'screen',}
        return self.realkind.upper() + "." + olivestage_map.get(self.stage, self.stage)

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.stage == 'void':
            bname = 'VARBC.cycle'
            if self.mixmodel is not None:
                bname += '_'
                if self.mixmodel.startswith('alad'):
                    bname = bname + self.mixmodel[:4]
                else:
                    bname = bname + self.mixmodel[:3]
        else:
            bname = 'VARBC.' + self.stage
        return bname


class BlackList(FlowResource):
    """
    TODO.
    """

    _footprint = dict(
        info = 'Blacklist file for observations',
        attr = dict(
            kind = dict(
                values  = ['blacklist'],
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
                default  = 'blacklist_[scope]',
                values   = ['BLACKLIST_LOC', 'BLACKLIST_DIAP', 'BLACKLIST_LOCAL', 'BLACKLIST_GLOBAL'],
                remap    = dict(
                    BLACKLIST_LOCAL  = 'BLACKLIST_LOC',
                    BLACKLIST_GLOBAL = 'BLACKLIST_DIAP',
                    blacklist_local  = 'BLACKLIST_LOC',
                    blacklist_global = 'BLACKLIST_DIAP',
                )
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


#: A namedtuple of the internal fields of an ObsRef file
ObsRefItem = namedtuple('ObsRefItem', ('data', 'fmt', 'instr', 'date', 'time'))


class ObsRefContent(TextContent):
    """Content class for refdata resources."""

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
    """
    TODO.
    """

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
        return self.realkind + '.' + self.part

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return self.realkind


#: A namedtuple of the internal fields of an ObsMap file
ObsMapItem = namedtuple('ObsMapItem', ('odb', 'data', 'fmt', 'instr'))

class ObsMapContent(TextContent):
    """Content class for obsmap resources."""

    @property
    def discarded(self):
        return self._discarded

    def append(self, item):
        """Append the specified ``item`` to internal data contents."""
        self._data.append(ObsMapItem(*item))

    def slurp(self, container):
        """Get data from the ``container``."""
        container.rewind()
        self.extend([
            obs for obs in
                [ ObsMapItem(*x.split()) for x in [ line.strip() for line in container ] if x and not x.startswith('#') ]
            if obs.odb not in self.discarded
        ])

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
    """
    Simple ascii table for the description of the mapping of
    observations set to ODB bases. The native format is :
    odb / data / fmt / instr.
    """

    _footprint = dict(
        info = 'Bator mapping file',
        attr = dict(
            kind = dict(
                values   = ['obsmap'],
            ),
            gvar = dict(
                type     = GenvKey,
                optional = True,
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
            scope = dict(
                optional = True,
                default  = 'full',
                values   = ['surface', 'surf', 'full'],
                remap = dict(surf = 'surface'),
            ),
            discard = dict(
                type     = footprints.FPSet,
                optional = True,
                default  = footprints.FPSet(),
            )
        )
    )

    @property
    def realkind(self):
        return 'obsmap'

    def contents_args(self):
        """Returns default arguments value to class content constructor."""
        return dict(discarded=set(self.discard))

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'OBSMAP_' + self.stage

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.scope.startswith('surf'):
            return 'BATOR_MAP_' + self.scope[:4].lower()
        else:
            return 'BATOR_MAP'

    def genv_basename(self):
        """Genv key naming convention."""
        cutoff_map = {'production': 'prod'}
        if self.gvar is None:
            if self.scope == 'surface':
                gkey = 'bator_map_surf'
            else:
                gkey = 'bator_map_' + cutoff_map.get(self.cutoff, self.cutoff)
            return GenvKey(gkey)
        else:
            return self.gvar

    def basename_info(self):
        """Generic information for names fabric, with radical = ``obsmap``."""
        return dict(
            style   = 'obsmap',
            radical = self.kind,
            fmt     = self.nativefmt,
            stage   = [self.scope, self.stage]
        )


class Bcor(FlowResource):
    """Bias correction parameters."""

    _footprint = dict(
        info = 'Bias correction parameters',
        attr = dict(
            kind = dict(
                values  = ['bcor'],
            ),
            nativefmt = dict(
                values  = ['ascii', 'txt'],
                default = 'txt',
                remap   = dict(ascii = 'txt')
            ),
            satbias = dict(
                values  = ['mtop', 'metop', 'noaa', 'ssmi'],
                remap   = dict(metop = 'mtop'),
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

