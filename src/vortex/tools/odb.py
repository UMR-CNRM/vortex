#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import io
import tempfile

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import tools

from . import addons


class OdbDriver(object):
    """A dedicated class for handling some ODB settings."""

    def __init__(self, sh=None, env=None, target=None):
        """A quite challenging initialisation since sh, env and target should be provided."""
        self.sh     = sh
        if self.sh is None:
            logger.critical('%s created with a proper shell access [%s]', self.__class__, self)
        self.env    = env
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

    def __init__(self, nslot=7, start='-PT3H', window='PT6H', chunk='PT1H', center=True):
        if isinstance(nslot, str):
            info = [ x.strip() for x in nslot.split('/') ]
            nslot = info[0]
            if len(info) > 1:
                start = info[1]
            if len(info) > 2:
                window = info[2]
            if len(info) > 3:
                chunk = info[3]
        self.nslot  = int(nslot)
        self.start  = tools.date.Period(start)
        self.window = tools.date.Period(window)
        self.chunk  = self.window if self.nslot < 2 else tools.date.Period(chunk)
        self.center = center

    def as_slots(self):
        """Return a list of slots in seconds."""
        if self.center:
            slots = [ self.chunk.length for x in range(self.nslot) ]
            nb = int(self.window.length / self.chunk.length)
            if nb != self.nslot:
                slots[0] = slots[-1] = self.chunk.length / 2
        else:
            islot = int(self.window.length / self.nslot)
            slots = [ islot for x in range(self.nslot) ]
        return slots

    def as_bounds(self, date, filename=None):
        """Return time slots as a list of compact date values."""
        date = tools.date.Date(date)
        boundlist = [ date + self.start ]
        for x in self.as_slots():
            boundlist.append(boundlist[-1] + x)
        boundlist = [ x.compact() for x in boundlist ]

        return boundlist

    def leftmargin(self, date):
        """Return length in minutes from left margin of the window."""
        return int(self.start.total_seconds() / 60)

    def rightmargin(self, date):
        """Return length in minutes from rigth margin of the window."""
        date = tools.date.Date(date)
        end = date + self.start + self.window
        delta = end - date
        return int(delta.total_seconds() / 60)

    def as_file(self, date, filename):
        """Fill the specified ``filename`` wih the current list of time slots at this ``date``."""
        nbx = 0
        with io.open(filename, 'w') as fd:
            for x in self.as_bounds(date):
                fd.write(unicode(x + '\n'))
            nbx = fd.tell()
        return nbx


class OdbShell(addons.Addon):
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
            tmpname = dict(
                optional = True,
                default  = 'ODB.tgz',
            ),
            pipeget = dict(
                type     = bool,
                optional = True,
                default  = True,
            ),
        )
    )

    def odb_cp(self, source, destination, intent='in'):
        """Extended copy for ODB repository."""
        rc, source, destination = self.sh.tarfix_out(source, destination)
        rc = rc and self.sh.cp(source, destination, intent=intent)
        if rc :
            rc, source, destination = self.sh.tarfix_in(source, destination)
            if rc and intent == 'inout':
                self.sh.stderr('chmod', 0644, destination)
                oldtrace, self.sh.trace = self.sh.trace, False
                for infile in self.sh.ffind(destination):
                    self.sh.chmod(infile, 0644)
                self.sh.trace = oldtrace
        return rc

    def odb_credentials(self, hostname=None, logname=None):
        """Some heuristic to get proper values for these arguments."""
        if hostname is None:
            hostname = self.sh.env.VORTEX_ARCHIVE_HOST

        if logname is None:
            logname = self.sh.env.VORTEX_ARCHIVE_USER

        return (hostname, logname)

    def odb_ftget(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp get on the specified target."""
        hostname, logname = self.odb_credentials(hostname, logname)

        if hostname is None:
            return False

        if not source.endswith('.tgz'):
            source = source + '.tgz'

        self.sh.rm(destination)

        destination = self.sh.path.abspath(destination)

        ftp = self.sh.ftp(hostname, logname)
        if ftp:
            loccwd = self.sh.getcwd()
            loctmp = tempfile.mkdtemp(prefix='odb_', dir=loccwd)
            self.sh.cd(loctmp)
            try:
                if self.pipeget:
                    p = self.sh.popen(
                        ['tar', 'xvfz', '-'],
                        stdin   = True,
                        output  = False,
                        bufsize = 8192,
                    )
                    rc = ftp.get(source, p.stdin)
                    self.sh.pclose(p)
                else:
                    rc = ftp.get(source, self.tmpname)
                    self.sh.untar(self.tmpname)
                    self.sh.rm(self.tmpname)
            finally:
                ftp.close()
                try:
                    unpacked = self.sh.glob('*')
                    if unpacked:
                        self.sh.mv(unpacked[-1], destination)
                    else:
                        logger.error('Nothing to unpack')
                except StandardError as trouble:
                    logger.critical('Unable to proceed odb post-ftget step')
                    raise trouble
                finally:
                    self.sh.cd(loccwd)
                    self.sh.rm(loctmp)
            return rc
        else:
            return False

    def odb_ftput(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp put on the specified target."""
        hostname, logname = self.odb_credentials(hostname, logname)

        if hostname is None:
            return False

        if not destination.endswith('.tgz'):
            destination = destination + '.tgz'

        ftp = self.sh.ftp(hostname, logname)
        if ftp:
            p = self.sh.popen(
                ['tar', 'cvfz', '-', source],
                stdout  = True,
                output  = False,
                bufsize = 8192,
            )
            rc = ftp.put(p.stdout, destination)
            self.sh.pclose(p)
            ftp.close()
            return rc
        else:
            return False