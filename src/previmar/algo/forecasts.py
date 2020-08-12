#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SURGES HYCOM
"""
from __future__ import print_function, absolute_import, unicode_literals, division

import re
import footprints
from bronx.fancies import loggers
from collections import defaultdict
from vortex.algo.components import Parallel, ParaBlindRun
from vortex.tools.parallelism import VortexWorkerBlindRun
from taylorism import Boss
#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class WithoutCouplingForecasts(Parallel):

    _footprint = dict(
        attr = dict(
            flyargs = dict(
                default = ('ASUR', 'PSUR',),
            ),
            flypoll = dict(
                values = ['iopoll_marine'],
                optional = True,
            ),
            io_poll_med = dict(
                values = ['med_io_poll'],
            ),
            pollingdir = dict(
                type = footprints.FPList,
                default = footprints.FPList(['RES0.', ]),
                optional = True,

            ),
        )
    )

    def prepare(self, rh, opts):
        """Add some defaults env values for mpitool itself."""
        super(Parallel, self).prepare(rh, opts)
        if opts.get('mpitool', True):
            self.export('mpitool')

        if self.promises:
            self.io_poll_kwargs = dict(model=rh.resource.model, forcage=rh.resource.forcage, pollingdir=self.pollingdir)
            self.flyput = True
        else:
            self.flyput = False

    def execute(self, rh, opts):
        super(WithoutCouplingForecasts, self).execute(rh, opts)


class SurgesCouplingForecasts(Parallel):
    """Surges Coupling"""
    _footprint = dict(
        attr = dict(
            binary = dict(
                values = ['hycomcoupling'],
            ),
            config_name = dict(
                info     = "Name of configuration",
                default  = "",
                optional = True,
                type     = str,
            ),
            numod = dict(
                info     = "model ID",
                optional = True,
                default  = 165,
            ),
            codmod = dict(
                info     = "Data base BDAP Name of modele",
                type     = str,
                optional = True,
                default  = '',
            ),
            fcterm = dict(
                default  = 6,
                optional = True,
            ),
            freq_forcage = dict(
                info     = "Atmospheric grib forcing frequency (minutes)",
                default  = 180,
                optional = True,
            ),
            rstfin = dict(
                info     = "Term max of saving restart files",
                default  = 6,
                optional = True,
            ),
            flyargs = dict(
                default = ('ASUR', 'PSUR',),
            ),
            flypoll = dict(
                default = 'iopoll_marine',
            ),
            dir_exec = dict(
                default = 'EXEC_OASIS',
            ),
            pollingdir = dict(
                type = footprints.FPList,
                default = footprints.FPList(['RES0.', ]),
                optional = True,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Add some defaults env values for mpitool itself."""
        super(Parallel, self).prepare(rh, opts)
        if opts.get('mpitool', True):
            self.export('mpitool')

        # Tweak the pseudo hycom namelists New version  !
        for namsec in self.context.sequence.effective_inputs(role=re.compile('FileConfig')):

            r = namsec.rh

            term = str(self.fcterm)
            basedate = r.resource.date
            date = basedate.ymdh
            reseau = basedate.hh

            # Creation Dico des valeurs/cle a changer selon experience
            dico = {}
            if r.resource.param == 'ms':  # tideonly experiment
                dico["heures"] = term
                dico["savfin"] = term
                dico["rstfin"] = str(self.rstfin)
                dico["dateT0"] = date
            else:  # full experiment
                dico["heures"] = term
                dico["savfin"] = term
                dico["h_rese"] = reseau
                dico["modele"] = r.provider.vconf.upper()[-3:]
                xp = r.provider.vconf[-5:-3]
                mode_map = dict(fc='PR', an='AA')
                dico["anapre"] = mode_map.get(xp, xp)
                dico["nmatm"] = str(self.freq_forcage)
                if r.provider.vconf not in ['oin@fcaro','oin@ancep']:
                    dico["codmod"] = self.codmod
                dico["imodel"] = str(self.numod)
                dico["kmodel"] = self.config_name

            # modification du content
            paramct = r.contents
            paramct.substitute(dico)
            r.save()
            r.container.cat()

        # Promises should be nicely managed by a co-process
        if self.promises:
            self.io_poll_kwargs = dict(model=r.resource.model, forcage=r.resource.forcage, pollingdir=self.pollingdir)
            self.flyput = True
        else:
            self.flyput = False

    def execute(self, rh, opts):
        """Jump into the correct working directory."""
        tmpwd = self.dir_exec
        logger.info('Temporarily change the working dir to ./%s', tmpwd)
        with self.system.cdcontext(tmpwd):
            super(SurgesCouplingForecasts, self).execute(rh, opts)


class SurgesCouplingInterp(SurgesCouplingForecasts):
    """Algo for interpolation case, not documented yet"""
    _footprint = dict(
        attr = dict(
            binary = dict(
                values = ['hycominterp'],
            ),
        )
    )


class Grib2tauxParallel(ParaBlindRun):
    """Algo for parallel grib2taux"""
    _footprint = dict(
        info = 'AlgoComponent that runs serial binary grib2taux',
        attr = dict(
            kind = dict(
                values = ['Grib2tauxParaBlindRun'],
            ),
            verbose = dict(
                info        = 'Run in verbose mode',
                type        = bool,
                default     = True,
                optional    = True,
                doc_zorder  = -50,
            ),
        )
    )

    def _default_pre_execute(self, rh, opts):
        """Change default initialisation to use LongerFirstScheduler"""
        # Start the task scheduler
        self._boss = Boss(verbose=self.verbose,
                          scheduler=footprints.proxy.scheduler(limit='threads',
                                                               max_threads=10,
                                                               ))
        logger.info('COUCOU boss')
        self._boss.make_them_work()

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        scheduler_instructions = defaultdict(list)
        sh = self.system
        workdir = sh.pwd()

        file_out = 'forcing.mslprs.b'
        for zone in ['zone1', 'zone2', 'zone3', 'zone4']:

            with sh.cdcontext(zone, create=False):

                if not self.system.path.exists('grib2taux'):
                    sh.softlink(sh.path.join(workdir, 'grib2taux'),
                                'grib2taux')

                if sh.path.exists(file_out):  # rustine car continue a boucler apres 4 iter
                    logger.info('output cree  execute on arrete ! %s', file_out)
                    break

                scheduler_instructions['name'].append('{:s}'.format(zone))
                scheduler_instructions['progname'].append(sh.path.join(workdir, zone, 'grib2taux'))
                scheduler_instructions['base'].append(zone)
                scheduler_instructions['memory'].append('100')
                scheduler_instructions['expected_time'].append('100')
                scheduler_instructions['subdir'].append(zone)
                scheduler_instructions['progtaskset'].append('raw')

        self._default_pre_execute(rh, opts)
        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)
        logger.info("common_i %s", common_i)
        common_i.update(dict(workdir=workdir, ))
        self._add_instructions(common_i, scheduler_instructions)
        logger.info('scheduler_instruction %s', scheduler_instructions)
        print('Intermediate report:', self._boss.get_report())
        self._boss.wait_till_finished()


class Grib2tauxWorker(VortexWorkerBlindRun):
    """Transform wind and pressure"""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['Grib2tauxParaBlindRun'],
            ),
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = True
            ),
        )
    )

    def vortex_task(self, **kwargs):
        logger.info("self.subdir %s", self.subdir)
        file_out = 'forcing.mslprs.b'
        logger.info("file_out %s", file_out)

        rundir = self.system.getcwd()
        if self.subdir is not None:
            thisdir = self.system.path.join(rundir, self.subdir)
            logger.info('thisdir %s', thisdir)
            with self.system.cdcontext(thisdir, create=False):
                if self.system.path.exists(file_out):
                    logger.info('output cree %s', file_out)
                    # Deal with promised resources
                    expected = [x for x in self.context.sequence.outputs()
                                if (x.rh.provider.expected and
                                    x.rh.container.localpath() == file_out)]
                    for thispromise in expected:
                        thispromise.put(incache=True)
                    else:
                        logger.warning('Missing some output for %s', file_out)
                self.local_spawn('stdout.listing')
        else:
            thisdir = rundir
            # Freeze the current output
            if self.system.path.exists(file_out):
                logger.info('output cree %s', file_out)
                self.system.cp(file_out, '../.', fmt='ascii')
            else:
                logger.warning('Missing some grib output for %s',
                               file_out)
