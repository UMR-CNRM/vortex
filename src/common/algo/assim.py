#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools import odb
from vortex.tools.date import Date
from vortex.algo.components import BlindRun, Parallel
from .ifsroot import IFSParallel
from vortex.syntax.stdattrs import a_date


class MergeVarBC(Parallel):
    """
    Merge two VarBC files.

    The VarBC file resulting from the MergeVarBC contains all the items of the
    first VarBC file plus any new item that would be present in the second file.
    """

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
        super(MergeVarBC, self).prepare(rh, opts)


class Anamix(IFSParallel):
    """Merge the surface and atmospheric analyses into a single file"""

    _footprint = dict(
        info='Merge surface and atmospheric analyses',
        attr=dict(
            kind=dict(
                values=['anamix'],
            ),
            conf=dict(
                default=701,
            ),
            xpname=dict(
                default='CANS',
            ),
            timestep=dict(
                default=1,
            )
        )
    )


class SstAnalysis(IFSParallel):
    """SST (Sea Surface Temperature) Analysis"""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['sstana', 'sst_ana', 'sst_analysis', 'c931'],
                remap   = dict(autoremap = 'first'),
            ),
            conf = dict(
                default = 931,
            ),
            xpname = dict(
                default = 'ANAL',
            ),
            timestep = dict(
                default  = '1.',
            ),
        )
    )


class SeaIceAnalysis(IFSParallel):
    """Sea Ice Analysis"""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['seaiceana', 'seaice_ana', 'seaice_analysis', 'c932'],
                remap   = dict(autoremap = 'first'),
            ),
            conf = dict(
                default = 932,
            ),
            xpname = dict(
                default = 'ANAL',
            ),
            timestep = dict(
                default  = '1.',
            ),
            date = dict(
                type     = Date,
            )
        )
    )

    def prepare(self, rh, opts):
        """Update the date in the namelist."""

        super(SeaIceAnalysis, self).prepare(rh, opts)

        namrh_list = [x.rh  for x in self.context.sequence.effective_inputs(role='Namelist',
                                                                            kind='namelist',)]

        if not namrh_list:
            logger.critical('No namelist was found.')
            raise ValueError('No namelist was found for seaice analysis')

        for namrh in namrh_list:
            logger.info('Setup IDAT=%s in %s', self.date.ymd, namrh.container.actualpath())
            try:
                namrh.contents.setmacro('IDAT', int(self.date.ymd))
            except:
                logger.critical('Could not fix NAMICE in %s', namrh.container.actualpath())
                raise
            namrh.contents.rewrite(namrh.container)


class IFSODB(IFSParallel, odb.OdbComponent):
    """Mix IFS behavior and some ODB facilities."""

    _abstract  = True
    _footprint = dict(
        attr = dict(
            npool = dict(
                info        = 'The number of pool(s) in the ODB database.',
                type        = int,
                optional    = True,
                default     = 1,
            ),
            iomethod = dict(
                info        = 'The io_method of the ODB database.',
                type        = int,
                optional    = True,
                default     = 1,
                doc_zorder  = -50,
            ),
            slots = dict(
                info     = 'The timeslots of the assimilation window.',
                type     = odb.TimeSlots,
                optional = True,
                default  = odb.TimeSlots(7, chunk='PT1H'),
            ),
            virtualdb = dict(
                info            = 'The type of the virtual ODB database.',
                optional        = True,
                default         = 'ecma',
                access          = 'rwx',
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            ),
            date = dict(
                info            = 'The current run date.',
                optional        = True,
                access          = 'rwx',
                type            = Date,
                doc_zorder      = -50,
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
            thisloc = re.sub(r'\d+$', '', thisnam.options['channel']) + 'channels'
            if thisloc != thisnam.container.localpath():
                self.system.softlink(thisnam.container.localpath(), thisloc)

    def lookupodb(self, fatal=True):
        """Return a list of effective input resources which are odb observations."""
        allodb = [
            x.rh for x in self.context.sequence.effective_inputs(kind = 'observations')
            if x.rh.container.actualfmt == 'odb'
        ]
        allodb.sort(key=lambda rh: rh.resource.part)
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
            ODB_CCMA_LEFT_MARGIN     = self.slots.leftmargin,
            ODB_CCMA_RIGHT_MARGIN    = self.slots.rightmargin,
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
            ODB_CCMA_LEFT_MARGIN     = self.slots.leftmargin,
            ODB_CCMA_RIGHT_MARGIN    = self.slots.rightmargin,
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
                for badlink in [bl for bl in sh.glob(rawname + '/*.h')
                                if sh.path.islink(bl) and not sh.path.exists(bl)]:
                    sh.unlink(badlink)
            allio = ['IOASSIGN']
            allio.extend([ sh.path.join(x, 'IOASSIGN') for x in rawdbnames ])
            sh.cat(*allio, output='IOASSIGN.full')
            sh.mv('IOASSIGN.full', 'IOASSIGN')

        # Look for channels namelists and set appropriate links
        self.setchannels(opts)


class IFSODBCCMA(IFSODB):
    """Specialised IFSODB for CCMA processing"""

    _abstract = True
    _footprint = dict(
        attr=dict(
            virtualdb=dict(
                default='ccma',
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
            logger.critical('Missing CCMA input data for ' + self.kind)
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
        super(IFSODBCCMA, self).prepare(rh, opts)


class Minim(IFSODBCCMA):
    """Observation minimisation."""

    _footprint = dict(
        info='Minimisation in the assimilation process.',
        attr=dict(
            kind=dict(
                values=['minim', 'min', 'minimisation'],
                remap=dict(autoremap='first'),
            ),
            conf=dict(
                default=131,
            ),
            xpname=dict(
                default='MINI',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Find out if preconditioning eigenvectors are here."""

        # Check if a preconditioning EV map is here
        evmaprh = self.context.sequence.effective_inputs(role=('PreconEVMap',
                                                               'PreconditionningEVMap'),
                                                         kind='precevmap')
        if evmaprh:
            if len(evmaprh) > 1:
                logger.warning("Several preconditioning EV maps provided. Using the first one.")
            nprec_ev = evmaprh[0].rh.contents.data['evlen']
            # If there are preconditioning EV: update the namelist
            if nprec_ev > 0:
                for namrh in [x.rh  for x in self.context.sequence.effective_inputs(role='Namelist',
                                                                                    kind='namelist',)]:
                    namc = namrh.contents
                    try:
                        namc['NAMVAR'].NPCVECS = nprec_ev
                        namc.rewrite(namrh.container)
                    except Exception:
                        logger.critical('Could not fix NAMVAR in %s', namrh.container.actualpath())
                        raise
                logger.info("%d preconditioning EV will by used (NPCVECS=%d).", nprec_ev, nprec_ev)
            else:
                logger.warning("A preconditioning EV map was found, " +
                               "but no preconditioning EV are available.")
        else:
            logger.info("No preconditioning EV were found.")

        super(Minim, self).prepare(rh, opts)

    def postfix(self, rh, opts):
        """Find out if any special resources have been produced."""
        sh = self.system

        # Look up for PREConditionning Eigen Vectors
        prec = sh.ls('MEMINI*')
        if prec:
            prec_info = dict(evlen=len(prec))
            prec_info['evnum'] = [ int(x[6:])  for x in prec ]
            sh.json_dump(prec_info, 'precev_map.out', indent=4)

        super(Minim, self).postfix(rh, opts)


class Trajectory(IFSODBCCMA):
    """Observation trajectory."""

    _footprint = dict(
        info='Trajectory in the assimilation process.',
        attr=dict(
            kind=dict(
                values=['traj', 'trajectory'],
                remap=dict(autoremap='first'),
            ),
            conf=dict(
                default=2,
            ),
            xpname=dict(
                default='TRAJ',
            ),
        )
    )


class PseudoTrajectory(BlindRun):
    """Copy a few fields from the Guess file into the Analysis file"""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['pseudotraj', 'traj', 'trajectory'],
                remap   = dict(autoremap = 'first'),
            ),
        )
    )

    def prepare(self, rh, opts):
        """Add some defaults env values for mpitool itself."""
        super(PseudoTrajectory, self).prepare(rh, opts)
        self.export('drhook_not_mpi')


class SstGrb2Ascii(BlindRun):
    """Transform sst grib files from the BDAP into ascii files"""
    _footprint = dict(
        info = 'Binary to change the format of sst BDAP files.',
        attr = dict(
            kind = dict(
                values = ['lect_bdap'],
            ),
            date = a_date,
            nlat = dict(
                default = 0,
            ),
            nlon = dict(
                default = 0,
            )
        )
    )

    def prepare(self, rh, opts):
        """Add namelist delta, prepare the environment and build the arguments needed."""
        super(SstGrb2Ascii, self).prepare(rh, opts)
        for namrh in [x.rh for x in self.context.sequence.effective_inputs(role='Namelist',
                                                                           kind='namelist', )]:
            namc = namrh.contents
            try:
                namc.newblock('NAMFILE')
                namc['NAMFILE'].NBFICH = 1
                namc['NAMFILE']['CCNFICH(1)'] = 'GRIB_SST'
                namc.rewrite(namrh.container)
            except Exception:
                logger.critical('Could not fix NAMFILE in %s', namrh.container.actualpath())
                raise

    def spawn_command_options(self):
        """Build the dictionnary to provide arguments to the binary."""
        return dict(
            year = self.date.year,
            month = self.date.month,
            day = self.date.day,
            hour = self.date.hour,
            lon = self.nlon,
            lat = self.nlat,
        )
