#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
from collections import defaultdict

from bronx.stdtypes.date import Time, Month
import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo.components import AlgoComponentError

from vortex.util.structs import ShellEncoder
from .ifsroot import IFSParallel
from vortex.layout.dataflow import intent


class Forecast(IFSParallel):
    """Forecast for IFS-like Models."""

    _footprint = dict(
        info = "Run a forecast with Arpege/IFS.",
        attr = dict(
            kind = dict(
                values   = ['forecast', 'fc'],
                remap    = dict(forecast = 'fc')
            ),
            flyargs = dict(
                default = ('ICMSH', 'PF'),
            ),
            xpname = dict(
                default  = 'FCST'
            ),
            inline = dict(
                info        = "Do inline post-processing",
                type        = bool,
                optional    = True,
                default     = True,
                doc_zorder  = -5,
            ),
            ddhpack = dict(
                info        = "After run, gather the DDH output file in directories.",
                type        = bool,
                optional    = True,
                default     = False,
                doc_zorder  = -5,
            ),
            outputid = dict(
                info        = "The identifier for the encoding of post-processed fields.",
                type        = str,
                optional    = True,
            )
        )
    )

    @property
    def realkind(self):
        return 'forecast'

    def prepare(self, rh, opts):
        """Default pre-link for the initial condition file"""
        super(Forecast, self).prepare(rh, opts)

        sh = self.system

        analysis = self.setlink(
            initrole = ('InitialCondition', 'Analysis'),
            initname = 'ICMSH{0:s}INIT'.format(self.xpname)
        )

        if analysis:
            analysis  = analysis.pop()
            thismonth = analysis.rh.resource.date.month

            def checkmonth(actualrh):
                return bool(actualrh.resource.month == thismonth)

            self.setlink(
                initrole = ('GlobalClim', 'InitialClim'),
                initkind = 'clim_model',
                initname = 'Const.Clim',
                inittest = checkmonth,
            )

            for bdaprh in [x.rh for x in self.context.sequence.effective_inputs(
                role = ('LocalClim', 'TargetClim', 'BDAPClim'),
                kind = 'clim_bdap',
            ) if x.rh.resource.month == thismonth]:
                thisclim = bdaprh.container.localpath()
                thisname = 'const.clim.' + bdaprh.resource.geometry.area
                if thisclim != thisname:
                    sh.symlink(thisclim, thisname)

            for iaurh in [x for x in
                          self.context.sequence.effective_inputs(role = re.compile(r'IAU_\w'))]:
                self.grab(iaurh, comment='IAU files')

            # At least, expect the analysis to be there...
            self.grab(analysis, comment='analysis')

        for namrh in [x.rh for x in self.context.sequence.effective_inputs(
            role = 'Namelist',
            kind = 'namelist',
        )]:
            try:
                namlocal = namrh.container.actualpath()
                namc = namrh.contents
                namc['NAMCT0'].NFPOS = int(self.inline)
                logger.info("Setup NAMCT0's NFPOS=%d in %s", int(self.inline), namlocal)
                if self.outputid is not None:
                    namc.setmacro('OUTPUTID', self.outputid)
                    logger.info('Setup macro OUTPUTID=%s in %s', self.outputid, namlocal)
                namc.rewrite(namrh.container)
            except Exception:
                logger.critical('Could not fix %s', namrh.container.actualpath())
                raise

        # Promises should be nicely managed by a co-proccess
        if self.promises:
            prefixes_set = set()
            for pr_res in [pr.rh.resource for pr in self.promises]:
                if pr_res.realkind == 'historic':
                    prefixes_set.add('ICMSH')
                if pr_res.realkind == 'gridpoint':
                    prefixes_set.add('{:s}PF'.format('GRIB' if pr_res.nativefmt == 'grib' else ''))
            self.io_poll_args = tuple(prefixes_set)
            self.flyput = len(self.io_poll_args) > 0

    def postfix(self, rh, opts):
        """Find out if any special resources have been produced."""

        sh = self.system

        # Look up for the gridpoint files
        gp_out = sh.ls('PF{}*'.format(self.xpname))
        gp_map = defaultdict(list)
        if gp_out:
            re_pf = re.compile(r'^PF{}(\w+)\+(\d+(?::\d+)?)$'.format(self.xpname))
            for fname in gp_out:
                match_pf = re_pf.match(fname)
                if match_pf:
                    gp_map[match_pf.group(1).lower()].append(Time(match_pf.group(2)))
            for k, v in gp_map.iteritems():
                v.sort()
                logger.info('Gridpoint files found: domain=%s, terms=%s',
                            k,
                            ','.join([str(t) for t in v]))
        if len(gp_map) == 0:
            logger.info('No gridpoint file was found.')
        sh.json_dump(gp_map, 'gridpoint_map.out', indent=4, cls=ShellEncoder)

        # Gather DDH in folders
        if self.ddhpack:
            ddhmap = dict(DL='dlimited', GL='global', ZO='zonal')
            for (prefix, ddhkind) in ddhmap.iteritems():
                flist = sh.glob('DHF{}{}+*'.format(prefix, self.xpname))
                if flist:
                    dest = 'ddhpack_{}'.format(ddhkind)
                    logger.info('Creating a DDH pack: %s', dest)
                    sh.mkdir(dest)
                    for lfa in flist:
                        sh.mv(lfa, dest, fmt='lfa')

        super(Forecast, self).postfix(rh, opts)


class LAMForecast(Forecast):
    """Forecast for IFS-like Limited Area Models."""

    _footprint = dict(
        info = "Run a forecast with an Arpege/IFS like Limited Area Model.",
        attr = dict(
            kind = dict(
                values   = ['lamfc', 'lamforecast'],
                remap    = dict(lamforecast = 'lamfc'),
            ),
            synctool = dict(
                info            = 'The name of the script called when waiting for coupling files',
                optional        = True,
                default         = 'atcp.alad',
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            ),
            synctpl = dict(
                info            = 'The template used to generate the *synctool* script',
                optional        = True,
                default         = '@sync-fetch.tpl',
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            ),
        )
    )

    def spawn_command_options(self):
        """Dictionary provided for command line factory."""
        return dict(
            name       = (self.xpname + 'xxxx')[:4].upper(),
            timescheme = self.timescheme,
            timestep   = self.timestep,
            fcterm     = self.fcterm,
            fcunit     = self.fcunit,
            model      = 'aladin',
        )

    def prepare(self, rh, opts):
        """Default pre-link for boundary conditions files."""
        super(LAMForecast, self).prepare(rh, opts)

        sh = self.system

        # Check boundaries conditions
        cplrh = [x.rh for x in self.context.sequence.effective_inputs(
            role = 'BoundaryConditions',
            kind = 'boundary'
        )]
        cplrh.sort(key=lambda rh: rh.resource.date + rh.resource.term)

        # Ordered pre-linking of boundaring and building ot the synchronization tools
        firstsync = None
        sh.header('Check boundaries...')
        if any([x.is_expected() for x in cplrh]):
            logger.info('Some boundaries conditions are still expected')
            self.mksync = True
        else:
            logger.info('All boundaries conditions available')
            self.mksync = False

        for i, bound in enumerate(cplrh):
            thisbound = bound.container.localpath()
            sh.softlink(thisbound, 'ELSCF{0:s}ALBC{1:03d}'.format(self.xpname, i))
            if self.mksync:
                thistool = self.synctool + '.{0:03d}'.format(i)
                bound.mkgetpr(pr_getter=thistool, tplfetch=self.synctpl)
                if firstsync is None:
                    firstsync = thistool

        # Set up the first synchronization step
        if firstsync is not None:
            sh.symlink(firstsync, self.synctool)

    def postfix(self, rh, opts):
        """Post forecast information and cleaning."""
        sh = self.system

        if self.mksync:
            synclog = self.synctool + '.log'
            if sh.path.exists(synclog):
                sh.subtitle(synclog)
                sh.cat(synclog, output=False)

        super(LAMForecast, self).postfix(rh, opts)


class DFIForecast(LAMForecast):

    _footprint = dict(
        info = "Run a forecast with an Arpege/IFS like Limited Area Model (with DFIs).",
        attr = dict(
            kind = dict(
                values = ['fcdfi'],
            ),
        )
    )

    def prepare(self, rh, opts):
        """Pre-link boundary conditions as special DFI files."""
        super(DFIForecast, self).prepare(rh, opts)
        initname = 'ICMSH{0:s}INIT'.format(self.xpname)
        for pseudoterm in (999, 0, 1):
            self.system.softlink(initname, 'ELSCF{0:s}ALBC{1:03d}'.format(self.xpname, pseudoterm))


class FullPos(IFSParallel):
    """FUllpos for geometries transforms in IFS-like Models."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            xpname = dict(
                default = 'FPOS'
            ),
            flyput = dict(
                default  = False,
                values   = [False],
            ),
            server_run = dict(
                values   = [True, False],
            ),
            serversync_method = dict(
                default  = 'simple_socket',
            ),
            serversync_medium = dict(
                default  = 'cnt3_wait',
            ),
        )
    )

    @property
    def realkind(self):
        return 'fullpos'


class FullPosGeo(FullPos):
    """FUllpos for geometries transforms in IFS-like Models."""

    _footprint = dict(
        info = "Run a fullpos to interpolate to a new geometry",
        attr = dict(
            kind = dict(
                values  = ['l2h', 'h2l'],
            ),
        )
    )

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

        initrh = [x.rh for x in self.context.sequence.effective_inputs(
            role = ('Analysis', 'Guess', 'InitialCondition'),
            kind = ('analysis', 'historic', 'ic', re.compile('(stp|ana)min'),
                    re.compile('pert'), ),
        )]

        # is there one (deterministic forecast) or many (ensemble forecast) fullpos to perform ?
        isMany = len(initrh) > 1
        do_fix_input_clim = not self.system.path.exists('Const.Clim')
        do_fix_output_clim = not self.system.path.exists('const.clim.000')
        infile = 'ICMSH{0:s}INIT'.format(self.xpname)

        for num, r in enumerate(initrh):
            str_subtitle = 'Fullpos execution on {}'.format(r.container.localpath())
            sh.subtitle(str_subtitle)

            # Set the actual init file
            if sh.path.exists(infile):
                if isMany:
                    logger.critical('Cannot process multiple Historic files if %s exists.', infile)
            else:
                sh.cp(r.container.localpath(), infile, fmt=r.container.actualfmt, intent=intent.IN)

            # Fix links for climatology files
            actualmonth = Month(r.resource.date + r.resource.term)
            startingclim = r.resource.geometry

            def check_month_and_inputgeo(actualrh):
                return bool(hasattr(actualrh.resource, 'month') and
                            actualrh.resource.month == actualmonth and
                            actualrh.resource.geometry.tag == startingclim.tag)

            if do_fix_input_clim:
                sh.remove('Const.Clim')
                logger.info("Linking in the Initial clim file (Const.Clim) " +
                            "for month %s and geometry == %s.", actualmonth, startingclim.tag)
                self.setlink(
                    initrole = (re.compile('^Clim'), re.compile('Clim$')),
                    initkind = 'clim_model',
                    initname = 'Const.Clim',
                    inittest = check_month_and_inputgeo
                )

            def check_month_and_othergeo(actualrh):
                return bool(hasattr(actualrh.resource, 'month') and
                            actualrh.resource.month == actualmonth and
                            actualrh.resource.geometry.tag != startingclim.tag)

            if do_fix_output_clim:
                sh.remove('const.clim.000')
                logger.info("Linking in the Target clim file (const.clim.000) " +
                            "for month %s and geometry != %s.", actualmonth, startingclim.tag)
                self.setlink(
                    initrole = (re.compile('^Clim'), re.compile('Clim$')),
                    initkind = 'clim_model',
                    initname = 'const.clim.000',
                    inittest = check_month_and_othergeo
                )

            # Standard execution
            super(FullPosGeo, self).execute(rh, opts)

            # prepares the next execution
            if isMany:
                # Set a local storage place
                runstore = 'RUNOUT'
                sh.mkdir(runstore)
                # Freeze the current output
                for posfile in [x for x in sh.glob('PF{0:s}*+*'.format(self.xpname))]:
                    sh.move(posfile, sh.path.join(runstore, 'pfout_{:d}'.format(num)), fmt = r.container.actualfmt)

                sh.remove(infile, fmt=r.container.actualfmt)

                if not self.server_run:
                    # The only one listing
                    sh.cat('NODE.001_01', output='NODE.all')
                    # Some cleaning
                    sh.rmall('ncf927', 'dirlst')

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        sh = self.system

        initrh = [x.rh for x in self.context.sequence.effective_inputs(
            role = ('Analysis', 'Guess', 'InitialCondition'),
            kind = ('analysis', 'historic', 'ic', re.compile('(stp|ana)min'),
                    re.compile('pert'), ),
        )]
        if len(initrh) > 1:
            for num, r in enumerate(initrh):
                sh.move('RUNOUT/pfout_{:d}'.format(num),
                        'PF' + re.sub('^(?:ICMSH)(.*?)(?:INIT)(.*)$', r'\1\2', r.container.localpath()).format(self.xpname),
                        fmt=r.container.actualfmt)

        super(FullPosGeo, self).postfix(rh, opts)


class FullPosBDAP(FullPos):
    """Post-processing for IFS-like Models."""

    _footprint = dict(
        info = "Run a fullpos to post-process raw model outputs",
        attr = dict(
            kind = dict(
                values  = ['fullpos', 'fp'],
                remap   = dict(fp= 'fullpos')
            ),
            fcterm = dict(
                values = [0, ],
            ),
            outputid = dict(
                info        = "The identifier for the encoding of post-processed fields.",
                type        = str,
                optional    = True,
            ),
            server_run = dict(
                values   = [False, ],
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Some additional checks."""
        if self.system.path.exists('xxt00000000'):
            raise AlgoComponentError('There should be no file named xxt00000000 in the working directory')
        super(FullPosBDAP, self).prepare(rh, opts)

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

        namrh = [x.rh for x in self.context.sequence.effective_inputs(
            kind = 'namelistfp'
        )]

        namxx = [x.rh for x in self.context.sequence.effective_inputs(
            role = 'FullPosSelection',
            kind = 'namselect',
        )]

        initrh = [x.rh for x in self.context.sequence.effective_inputs(
            role = ('InitialCondition', 'ModelState'),
            kind = 'historic',
        )]
        initrh.sort(key=lambda rh: rh.resource.term)

        for r in initrh:
            sh.subtitle('Loop on {0:s}'.format(r.resource.term.fmthm))
            thesenames = list()

            thisdate = r.resource.date + r.resource.term
            thismonth = thisdate.month
            logger.info('Fullpos <month:%s>' % thismonth)
            for bdaprh in [x.rh for x in self.context.sequence.effective_inputs(
                role = 'LocalClim',
                kind = 'clim_bdap',
            ) if x.rh.resource.month == thismonth]:
                thisclim = bdaprh.container.localpath()
                thisname = 'const.clim.' + bdaprh.resource.geometry.area
                if thisclim != thisname:
                    thesenames.append(thisname)
                    sh.symlink(thisclim, thisname)

            # Set a local storage place
            runstore = 'RUNOUT' + r.resource.term.fmtraw
            sh.mkdir(runstore)

            # Define an input namelist
            try:
                namfp = [x for x in namrh if x.resource.term == r.resource.term].pop()
                namfplocal = namfp.container.localpath()
                if self.outputid is not None:
                    namfp.contents.setmacro('OUTPUTID', self.outputid)
                    logger.info('Setup macro OUTPUTID=%s in %s', self.outputid, namfplocal)
                namfp.contents.rewrite(namfp.container)
                sh.remove('fort.4')
                sh.symlink(namfplocal, 'fort.4')
            except Exception:
                logger.critical('Could not get a fullpos namelist for term %s', r.resource.term)
                raise

            # Define an selection namelist
            try:
                namxt = [x for x in namxx if x.resource.term == r.resource.term].pop()
                sh.remove('xxt00000000')
                sh.symlink(namxt.container.localpath(), 'xxt00000000')
            except Exception:
                logger.critical('Could not get a selection namelist for term %s', r.resource.term)
                raise

            # Finaly set the actual init file
            sh.remove('ICMSH{0:s}INIT'.format(self.xpname))
            sh.softlink(r.container.localpath(), 'ICMSH{0:s}INIT'.format(self.xpname))

            # Standard execution
            super(FullPosBDAP, self).execute(rh, opts)

            # Freeze the current output
            for posfile in [x for x in (sh.glob('PF{0:s}*+*'.format(self.xpname)) +
                                        sh.glob('GRIBPF{0:s}*+*'.format(self.xpname)))]:
                rootpos = re.sub('0+$', '', posfile)
                sh.move(
                    posfile,
                    sh.path.join(runstore, rootpos + r.resource.term.fmthm),
                    fmt = 'grib' if posfile.startswith('GRIB') else 'lfi',
                )
            for logfile in sh.glob('NODE.*', 'std*'):
                sh.move(logfile, sh.path.join(runstore, logfile))

            # Some cleaning
            sh.rmall('PX{0:s}*'.format(self.xpname), fmt='lfi')
            sh.rmall('ncf927', 'dirlst')
            for clim in thesenames:
                sh.rm(clim)

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        sh = self.system

        for fpfile in [x for x in (sh.glob('RUNOUT*/PF{0:s}*'.format(self.xpname)) +
                                   sh.glob('RUNOUT*/GRIBPF{0:s}*+*'.format(self.xpname))) if sh.path.isfile(x)]:
            sh.move(fpfile, sh.path.basename(fpfile),
                    fmt = 'grib' if fpfile.startswith('GRIB') else 'lfi')
        sh.cat('RUNOUT*/NODE.001_01', output='NODE.all')

        super(FullPosBDAP, self).postfix(rh, opts)
