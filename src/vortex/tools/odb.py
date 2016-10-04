#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

import io
import re

import footprints
from vortex import tools
from . import folder

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class OdbDriver(object):
    """A dedicated class for handling some ODB settings."""

    def __init__(self, sh=None, env=None, target=None):
        """A quite challenging initialisation since sh, env and target should be provided."""
        self.sh = sh
        if self.sh is None:
            logger.critical('%s created with a proper shell access [%s]', self.__class__, self)
        self.env = env
        if self.env is None:
            logger.critical('%s created with a proper environment access [%s]', self.__class__, self)
        self.target = target
        if self.target is None:
            logger.critical('%s created with a proper target access [%s]', self.__class__, self)

    def setup(self, date=None, npool=1, nslot=1, iomethod=1, layout='ecma'):
        """Setup given environment with default ODB env variables."""

        self.env.update(
            ODB_CMA                = layout.upper(),
            BATOR_NBPOOL           = npool,
            BATODB_NBPOOL          = npool,
            BATOR_NBSLOT           = nslot,
            BATODB_NBSLOT          = nslot,
            ODB_IO_METHOD          = iomethod,
        )

        self.env.default(
            ODB_DEBUG              = 0,
            ODB_CTX_DEBUG          = 0,
            ODB_REPRODUCIBLE_SEQNO = 4,
            ODB_STATIC_LINKING     = 1,
            ODB_ANALYSIS_DATE      = date.ymd,
            ODB_ANALYSIS_TIME      = date.hm + '00',
            TO_ODB_ECMWF           = 0,
            TO_ODB_SWAPOUT         = 0,
        )

        if iomethod == 4:
            self.env.default(
                ODB_IO_GRPSIZE  = npool,
                ODB_IO_FILESIZE = 128,
            )

        if self.env.NPROC:
            self.env.default(
                NPROCA = self.env.NPROC,
                NPROCB = 1,
            )

        if self.sh.path.exists('IOASSIGN'):
            self.env.default(
                IOASSIGN = self.sh.path.abspath('IOASSIGN'),
            )

    def ioassign_create(self, ioassign='ioassign.x', npool=1, layout='ecma'):
        """Build IO-Assign table."""
        iopath   = self.target.get('odbtools:rootdir', self.env.TMPDIR)
        iovers   = self.target.get('odbtools:odbcycle', 'oper')
        iocreate = self.target.get('odbtools:iocreate', 'create_ioassign')
        iocmd    = self.env.get('ODB_IOCREATE_COMMAND', self.sh.path.join(iopath, iovers, iocreate))
        ioassign = self.sh.path.abspath(ioassign)
        self.sh.xperm(ioassign, force=True)
        self.env.ODB_IOASSIGN_BINARY = ioassign
        self.sh.spawn([iocmd, '-l' + layout.upper(), '-n' + str(npool)], output=False)

    def ioassign_merge(self, ioassign='ioassign.x', layout='ecma', odbnames=None):
        """Build IO-Assign table."""
        layout   = layout.upper()
        iopath   = self.target.get('odbtools:rootdir', self.env.TMPDIR)
        iovers   = self.target.get('odbtools:odbcycle', 'oper')
        iocreate = self.target.get('odbtools:iocreate', 'create_ioassign')
        iomerge  = self.target.get('odbtools:iomerge', 'create_ioassign')
        iocmd    = [self.env.get('ODB_IOMERGE_COMMAND', self.sh.path.join(iopath, iovers, iomerge))]
        self.sh.xperm(ioassign, force=True)
        self.env.default(
            ODB_IOASSIGN_BINARY  = self.sh.path.abspath(ioassign),
            ODB_IOCREATE_COMMAND = self.sh.path.join(iopath, iovers, iocreate),
        )
        oldpwd = self.sh.getcwd()
        self.sh.cd(layout, create=True)
        self.env.ODB_SRCPATH_ECMA = self.env.ODB_DATAPATH_ECMA = self.sh.getcwd()
        iocmd.extend(['-d', oldpwd])
        for dbname in odbnames:
            iocmd.extend(['-t', dbname])
        self.sh.spawn(iocmd, output=False)
        self.sh.cd(oldpwd)


class OdbComponent(object):
    """Extend Algo Components with ODB features."""

    @property
    def odb(self):
        if not hasattr(self, '_odb'):
            self._odb = OdbDriver(
                sh     = self.system,
                env    = self.env,
                target = self.target,
            )
        return self._odb


class TimeSlots(object):
    """Handling of assimilation time slots."""

    def __init__(self, nslot=7, start='-PT3H', window='PT6H', chunk=None, center=True):
        if isinstance(nslot, str):
            info = [x.strip() for x in nslot.split('/')]
            nslot = info[0]
            if len(info) > 1:
                start = info[1]
            if len(info) > 2:
                window = info[2]
            if len(info) > 3:
                if re.match('^regular', info[3]):
                    center = False
                else:
                    chunk = info[3]
        self.nslot  = int(nslot)
        self.center = center if self.nslot > 1 else False
        self.start  = tools.date.Period(start)
        self.window = tools.date.Period(window)
        if chunk is None:
            cslot = self.nslot - 1 if self.center else self.nslot
            chunk = 'PT' + str((self.window.length // max(1, cslot)) // 60) + 'M'
        self.chunk = self.window if self.nslot < 2 else tools.date.Period(chunk)

    def __eq__(self, other):
        if isinstance(other, basestring):
            try:
                other = TimeSlots(other)
            except ValueError:
                pass
        return (isinstance(other, TimeSlots) and
                self.nslot == other.nslot and self.center == other.center and
                self.start == other.start and self.window == other.window and
                self.chunk == other.chunk)

    def __str__(self):
        chunky = self.chunk.isoformat() if self.center else 'regular'
        return '{0.nslot:d}/{1:s}/{2:s}/{3:s}'.format(self,
                                                      self.start.isoformat(),
                                                      self.window.isoformat(),
                                                      chunky)

    def __repr__(self, *args, **kwargs):
        return super(TimeSlots, self).__repr__()[:-1] + ' | {!s}>'.format(self)

    def as_slots(self):
        """Return a list of slots in seconds."""
        if self.center:
            slots = [self.chunk.length, ] * self.nslot
            nb = self.window.length // self.chunk.length
            if nb != self.nslot:
                slots[0] = slots[-1] = self.chunk.length // 2
        else:
            islot = self.window.length // self.nslot
            slots = [islot, ] * self.nslot
        return slots

    def as_bounds(self, date):
        """Return time slots as a list of compact date values."""
        date = tools.date.Date(date)
        boundlist = [date + self.start, ]
        for x in self.as_slots():
            boundlist.append(boundlist[-1] + x)
        boundlist = [x.compact() for x in boundlist]

        return boundlist

    @property
    def leftmargin(self):
        """Return length in minutes from left margin of the window."""
        return int(self.start.total_seconds()) // 60

    @property
    def rightmargin(self):
        """Return length in minutes from rigth margin of the window."""
        return int((self.start + self.window).total_seconds()) // 60

    def as_environment(self):
        """Return a dictionary of ready-to-export variables that describe the timeslots."""
        thelen = self.chunk.length // 60 if self.center and self.nslot > 1 else 0
        return dict(BATOR_WINDOW_LEN=self.window.length // 60,
                    BATOR_WINDOW_SHIFT=int(self.start.total_seconds()) // 60,
                    BATOR_SLOT_LEN=thelen, BATOR_CENTER_LEN=thelen)

    def as_file(self, date, filename):
        """Fill the specified ``filename`` wih the current list of time slots at this ``date``."""
        with io.open(filename, 'w') as fd:
            for x in self.as_bounds(date):
                fd.write(unicode(x + '\n'))
            nbx = fd.tell()
        return nbx


class OdbShell(folder.FolderShell):
    """
    Default interface to ODB commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info = 'Default ODB system interface',
        attr = dict(
            kind = dict(
                values   = ['odb'],
            ),
        )
    )

    def odb_cp(self, source, destination, intent='in'):
        """Extended copy for ODB repository."""
        return super(OdbShell, self)._folder_cp(source, destination, intent)

    def odb_mv(self, source, destination):
        """Extended copy for ODB repository."""
        return super(OdbShell, self)._folder_mv(source, destination)

    def odb_ftget(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp get on the specified target."""
        return super(OdbShell, self)._folder_ftget(source, destination,
                                                   hostname, logname)

    def odb_ftput(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp get on the specified target."""
        return super(OdbShell, self)._folder_ftput(source, destination,
                                                   hostname, logname)

    def odb_rawftput(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp get on the specified target."""
        return super(OdbShell, self)._folder_rawftput(source, destination,
                                                      hostname, logname)

    odb_rawftget = odb_ftget
