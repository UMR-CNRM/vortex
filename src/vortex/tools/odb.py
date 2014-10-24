#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import io
import tempfile

from vortex.autolog import logdefault as logger
from vortex import tools

from . import addons


def setup_env(env=None, date=None, npool=1, nslots=1, iomethod=1, cma='ECMA'):
    """Setup given environment with default ODB env variables."""

    env.update(
        ODB_CMA                = cma,
        BATOR_NBPOOL           = npool,
        BATODB_NBPOOL          = npool,
        BATOR_NBSLOT           = nslots,
        BATODB_NBSLOT          = nslots,
        ODB_IO_METHOD          = iomethod,
        ODB_DEBUG              = env.ODB_DEBUG              or 0,
        ODB_CTX_DEBUG          = env.ODB_CTX_DEBUG          or 0,
        ODB_REPRODUCIBLE_SEQNO = env.ODB_REPRODUCIBLE_SEQNO or 4,
        ODB_STATIC_LINKING     = env.ODB_STATIC_LINKING     or 1,
        ODB_ANALYSIS_DATE      = date.ymd,
        ODB_ANALYSIS_TIME      = env.ODB_ANALYSIS_TIME      or date.hm + '00',
        TO_ODB_ECMWF           = 0,
        TO_ODB_SWAPOUT         = env.TO_ODB_SWAPOUT         or 0,
    )

    if iomethod == 4:
        env.update(
            ODB_IO_GRPSIZE  = env.ODB_IO_GRPSIZE  or npool,
            ODB_IO_FILESIZE = env.ODB_IO_FILESIZE or 128,
        )


class TimeSlots(object):
    def __init__(self, nslots=7, start='-PT3H', window='PT6H', chunk='PT1H', center=True):
        if isinstance(nslots, str):
            info = [ x.strip() for x in nslots.split('/') ]
            nslots = info[0]
            if len(info) > 1:
                start = info[1]
            if len(info) > 2:
                window = info[2]
            if len(info) > 3:
                chunk = info[3]
        self.nslots = int(nslots)
        self.start  = tools.date.Period(start)
        self.window = tools.date.Period(window)
        self.chunk  = self.window if self.nslots == 1 else tools.date.Period(chunk)
        self.center = center

    def at_date(self, date):
        """Return a list of date bounds for the slots at this ``date``."""
        if self.center:
            self.slots = [ self.chunk.length for x in range(self.nslots) ]
            nb = int(self.window.length / self.chunk.length)
            if nb != self.nslots:
                self.slots[0] = self.slots[-1] = self.chunk.length / 2
        else:
            islot = int(self.window.length / self.nslots)
            self.slots = [ islot for x in range(self.nslots) ]

    def as_list(self, date, filename=None):
        """Return time slots as a list of compact date values."""

        date = tools.date.Date(date)
        self.at_date(date)

        boundlist = [ date + self.start ]
        for x in self.slots:
            boundlist.append(boundlist[-1] + x)
        boundlist = [ x.compact() for x in boundlist ]

        return boundlist

    def as_file(self, date, filename):
        """Fill the specified ``filename`` wih the current list of time slots at this ``date``."""
        nbx = 0
        with io.open(filename, 'w') as fd:
            for x in self.as_list(date):
                fd.write(unicode(x + '\n'))
            nbx = fd.tell()
        return nbx


class ODB_Tool(addons.Addon):
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
        )
    )

    def odb_cp(self, source, destination, intent='in'):
        """Extended copy for ODB repository."""
        logger.info('Using ODB copy')
        rc, source, destination = self.sh.tarfix_out(source, destination)
        rc = rc and self.sh.cp(source, destination, intent=intent)
        rt, source, destination = self.sh.tarfix_in(source, destination)
        if intent == 'inout':
            for infile in self.ffind(destination):
                self.chmod(linkedfile, 0644)
        return rc and rt

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
            rc = ftp.get(source, self.tmpname)
            ftp.close()
            self.sh.untar(self.tmpname)
            self.sh.rm(self.tmpname)
            unpacked = self.sh.glob('*')
            self.sh.mv(unpacked[-1], destination)
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
                output  = False,
                bufsize = 8192,
            )
            rc = ftp.put(p.stdout, destination)
            self.sh.pclose(p)
            ftp.close()
            return rc
        else:
            return False
