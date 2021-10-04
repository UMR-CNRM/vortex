# -*- coding: utf-8 -*-

"""
Algo for MFWAM production.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six

#: No automatic export
__all__ = []

import io
import time

from bronx.datagrip import namelist as bnamelist
from bronx.fancies import loggers
from bronx.stdtypes.date import Time, Period
from footprints.stdtypes import FPList

from vortex.algo.components import Parallel, ParaBlindRun
from vortex.tools import grib

from vortex.tools.parallelism import VortexWorkerBlindRun
from vortex.layout.monitor import BasicInputMonitor

logger = loggers.getLogger(__name__)


class Mfwam(Parallel, grib.EcGribDecoMixin):
    """Algocomponent for MFWAM."""
    _footprint = dict(
        info='Algo for MFWAM',
        attr = dict(
            kind = dict(
                values = ['MFWAM'],
            ),
            list_guess = dict(
                type     = FPList,
                optional = True,
                default  = list(range(0, 13, 6)),
            ),
            anabegin = dict(
                type     = Period,
                optional = True,
                default  = Period('PT6H'),
            ),
            currentbegin = dict(
                type     = Period,
                optional = True,
                default  = Period('PT6H'),
            ),
            current_coupling = dict(
                optional = True,
                default = False,
            ),
            numod = dict(
                type = int,
                optional = True,
                default = 24,
            ),
            soce = dict(
                type = int,
                optional = True,
                default = 40,
            ),
            fcterm = dict(
                type = Time,
                optional = True,
            ),
            isana = dict(
                type = bool,
                optional = True,
                default = True,
            ),
            deltabegin = dict(
                type     = Period,
                optional = True,
                default  = Period('PT0H'),
            ),
            flyargs = dict(
                default = ('MPP', 'APP',),
            ),
            flypoll = dict(
                default = 'iopoll_waves',
            ),
        )
    )

    def spawn_hook(self):
        """"""
        super(Mfwam, self).spawn_hook()
        if self.system.path.exists('fort.3'):
            self.system.subtitle('{0:s} : dump namelist <fort.3>'.format(self.realkind))
            self.system.cat('fort.3', output=False)

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Mfwam, self).prepare(rh, opts)

        # setup MPI compatibilite
        self.env.update(
            I_MPI_COMPATIBILITY=4,
        )

        fcterm = self.fcterm

        windcandidate = [x.rh
                         for x in self.context.sequence.effective_inputs(role=('Wind',),
                                                                         kind='forcing')]

        # Is there a analysis wind forcing ?
        if len(windcandidate) == 2:
            rhgrib = windcandidate[0]

            # Check for input grib files to concatenate
            rhdict = {rh.container.filename: rh for rh in windcandidate}

            # Check sfwindin
            tmpout = 'sfcwindin'
            if self.system.path.exists(tmpout):
                self.system.rm(tmpout)

            with io.open(tmpout, 'wb') as outfile:
                for fname in [x.container.localpath() for x in sorted(windcandidate,
                                                                      key=lambda rh: rh.resource.begintime)]:
                    with io.open(fname, 'rb') as infile:
                        outfile.write(infile.read())

            # recuperation fcterm
            if fcterm is None:
                fcterm = rhdict['sfcwindin_fc'].resource.endtime
                logger.info('fcterm %s', fcterm)

            datefin = (rhdict['sfcwindin_ana'].resource.date + fcterm).compact()
            datedebana = rhdict['sfcwindin_ana'].resource.date - self.anabegin + self.deltabegin
            datefinana = rhdict['sfcwindin_ana'].resource.date

        elif len(windcandidate) == 1:
            rhgrib = windcandidate[0]

            if not self.system.path.exists('sfcwindin'):
                self.system.cp(rhgrib.container.localpath(), 'sfcwindin',
                               intent='in', fmt=rhgrib.container.actualfmt)

            # recuperation fcterm
            if fcterm is None:
                fcterm = rhgrib.resource.endtime
                logger.info('fcterm %s', fcterm)

            datefin = (rhgrib.resource.date + fcterm).compact()
            datedebana = rhgrib.resource.date - self.anabegin + self.deltabegin
            if self.isana:
                datefinana = rhgrib.resource.date
            else:
                datefinana = datedebana
        else:
            logger.info("%d winds", len(windcandidate))
            raise ValueError("No winds or too many")

        # Untar SAR data if exists
        sarcandidate = self.context.sequence.effective_inputs(role=('ObservationSpec'))
        if len(sarcandidate) > 0:
            rhsar = sarcandidate[0].rh
            self.system.untar(rhsar.container.localpath())

        # Tweak Namelist parameters
        namcandidate = self.context.sequence.effective_inputs(role=('Namelist'),
                                                              kind=('namelist'))

        if len(namcandidate) != 1:
            raise IOError("No or too much namelists for MFWAM")
        namcontents = namcandidate[0].rh.contents

        namcontents.setmacro('CBPLTDT', datedebana.compact())  # debut analyse
        namcontents.setmacro('CDATEF', datefinana.compact())   # fin echeance analyse ici T0
        namcontents.setmacro('CEPLTDT', datefin)  # fin echeance prevision

        if self.current_coupling:
            namcontents.setmacro('CDATECURA', (datedebana - self.currentbegin).compact())

        namcontents.setmacro('NUMOD', self.numod)

        if self.soce:
            namcontents.setmacro('SOCE', self.soce)

        for i in ['PATH', 'CPATH']:
            namcontents.setmacro(i, '.')

        namcandidate[0].rh.save()

        # Tweak Namelist guess dates ad concatenate namcontents
        with io.open('fort.3', 'w') as fhnam:
            for xguess in self.list_guess:
                nblock = bnamelist.NamelistBlock('NAOS')
                nblock["CLSOUT"] = (rhgrib.resource.date + Time(xguess)).compact()
                fhnam.write(nblock.dumps())
            fhnam.write(namcontents.dumps())

        if self.promises:
            self.io_poll_sleep = 20
            self.io_poll_kwargs = dict(model='mfwam')
            self.flyput = True
        else:
            self.flyput = False

    def postfix(self, rh, opts):
        """Manually call the iopoll method to deal with the latest files."""
        if self.flyput:
            self.manual_flypolling_job()
        super(Mfwam, self).postfix(rh, opts)


class MfwamGauss2Grib(ParaBlindRun):
    """Post-processing of MFWAM output gribs."""

    _footprint = dict(
        info ="Post-processing of MFWAM output gribs",
        attr = dict(
            kind = dict(
                values  = ['mfwamgauss2grib'],
            ),
            fortinput = dict(
                optional = True,
                default = 'input',
            ),
            fortoutput = dict(
                optional = True,
                default = 'output',
            ),
            grid = dict(
                type = FPList,
                default = FPList(["glob02", ])
            ),
            refreshtime = dict(
                type = int,
                optional = True,
                default = 20,
            ),
            timeout = dict(
                type = int,
                optional = True,
                default = 600,
            ),
        )
    )

    def execute(self, rh, opts):
        """The algo component launchs a worker per output file."""
        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        common_i.update(dict(fortinput=self.fortinput, fortoutput=self.fortoutput))
        tmout = False

        # verification of the namelists
        for dom in self.grid:
            if not self.system.path.exists("./grids/" + dom + ".nam"):
                raise IOError("./grids/" + dom + ".nam must exist.")

        # Monitor for the input files
        bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                               role='GridParameters', kind='gridpoint')

        with bm:
            while not bm.all_done or len(bm.available) > 0:
                while bm.available:
                    gpsec = bm.pop_available().section
                    file_in = gpsec.rh.container.localpath()
                    self._add_instructions(common_i,
                                           dict(file_in=[file_in, ],
                                                grid=[self.grid, ],
                                                file_out=[file_in, ]))

                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ?
                    tmout = bm.is_timedout(self.timeout)
                if tmout:
                    break
                # Wait a little bit :-)
                time.sleep(1)
                bm.health_check(interval=30)

        self._default_post_execute(rh, opts)

        for failed_file in [e.section.rh.container.localpath() for e in six.itervalues(bm.failed)]:
            logger.error("We were unable to fetch the following file: %s", failed_file)
            if self.fatal:
                self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_file)),
                                           traceback=False)

        if tmout:
            raise IOError("The waiting loop timed out")


class _MfwamGauss2GribWorker(VortexWorkerBlindRun):
    """Worker of the post-processing for MFWAM."""

    _footprint = dict(
        info = "Worker of the post-processing for MFWAM",
        attr = dict(
            kind = dict(
                values  = ['mfwamgauss2grib'],
            ),
            fortinput = dict(),
            fortoutput = dict(),
            # Input/Output data
            file_in = dict(),
            grid = dict(
                type = FPList,
            ),
            file_out = dict(),
        )
    )

    def vortex_task(self, **kwargs):  # @UnusedVariable
        """Post-processing of a single output grib."""
        logger.info("Starting the post-processing")

        sh = self.system
        logger.info("Post-processing of %s", self.file_in)

        # Prepare the working directory
        cwd = sh.pwd()
        output_files = set()
        with sh.cdcontext(sh.path.join(cwd, self.file_in + '.process.d'), create=True):

            sh.softlink(sh.path.join(cwd, self.file_in), self.fortinput)
            for dom in self.grid:
                sh.title('domain : {:s}'.format(dom))
                # copy of namelist
                sh.cp(sh.path.join(cwd, "grids", dom + ".nam"), 'fort.2')
                # execution
                self.local_spawn("output.{:s}.log".format(dom))
                # copie output
                output_file = "reg{0:s}_{1:s}".format(self.file_out, dom)
                sh.mv(self.fortoutput, sh.path.join(cwd, output_file), fmt='grib')
                output_files.add(sh.path.join(cwd, output_file))

        # Deal with promised resources
        expected = [x for x in self.context.sequence.outputs()
                    if (x.rh.provider.expected and
                        x.rh.container.localpath() in output_files)]
        for thispromise in expected:
            thispromise.put(incache=True)
