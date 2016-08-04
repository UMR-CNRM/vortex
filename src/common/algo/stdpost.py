#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
import json

import footprints
from footprints.stdtypes import FPTuple
logger = footprints.loggers.getLogger(__name__)

from vortex.layout.monitor    import BasicInputMonitor
from vortex.algo.components   import TaylorRun, BlindRun, ParaBlindRun, AlgoComponentError
from vortex.syntax.stdattrs   import DelayedEnvValue, FmtInt
from vortex.tools             import grib
from vortex.tools.fortran     import NamelistBlock
from vortex.tools.parallelism import TaylorVortexWorker, VortexWorkerBlindRun
from vortex.tools.systems     import ExecutionError

from common.tools.grib        import GRIBFilter


class _FA2GribWorker(VortexWorkerBlindRun):
    """The taylorism worker that actually do the gribing (in parallel).

    This is called indirectly by taylorism when :class:`Fa2Grib` is used.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['fa2grib']
            ),
            # Progrid parameters
            fortnam = dict(),
            fortinput = dict(),
            compact = dict(),
            timeshift = dict(
                type = int
            ),
            timeunit = dict(
                type = int
            ),
            numod = dict(
                type = int
            ),
            sciz = dict(
                type = int
            ),
            scizoffset = dict(
                type = int,
                optional = True
            ),
            # Input/Output data
            file_in = dict(),
            file_out = dict(),
            member = dict(
                type = FmtInt,
                optional = True,
            )
        )
    )

    def vortex_task(self, **kwargs):

        logger.info("Starting the Fa2Grib processing for tag=%s", self.name)

        thisoutput = 'GRIDOUTPUT'
        rdict = dict(rc=True)

        # First, check that the hooks were applied
        for thisinput in [x for x in self.context.sequence.inputs()
                          if x.rh.container.localpath() == self.file_in]:
            if thisinput.rh.delayhooks:
                thisinput.rh.apply_get_hooks()

        # Jump into a working directory
        cwd = self.system.pwd()
        tmpwd = self.system.path.join(cwd, self.file_out + '.process.d')
        self.system.mkdir(tmpwd)
        self.system.cd(tmpwd)

        # Build the local namelist block
        nb = NamelistBlock(name='NAML')
        nb.NBDOM = 1
        nb.CHOPER = self.compact
        nb.INUMOD = self.numod
        if self.scizoffset is not None:
            nb.ISCIZ = self.scizoffset + (self.member if self.member is not None else 0)
        else:
            if self.sciz:
                nb.ISCIZ = self.sciz
        if self.timeshift:
            nb.IHCTPI = self.timeshift
        if self.timeunit:
            nb.ITUNIT = self.timeunit
        nb['CLFSORT(1)'] = thisoutput
        nb['CDNOMF(1)'] = self.fortinput
        with open(self.fortnam, 'w') as namfd:
            namfd.write(nb.dumps())

        # Finally set the actual init file
        self.system.softlink(self.system.path.join(cwd, self.file_in),
                             self.fortinput)

        # Standard execution
        list_name = self.system.path.join(cwd, self.file_out + ".listing")
        try:
            self.local_spawn(list_name)
        except ExecutionError as e:
            rdict['rc'] = e

        # Freeze the current output
        if self.system.path.exists(thisoutput):
            self.system.move(thisoutput, self.system.path.join(cwd, self.file_out))
        else:
            logger.warning('Missing some grib output: %s', self.file_out)
            rdict['rc'] = False

        # Final cleaning
        self.system.cd(cwd)
        self.system.remove(tmpwd)

        if self.system.path.exists(self.file_out):
            # Deal with promised resources
            expected = [x for x in self.context.sequence.outputs()
                        if x.rh.provider.expected and x.rh.container.localpath() == self.file_out]
            for thispromise in expected:
                thispromise.put(incache=True)

        logger.info("Fa2Grib processing is done for tag=%s", self.name)

        return rdict


class _GribFilterWorker(TaylorVortexWorker):
    """The taylorism worker that actually filter the gribfiles.

    This is called indirectly by taylorism when :class:`Fa2Grib` is used.
    """

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['gribfilter']
            ),
            # Filter settings
            filters = dict(
                type = FPTuple,
            ),
            concatenate = dict(
                type = bool,
            ),
            # Input/Output data
            file_in = dict(),
            file_outfmt = dict(),
        )
    )

    def vortex_task(self, **kwargs):

        logger.info("Starting the GribFiltering for tag=%s", self.file_in)

        rdict = dict(rc=True)

        # Create the filtering object and add filters
        gfilter = GRIBFilter(concatenate=self.concatenate)
        if self.filters:
            gfilter.add_filters(* list(self.filters))

        # Process the input file
        newfiles = gfilter(self.file_in, self.file_outfmt)

        if newfiles:
            # Deal with promised resources
            allpromises = [x for x in self.context.sequence.outputs()
                           if x.rh.provider.expected]
            for newfile in newfiles:
                expected = [x for x in allpromises
                            if x.rh.container.localpath() == newfile]
                for thispromise in expected:
                    thispromise.put(incache=True)

        else:
            logger.warning('No file has been generated.')
            rdict['rc'] = False

        logger.info("GribFiltering is done for tag=%s", self.name)

        return rdict


class Fa2Grib(ParaBlindRun):
    """Standard FA conversion, e.g. with PROGRID as a binary resource."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'fa2grib' ],
            ),
            timeout = dict(
                type = int,
                optional = True,
                default = 300,
            ),
            refreshtime = dict(
                type = int,
                optional = True,
                default = 20,
            ),
            fatal = dict(
                type = bool,
                optional = True,
                default = True,
            ),
            fortnam = dict(
                optional = True,
                default  = 'fort.4',
            ),
            fortinput = dict(
                optional = True,
                default  = 'fort.11',
            ),
            compact = dict(
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_COMPACT', 'L'),
            ),
            timeshift = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_SHIFT', 0),
            ),
            timeunit = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_TUNIT', 1),
            ),
            numod = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_NUMOD', 221),
            ),
            sciz = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_SCIZ', 0),
            ),
            scizoffset = dict(
                type     = int,
                optional = True,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Fa2Grib, self).prepare(rh, opts)
        self.system.remove(self.fortinput)
        self.env.DR_HOOK_NOT_MPI = 1

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        # Update the common instructions
        common_i.update(dict(fortnam=self.fortnam, fortinput=self.fortinput,
                             compact=self.compact, numod=self.numod,
                             sciz=self.sciz, scizoffset=self.scizoffset,
                             timeshift=self.timeshift, timeunit=self.timeunit))
        tmout = False

        # Monitor for the input files
        bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                               role='Gridpoint', kind='gridpoint')
        with bm:
            while not bm.all_done or len(bm.available) > 0:

                while bm.available:
                    s = bm.pop_available().section
                    file_in = s.rh.container.localpath()
                    # Find the name of the output file
                    if s.rh.provider.member is not None:
                        file_out = 'GRIB{0:s}_{1!s}+{2:s}'.format(s.rh.resource.geometry.area,
                                                                  s.rh.provider.member,
                                                                  s.rh.resource.term.fmthm)
                    else:
                        file_out = 'GRIB{0:s}+{1:s}'.format(s.rh.resource.geometry.area,
                                                            s.rh.resource.term.fmthm)
                    logger.info("Adding input file %s to the job list", file_in)
                    self._add_instructions(common_i,
                                           dict(name=[file_in, ],
                                                file_in=[file_in, ], file_out=[file_out, ],
                                                member=[s.rh.provider.member, ]))

                # Timeout ?
                if (self.timeout > 0) and (bm.inactive_time > self.timeout):
                    logger.error("The waiting loop timed out (%d seconds)", self.timeout)
                    logger.error("The following files are still unaccounted for: %s",
                                 ",".join([e.section.rh.container.localpath()
                                           for e in bm.expected.itervalues()]))
                    tmout = True
                    break

                # Wait a little bit :-)
                if not bm.all_done or len(bm.available) > 0:
                    self.system.sleep(1)

        self._default_post_execute(rh, opts)

        if bm.failed:
            for failed_files in [e.section.rh.container.localpath()
                                 for e in bm.failed.itervalues()]:
                logger.error("We were unable to fetch the following file: %s",
                             failed_files)
                if self.fatal:
                    self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_files)),
                                               traceback=False)

        if tmout:
            raise IOError("The waiting loop timed out")


class StandaloneGRIBFilter(TaylorRun, grib.GribApiComponent):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'gribfilter' ],
            ),
            timeout = dict(
                type = int,
                optional = True,
                default = 300,
            ),
            refreshtime = dict(
                type = int,
                optional = True,
                default = 20,
            ),
            concatenate = dict(
                type = bool,
                default =False,
                optional = True,
            ),
        )
    )

    def execute(self, rh, opts):

        # We re-serialise data because footprints don't like dictionaries
        filters = [json.dumps(x.rh.contents.data)
                   for x in self.context.sequence.effective_inputs(role='GRIBFilteringRequest',
                                                                   kind='filtering_request')]
        filters = FPTuple(filters)

        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        # Update the common instructions
        common_i.update(dict(concatenate=self.concatenate,
                             filters=filters))
        tmout = False

        # Monitor for the input files
        bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                               role='Gridpoint', kind='gridpoint')
        with bm:
            while not bm.all_done or len(bm.available) > 0:

                while bm.available:
                    s = bm.pop_available().section
                    file_in = s.rh.container.localpath()
                    file_outfmt = re.sub(r'^(.*?)((:?\.[^.]*)?)$', r'\1_{filtername:s}\2', file_in)

                    logger.info("Adding input file %s to the job list", file_in)
                    self._add_instructions(common_i,
                                           dict(name=[file_in, ],
                                                file_in=[file_in, ], file_outfmt=[file_outfmt, ]))

                # Timeout ?
                if (self.timeout > 0) and (bm.inactive_time > self.timeout):
                    logger.error("The waiting loop timed out (%d seconds)", self.timeout)
                    logger.error("The following files are still unaccounted for: %s",
                                 ",".join([e.section.rh.container.localpath()
                                           for e in bm.expected.itervalues()]))
                    tmout = True
                    break

                # Wait a little bit :-)
                if not bm.all_done or len(bm.available) > 0:
                    self.system.sleep(1)

        self._default_post_execute(rh, opts)

        if bm.failed:
            for failed_files in [e.section.rh.container.localpath()
                                 for e in bm.failed.itervalues()]:
                logger.error("We were unable to fetch the following file: %s",
                             failed_files)
                if self.fatal:
                    self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_files)),
                                               traceback=False)

        if tmout:
            raise IOError("The waiting loop timed out")


class AddField(BlindRun):
    """Miscellaneous manipulation on input FA resources."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'addcst', 'addconst', 'addfield' ],
                remap = dict(
                    addconst = 'addcst',
                ),
            ),
            fortnam = dict(
                optional = True,
                default = 'fort.4',
            ),
            fortinput = dict(
                optional = True,
                default = 'fort.11',
            ),
            fortoutput = dict(
                optional = True,
                default = 'fort.12',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(AddField, self).prepare(rh, opts)
        self.system.remove(self.fortinput)
        self.env.DR_HOOK_NOT_MPI = 1

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        # Is there any namelist provided ?
        namrh = [ x.rh for x in self.context.sequence.effective_inputs(role=('Namelist'), kind='namelist') ]
        if namrh:
            self.system.softlink(namrh[0].container.localpath(), self.fortnam)
        else:
            logger.warning('Do not find any namelist for %s', self.kind)

        # Look for some sources files
        srcrh = [ x.rh for x in self.context.sequence.effective_inputs(role=('Gridpoint', 'Sources'),
                                                                       kind='gridpoint') ]
        srcrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))

        for r in srcrh:
            self.system.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                           r.resource.term.fmthm))

            # Some cleaning
            self.system.remove(self.fortinput)
            self.system.remove(self.fortoutput)

            # Prepare double input
            self.system.link(r.container.localpath(), self.fortinput)
            self.system.cp(r.container.localpath(), self.fortoutput)

            # Standard execution
            opts['loop'] = r.resource.term
            super(AddField, self).execute(rh, opts)

            # Some cleaning
            self.system.rmall('DAPDIR', self.fortinput, self.fortoutput)

    def postfix(self, rh, opts):
        """Post add cleaning."""
        super(AddField, self).postfix(rh, opts)
        self.system.remove(self.fortnam)


class DiagPE(BlindRun, grib.GribApiComponent):
    """Execution of diagnostics on grib input (ensemble forecasts specific)."""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'diagpe' ],
            ),
            method = dict(
                info   = 'The method used to compute the diagnosis',
                values = [ 'neighbour' ],
            ),
            numod = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_NUMOD', 118),
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(DiagPE, self).prepare(rh, opts)
        # Prevent DrHook to initialise MPI and setup grib_api
        for optpack in ('drhook_not_mpi', ):
            self.export(optpack)
        self.gribapi_setup(rh, opts)

    def spawn_hook(self):
        """Usually a good habit to dump the fort.4 namelist."""
        super(DiagPE, self).spawn_hook()
        if self.system.path.exists('fort.4'):
            self.system.subtitle('{0:s} : dump namelist <fort.4>'.format(self.realkind))
            self.system.cat('fort.4', output=False)

    def execute(self, rh, opts):
        """Loop on the various grib files provided."""

        srcsec = self.context.sequence.effective_inputs(role=('Gridpoint', 'Sources'),
                                                        kind='gridpoint')
        # Find out what are the terms
        terms = sorted(set([s.rh.resource.term for s in srcsec]))
        # Find out the number of members
        members = sorted(set([s.rh.provider.member for s in srcsec]))
        # Check that the date is consistent among inputs
        basedates = list(set([s.rh.resource.date for s in srcsec]))
        if len(basedates) > 1:
            raise AlgoComponentError('The date must be consistent among the input resources')
        basedate = basedates[-1]

        for term in terms:
            # Tweak the namelist
            namsec = self.setlink(initrole='Namelist', initkind='namelist', initname='fort.4')
            for nam in [ x.rh for x in namsec if 'NAM_PARAM' in x.rh.contents ]:
                logger.info("Substitute the date (%s) to AAAAMMJJHH namelist entry", basedate.ymdh)
                nam.contents['NAM_PARAM']['AAAAMMJJHH'] = basedate.ymdh
                logger.info("Substitute the number of members (%d) to NBRUN namelist entry", len(members))
                nam.contents['NAM_PARAM']['NBRUN'] = len(members)
                logger.info("Substitute the the number of terms to NECH(0) namelist entry")
                nam.contents['NAM_PARAM']['NECH(0)'] = 1
                logger.info("Substitute the ressource term to NECH(1) namelist entry")
                # NB: term should be expressed in minutes
                nam.contents['NAM_PARAM']['NECH(1)'] = int(term)
                nam.contents['NAM_PARAM']['ECHFINALE'] = terms[-1].hour
                # Now, update the model number for the GRIB files
                logger.info("Substitute the model number (%d) to namelist entry", self.numod)
                nam.contents['NAM_PARAM']['NMODELE'] = self.numod
                # We are done with the namelist
                nam.save()

            # Standard execution
            opts['loop'] = term
            super(DiagPE, self).execute(rh, opts)


class DiagPI(BlindRun, grib.GribApiComponent):
    """Execution of diagnostics on grib input (deterministic forecasts specific)."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'diagpi', 'diaglabo' ],
            ),
            numod = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_NUMOD', 62),
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(DiagPI, self).prepare(rh, opts)
        # Prevent DrHook to initialise MPI and setup grib_api
        for optpack in ('drhook_not_mpi', ):
            self.export(optpack)
        self.gribapi_setup(rh, opts)

    def spawn_hook(self):
        """Usually a good habit to dump the fort.4 namelist."""
        super(DiagPI, self).spawn_hook()
        if self.system.path.exists('fort.4'):
            self.system.subtitle('{0:s} : dump namelist <fort.4>'.format(self.realkind))
            self.system.cat('fort.4', output=False)

    def execute(self, rh, opts):
        """Loop on the various grib files provided."""

        # Intialise a GRIBFilter (at least try to)
        gfilter = GRIBFilter(concatenate=False)
        gfilter.add_filters(self.context)

        srcsec = self.context.sequence.effective_inputs(role=('Gridpoint', 'Sources'),
                                                        kind='gridpoint')
        srcsec.sort(lambda a, b: cmp(a.rh.resource.term, b.rh.resource.term))
        for sec in srcsec:
            r = sec.rh
            self.system.title('Loop on domain {0:s} and term {1:s}'.format(r.resource.geometry.area,
                                                                           r.resource.term.fmthm))
            # Tweak the namelist
            namsec = self.setlink(initrole='Namelist', initkind='namelist', initname='fort.4')
            for nam in [ x.rh for x in namsec if 'NAM_PARAM' in x.rh.contents ]:
                logger.info("Substitute the date (%s) to AAAAMMJJHH namelist entry", r.resource.date.ymdh)
                nam.contents['NAM_PARAM']['AAAAMMJJHH'] = r.resource.date.ymdh
                logger.info("Substitute the the number of terms to NECH(0) namelist entry")
                nam.contents['NAM_PARAM']['NECH(0)'] = 1
                logger.info("Substitute the ressource term to NECH(1) namelist entry")
                # NB: term should be expressed in minutes
                nam.contents['NAM_PARAM']['NECH(1)'] = int(r.resource.term)
                # Add the member number in a dedicated namelist block
                if r.provider.member is not None:
                    mblock = nam.contents.newblock('NAM_PARAMPE')
                    mblock['NMEMBER'] = int(r.provider.member)
                # Now, update the model number for the GRIB files
                if 'NAM_DIAG' in x.rh.contents:
                    nmod = self.numod
                    logger.info("Substitute the model number (%d) to namelist entry", nmod)
                    for namk in ('CONV', 'BR', 'HIV', 'ECHOT', 'ICA'):
                        if nam.contents['NAM_DIAG'].has_key(namk) and nam.contents['NAM_DIAG'][namk] != 0:
                            nam.contents['NAM_DIAG'][namk] = nmod
                # We are done with the namelist
                nam.save()

            # Expect the input grib file to be here
            self.grab(sec, comment='diagpi source')
            # Also link in previous grib files in order to compute some winter diagnostics
            srcpsec = [x
                       for x in self.context.sequence.effective_inputs(role=('Preview', 'Previous'),
                                                                       kind='gridpoint')
                       if x.rh.resource.term < r.resource.term]
            for pr in srcpsec:
                self.grab(pr, comment='diagpi additional source for winter diag')

            # Standard execution
            opts['loop'] = r.resource.term
            super(DiagPI, self).execute(rh, opts)

            actualname = r'GRIB[-_A-Z]+{0:s}\+{1:s}'.format(r.resource.geometry.area,
                                                            r.resource.term.fmthm)
            # Find out the output file and filter it
            filtered_out = list()
            if len(gfilter):
                for candidate in [f for f in self.system.glob('GRIB*') if re.match(actualname, f)]:
                    logger.info("Starting GRIB filtering on %s.", candidate)
                    filtered_out = gfilter(candidate, candidate + '_{filtername:s}')

            # The diagnostic output may be promised
            expected = [x for x in self.promises
                        if (re.match(actualname, x.rh.container.localpath()) or
                            x.rh.container.localpath() in filtered_out)]
            for thispromise in expected:
                thispromise.put(incache=True)


class Fa2GaussGrib(BlindRun):
    """Standard FA conversion, e.g. with GOBPTOUT as a binary resource."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['fa2gaussgrib'],
            ),
            fortinput = dict(
                optional = True,
                default = 'PFFPOS_FIELDS',
            ),
            numod = dict(
                type     = int,
                optional = True,
                default  = DelayedEnvValue('VORTEX_GRIB_NUMOD', 212),
            ),
            verbose = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Fa2GaussGrib, self).prepare(rh, opts)
        # Prevent DrHook to initialize MPI and setup grib_api
        self.export('drhook_not_mpi')

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        thisoutput = 'GRID_' + self.fortinput[7:14] + '1'

        gpsec = self.context.sequence.effective_inputs(role=('Historic', 'ModelState'))
        gpsec.sort(lambda a, b: cmp(a.rh.resource.term, b.rh.resource.term))

        for sec in gpsec:
            r = sec.rh

            self.system.title('Loop on files: {:s}'.format(r.container.localpath()))

            # Some preventive cleaning
            self.system.remove(thisoutput)
            self.system.remove('fort.4')

            # Build the local namelist block
            nb = NamelistBlock(name='NAML')
            nb.NBDOM = 1
            nb.INUMOD = self.numod

            nb['LLBAVE'] = self.verbose
            nb['CDNOMF(1)'] = self.fortinput
            with open('fort.4', 'w') as namfd:
                namfd.write(nb.dumps())

            self.system.header('{0:s} : local namelist {1:s} dump'.format(self.realkind, 'fort.4'))
            self.system.cat('fort.4', output=False)

            # Expect the input FP file source to be there...
            self.grab(sec, comment='fullpos source')

            # Finaly set the actual init file
            self.system.softlink(r.container.localpath(), self.fortinput)

            # Standard execution
            super(Fa2GaussGrib, self).execute(rh, opts)

            # Freeze the current output
            if self.system.path.exists(thisoutput):
                self.system.move(thisoutput, 'GGRID' + r.container.localpath()[6:], fmt = r.container.actualfmt)
            else:
                logger.warning('Missing some grib output for %s',
                               thisoutput)

            # Some cleaning
            self.system.rmall(self.fortinput)
