#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import six

#: No automatic export
__all__ = []

import io
import re
import time

from bronx.datagrip import namelist as bnamelist
from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Time, Period
from footprints.stdtypes import FPList

from vortex.algo.components import BlindRun, Parallel, ParaBlindRun
from vortex.tools import grib

from vortex.tools.parallelism import VortexWorkerBlindRun
from vortex.layout.monitor import BasicInputMonitor

logger = loggers.getLogger(__name__)


# LFM: docstring + info ?
# LFM: date_cura ne sert a rien -> virer ?
class Mfwam(Parallel, grib.EcGribDecoMixin):
    """."""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['MFWAM'],
            ),
            list_guess = dict(
                type     = FPList,
                optional = True,
                default  = list(range(0, 13, 6)),
            ),
            twowinds = dict(
                optional = True,
                type     = bool,
                default  = True,
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
            assim = dict(
                type = bool,
                optional = True,
                default = False,
            ),
            date_cura = dict(
                optional = True,
                default = False,
            ),
            flyargs = dict(
                default = ('MPP', 'APP',),
            ),
            flypoll = dict(
                default = 'iopoll_marine',
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
            I_MPI_COMPATIBILITY = 4,
        )

        fcterm = self.fcterm

        # Is there a analysis wind forcing ?
        # LFM: Y a t'il vraiement besoin de ce truc. Pourquoi ne pas le detecter
        #      en regardant quels sont les gribs présents.
        # LFM: Pourrait il y en avoir plus que deux ? Ne vaudrait il pas mieux en
        #      traiter un ou plus (en les triant par date de validité par exemple) ?
        windcandidate = [x.rh for x in self.context.sequence.effective_inputs(role=re.compile('wind'),
                                                                              kind = 'gridpoint')]
        if len(windcandidate)==2:
#        if self.twowinds:
            # Check for input grib files to concatenate
            # LFM: Mauvais usage du role. role = Forcing ? WindForcing ?
            gpsec = [ x.rh for x in self.context.sequence.effective_inputs(role = re.compile('wind'),
                                                                           kind = 'gridpoint') ]
            # LFM: Et si il y a plus de deux gribs en entrée ???
            # Check for input grib files to concatenate
            for i, val in enumerate(gpsec):
                if val.resource.origin in ['ana', 'analyse']:
                    gpsec1 = i
                elif val.resource.origin in ['fcst', 'forecast']:
                    gpsec2 = i

            # LFM: Si sfcwindin existe déjà, on fait quoi ?
            # Privilégier l'usage de python et non self.system
            tmpout = 'sfcwindin'
            self.system.cp(gpsec[gpsec1].container.localpath(), tmpout, intent='inout', fmt='grib')
            self.system.cat(gpsec[gpsec2].container.localpath(), output=tmpout)
            rhgrib = gpsec[gpsec1]

            # recuperation fcterm
            if fcterm is None:
                fcterm = gpsec[gpsec2].resource.term
                logger.info('fcterm %s', fcterm)

            datefin = (rhgrib.resource.date + fcterm + self.deltabegin).compact()
            datedebana = rhgrib.resource.date - self.anabegin + self.deltabegin
            datefinana = rhgrib.resource.date

        elif len(windcandidate)==1:
            rhgrib = self.context.sequence.effective_inputs(role = re.compile('wind'),
                                                            kind = 'gridpoint')[0].rh
            # LFM: Et si il y a plusieurs gribs en entrée ???
            # LFM: Si sfcwindin existe déjà, on fait quoi ?
            self.system.cp(rhgrib.container.localpath(), 'sfcwindin', intent='in', fmt='grib')

            # recuperation fcterm
            if fcterm is None:
                fcterm = rhgrib.resource.term
                logger.info('fcterm %s', fcterm)

            datefin = (rhgrib.resource.date + fcterm + self.deltabegin).compact()
            datedebana = rhgrib.resource.date - self.anabegin + self.deltabegin
            if self.isana:
                datefinana = rhgrib.resource.date
            else:
                datefinana = datedebana
        else:
            raise ValueError("No winds or too much")

        # Tweak Namelist parameters
        namcandidate = self.context.sequence.effective_inputs(role=('Namelist'), kind=('namelist'))
        # LFM: Et si il y a plusieurs namelists. Faire une verification ?
        namcontents = namcandidate[0].rh.contents

        namcontents.setmacro('CBPLTDT', datedebana.compact())  # debut analyse
        namcontents.setmacro('CDATEF', datefinana.compact() )  # fin echeance analyse ici T0
        namcontents.setmacro('CEPLTDT', datefin)  # fin echeance prevision

        # sort altidata file
        # LFM: Quelle est la subtile différence entre isana et assim ?
        # LFM: Pourquoi ajouter un switch de plus ? On regarde si il y a des obs en entrée :
        #      Si il y en a on fait de l'assimilatiob sinon c'est que ce n'est pas de l'assim
        # LFM: Et les autres types de données genre SAR. Pourquoi pas jouer sur
        #      le role avec un truc à peu près claire du genre Observations ?
        if self.assim:
            for altisec in self.context.sequence.effective_inputs(kind = 'altidata'):

                r = altisec.rh
                r.contents.sort()
                r.save()
                self.system.subtitle('{0:s} file sorted'.format(r.container.localpath()))
            namcontents.setmacro('IASSI', 1)
        else:
            namcontents.setmacro('IASSI', 0)

        if self.current_coupling:
            namcontents.setmacro('CDATECURA', (datedebana - self.currentbegin).compact())

        namcontents.setmacro('NUMOD', self.numod)

        if self.soce:
            namcontents.setmacro('SOCE', self.soce)

        for i in ['PATH', 'CPATH']:
            namcontents.setmacro(i, '.')

        namcandidate[0].rh.save()

        # Tweak Namelist guess dates
 
        dt = [ (rhgrib.resource.date + Time(x)).compact() for x in self.list_guess ]
        outstr0 = [ " &NAOS \n   CLSOUT='{0:s}', \n / \n".format(x) for x in dt ]
        outstr = ''.join(outstr0)
        with io.open('fort.3','w') as fhnam:
            fhnam.write(outstr)

        self.system.cat(namcandidate[0].rh.container.localpath(), output='fort.3', outmode='a')

        if self.promises:
            self.io_poll_sleep = 20
            self.io_poll_kwargs = dict(model='mfwam')
            self.flyput = True
        else:
            self.flyput = False


# LFM: Docstring + info ?
class MfwamFilter(BlindRun):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['MfwamAlti'],
            ),
            begindate = dict(
                type     = Date,
            ),
            enddate = dict(
                type     = Date,
            ),
            val_alti = dict(
                default = ['jason2'],
                type    = FPList,
            ),
        )
    )

    def spawn_command_options(self):
        """Dictionary provided for command line factory."""
        return dict(
            begindate=self.begindate,
            enddate=self.enddate,
        )

    def postfix(self, rh, opts):
        """Set some variables according to target definition."""
        super(MfwamFilter, self).postfix(rh, opts)
        filename_out = 'obs_alti'
        if not self.system.path.exists(filename_out):
            raise IOError(filename_out + " must exists.")

        r_alti = [ x.rh for x in self.context.sequence.effective_inputs(role = re.compile('Altidata'),
                                                                        kind = 'altidata') ]

        rh.resource.satellite

        ultimate_alti = [ val.resource.satellite for val in r_alti
                          if val.resource.satellite not in self.val_alti ]

        ind = [ i for i, val in enumerate(r_alti)
                if val.resource.satellite in ultimate_alti ]

        # existence 3 fichier rejet* par satellite ??
        file_rejet = self.system.glob('rejet_*')
        filename_out_sorted = 'altidata'
        if len(self.val_alti) == len(file_rejet):
            if ultimate_alti:
                logger.info("new sat %s concat treatment", ultimate_alti)
                # LFM: le faire directement en python, eviter l'appel systeme
                for ind0 in ind:
                    self.system.cat(r_alti[ind0].container.localpath(), output=filename_out, outmode='a')
            # LFM: Idem. Du coup pas besoin d'ajouter sort dans l'objet system
            self.system.sort('-k1', filename_out, output=filename_out_sorted)
            if not self.system.path.exists(filename_out_sorted):
                raise IOError(filename_out_sorted + " must exists.")


# LFM: docstring + info ?
# LFM: grille -> grid
class MfwamGauss2Grib(ParaBlindRun):
    """."""

    _footprint = dict(
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
            grille = dict(
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


    # LFM: docstring
    def execute(self, rh, opts):
        """"""
        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        common_i.update(dict(fortinput=self.fortinput, fortoutput=self.fortoutput))
        tmout = False

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
                                                grille=[self.grille, ],
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


# LFM: docstring
# LFM: grille -> grid ?
# LFM: file_exe supprimé -> normalement ne sert à rien !
# LFM: On fait le présuposé que "../" + dom + ".nam" existe : il faudrait au moins le vérifier
#      dans l'algocomponent
#AD : j'ai remis file_exe pour citer le nom de l'exécutable lors de sa copie.
class _MfwamGauss2GribWorker(VortexWorkerBlindRun):
    """."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['mfwamgauss2grib'],
            ),
            fortinput = dict(),
            fortoutput = dict(),
            # Input/Output data
            file_in = dict(),
            grille = dict(
                type = FPList,
            ),
            file_out = dict(),
            file_exe = dict(
                optional = True,
                default  = 'transfo_grib.exe',
            )
        )
    )

    # LFM: docstring
    def vortex_task(self, **kwargs):  # @UnusedVariable
        """"""
        logger.info("Starting the post-processing")

        sh = self.system.sh
        logger.info("Post-processing of %s", self.file_in)

        # Prepare the working directory
        cwd = sh.pwd()
        output_files = set()
        with sh.cdcontext(sh.path.join(cwd, self.file_in + '.process.d'), create=True):

            sh.softlink(sh.path.join(cwd, self.file_in), self.fortinput)
            sh.cp(sh.path.join(cwd,self.file_exe),self.file_exe)

            for dom in self.grille:
                sh.title('domain : {:s}'.format(dom))
                # copy of namelist
                sh.cp(sh.path.join(cwd, dom + ".nam"), 'fort.2')
                # execution
                self.local_spawn("output.{:s}.log".format(dom))
                # copie output
                output_file = "reg{0:s}_{1:s}".format(self.file_out, dom)
                sh.mv(self.fortoutput, sh.path.join(cwd, output_file), fmt = 'grib')
                output_files.add(sh.path.join(cwd,output_file))

        # Deal with promised resources
        expected = [x for x in self.context.sequence.outputs()
                    if (x.rh.provider.expected and
                        x.rh.container.localpath() in output_files)]
        for thispromise in expected:
            thispromise.put(incache=True)
