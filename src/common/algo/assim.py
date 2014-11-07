#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools import date, odb
from vortex.algo.components import BlindRun, Parallel
from .ifsroot import IFSParallel


class MargeVarBC(Parallel):
    """Nothing really specific."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['mergevarbc'],
            ),
            varbcout = dict(
                optional = True,
                default  = 'VARBC.cycle_out',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Find any ODB candidate in input files."""

        sh = self.system

        sh.touch(self.varbcout)

        # Let ancesters doing real stuff
        super(MargeVarBC, self).prepare(rh, opts)


class IFSODB(IFSParallel, odb.OdbComponent):
    """Mix IFS behavior and some ODB facilities."""

    _abstract  = True
    _footprint = dict(
        attr = dict(
            npool = dict(
                type     = int,
                optional = True,
                default  = 1,
            ),
            iomethod = dict(
                type     = int,
                optional = True,
                default  = 1,
            ),
            slots = dict(
                type     = odb.TimeSlots,
                optional = True,
                default  = odb.TimeSlots(7, chunk='PT1H'),
            ),
            virtualdb = dict(
                optional = True,
                default  = 'ecma',
                access   = 'rwx',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Mostly used for setting environment."""
        super(IFSODB, self).prepare(rh, opts)
        self.odb.setup(
            layout   = self.virtualdb,
            date     = self.date,
            npool    = self.npool,
            nslot    = self.slots.nslot,
            iomethod = self.iomethod,
        )

    def setchannels(self, opts):
        """Look up for namelist channels in effective inputs."""
        namchan = [
            x.rh for x in self.context.sequence.effective_inputs(kind = 'namelist')
                if 'channel' in x.rh.options
        ]
        for thisnam in namchan:
            thisloc = re.sub('\d+$', '', thisnam.options['channel']) + 'channels'
            if thisloc != thisnam.container.localpath():
                self.system.softlink(thisnam.container.localpath(), thisloc)

    def lookupodb(self, fatal=True):
        """Return a list of effective input resources which are odb observations."""
        allodb = [
            x.rh for x in self.context.sequence.effective_inputs(kind = 'observations')
                if x.rh.container.actualfmt == 'odb'
        ]
        allodb.sort(lambda a, b: cmp(a.resource.part, b.resource.part))
        if not allodb and fatal:
            logger.critical('Missing ODB input data for %s', self.fullname())
            raise ValueError('Missing ODB input data')
        return allodb


class Canari(IFSODB):
    """Surface analysis."""

    _footprint = dict(
        info = 'Surface assimilation based on optimal interpolation',
        attr = dict(
            kind = dict(
                values  = ['canari'],
            ),
            conf = dict(
                default = 701,
            ),
            xpname = dict(
                default = 'CANS',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""

        sh = self.system

        # Looking for input observations
        obsodb = [ x for x in self.lookupodb() if x.resource.part.startswith('surf') ]

        if not obsodb:
            logger.critical('No surface obsdata in inputs')
            raise ValueError('No surface obsdata for canari')

        rsurf = obsodb.pop()

        if obsodb:
            logger.error('More than one surface obsdata provided')
            logger.error('Using : %s / %s', rsurf.resource.layout, rsurf.resource.part)
            for robs in obsodb:
                logger.error('Skip : %s / %s', robs.resource.layout, robs.resource.part)

        # Defaults settings
        self.virtualdb = rsurf.resource.layout
        self.date      = rsurf.resource.date
        cma_path       = sh.path.abspath(rsurf.container.localpath())
        sh.cp(sh.path.join(cma_path, 'IOASSIGN'), 'IOASSIGN')
        super(Canari, self).prepare(rh, opts)

        # Some extra settings
        self.env.update(
            ODB_SRCPATH_ECMA         = cma_path,
            ODB_DATAPATH_ECMA        = cma_path,
            ODB_CCMA_CREATE_POOLMASK = 1,
            ODB_CCMA_POOLMASK_FILE   = sh.path.join(cma_path, self.virtualdb.upper() + '.poolmask'),
            ODB_POOLMASKING          = 1,
            ODB_PACKING              = -1,
            BASETIME                 = self.date.ymdh,
            ODB_CCMA_TSLOTS          = self.slots.nslot,
        )

        self.env.default(
            ODB_MERGEODB_DIRECT      = 1,
            ODB_CCMA_LEFT_MARGIN     = self.slots.leftmargin(self.date),
            ODB_CCMA_RIGHT_MARGIN    = self.slots.rightmargin(self.date),
        )


class Screening(IFSODB):
    """Observation screening."""

    _footprint = dict(
        info = 'Observations screening.',
        attr = dict(
            kind = dict(
                values  = ['screening', 'screen', 'thinning'],
                remap   = dict(autoremap = 'first'),
            ),
            ioassign = dict(),
            conf = dict(
                default = 2,
            ),
            xpname = dict(
                default = 'SCRE',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""

        sh = self.system

        # Looking for input observations
        allodb = self.lookupodb()

        # Assume that the first one looks like the others (something to care of later)
        odbtop = allodb[0]
        self.virtualdb = odbtop.resource.layout
        self.date      = odbtop.resource.date

        # Perform the premerging stuff
        self.odb.ioassign_merge(
            layout   = self.virtualdb,
            ioassign = self.ioassign,
            odbnames = [ x.resource.part for x in allodb ],
        )

        # Prepare CCMA output
        thiscwd = sh.getcwd()
        thisdb  = self.virtualdb.upper()
        self.env.update(
            ODB_SRCPATH_CCMA  = sh.path.join(thiscwd, 'CCMA'),
            ODB_DATAPATH_CCMA = sh.path.join(thiscwd, 'CCMA'),
        )
        sh.mkdir('CCMA')
        self.odb.ioassign_create(
            layout   = 'CCMA',
            npool    = self.npool,
            ioassign = self.ioassign
        )
        sh.ll('CCMA.IOASSIGN')
        sh.cp('CCMA.IOASSIGN', sh.path.join('CCMA', 'IOASSIGN'))
        sh.rm('IOASSIGN')
        sh.cat(sh.path.join(thisdb, 'IOASSIGN'), 'CCMA.IOASSIGN', output='IOASSIGN')

        # Defaults settings
        super(Screening, self).prepare(rh, opts)

        # Some extra settings
        self.env.update(
            ODB_CCMA_CREATE_POOLMASK = 1,
            ODB_CCMA_POOLMASK_FILE   = sh.path.join(thiscwd, thisdb, thisdb + '.poolmask'),
            ODB_CCMA_CREATE_DIRECT   = 1,
            BASETIME                 = self.date.ymdh,
            ODB_CCMA_TSLOTS          = self.slots.nslot,
        )

        self.env.default(
            ODB_MERGEODB_DIRECT      = 1,
            ODB_CCMA_LEFT_MARGIN     = self.slots.leftmargin(self.date),
            ODB_CCMA_RIGHT_MARGIN    = self.slots.rightmargin(self.date),
        )

        # Look for extras ODB raw
        odbraw = [
            x.rh for x in self.context.sequence.effective_inputs(kind = 'odbraw')
                if x.rh.container.actualfmt == 'odb'
        ]
        if not odbraw:
            logger.error('No ODB bias table found')
        else:
            rawdbnames = [ x.resource.layout.upper() for x in odbraw ]
            for rawname in rawdbnames:
                self.env[ 'ODB_SRCPATH_' + rawname] = sh.path.join(thiscwd, rawname)
                self.env[ 'ODB_DATAPATH_' + rawname] = sh.path.join(thiscwd, rawname)
                for badlink in [ bl for bl in sh.glob(rawname + '/*.h') if sh.path.islink(bl) and not sh.path.exists(bl) ]:
                    sh.unlink(badlink)
            allio = ['IOASSIGN']
            allio.extend([ sh.path.join(x, 'IOASSIGN') for x in rawdbnames ])
            sh.cat(*allio, output='IOASSIGN.full')
            sh.mv('IOASSIGN.full', 'IOASSIGN')

        # Look for channels namelists and set appropriate links
        self.setchannels(opts)


class Minim(IFSODB):
    """Observation screening."""

    _footprint = dict(
        info = 'Minimisation in the assimilation process.',
        attr = dict(
            kind = dict(
                values  = ['minim', 'min', 'minimisation'],
                remap   = dict(autoremap = 'first'),
            ),
            conf = dict(
                default = 131,
            ),
            xpname = dict(
                default = 'MINI',
            ),
            virtualdb = dict(
                default = 'ccma',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""

        sh = self.system

        # Looking for input observations
        allodb  = self.lookupodb()
        allccma = [ x for x in allodb if x.resource.layout.lower() == 'ccma' ]

        if not allccma:
            logger.critical('Missing CCMA input data for minimisation')
            raise ValueError('Missing CCMA input data')

        # Set env and IOASSIGN
        ccma = allccma.pop()
        ccma_path = sh.path.abspath(ccma.container.localpath())
        sh.cp(sh.path.join(ccma_path, 'IOASSIGN'), 'IOASSIGN')
        self.env.update(
            ODB_SRCPATH_CCMA  = ccma_path,
            ODB_DATAPATH_CCMA = ccma_path,
        )

        # Look for channels namelists and set appropriate links
        self.setchannels(opts)

        # Defaults settings
        self.date = ccma.resource.date
        super(Minim, self).prepare(rh, opts)


class PseudoTrajectory(BlindRun):
    """Some kind of mysterious Lopez Mix..."""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['pseudotraj', 'traj', 'trajectory'],
                remap   = dict(autoremap = 'first'),
            ),
        )
    )
