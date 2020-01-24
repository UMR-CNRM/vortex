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
            assim = dict(
                type = bool,
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

        
        windcandidate = [x.rh for x in self.context.sequence.effective_inputs(role=re.compile('wind'),
                                                                              kind = 'gridpoint')]
        
        # Is there a analysis wind forcing ?                                                                      
        if len(windcandidate)==2:


            # Check for input grib files to concatenate
            for i, val in enumerate(windcandidate):
                if val.resource.origin in ['ana', 'analyse']:
                    gpsec1 = i
                elif val.resource.origin in ['fcst', 'forecast']:
                    gpsec2 = i

            # Check sfwindin
            tmpout='sfcwindin'
            if self.system.path.exists(tmpout):
                self.system.rm(tmpout)

            with open (tmpout,'w') as outfile:
                for fname in [x.container.localpath() for x in windcandidate]:
                    with open(fname) as infile:
                        outfile.write(infile.read())

            rhgrib = windcandidate[gpsec1]

            # recuperation fcterm
            if fcterm is None:
                fcterm = windcandidate[gpsec2].resource.term
                logger.info('fcterm %s', fcterm)

            datefin = (rhgrib.resource.date + fcterm + self.deltabegin).compact()
            datedebana = rhgrib.resource.date - self.anabegin + self.deltabegin
            datefinana = rhgrib.resource.date

        elif len(windcandidate)==1:
            rhgrib = windcandidate[0]

            if not self.system.path.exists('sfcwindin'):
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
        namcandidate = self.context.sequence.effective_inputs(role=('Namelist'),kind=('namelist'))

        if len(namcandidate)!=1:
            raise IOError("No or too much namelists for MFWAM")
        namcontents = namcandidate[0].rh.contents

        namcontents.setmacro('CBPLTDT', datedebana.compact())  # debut analyse
        namcontents.setmacro('CDATEF', datefinana.compact() )  # fin echeance analyse ici T0
        namcontents.setmacro('CEPLTDT', datefin)  # fin echeance prevision

        # sort altidata file
        # LFM: Pourquoi ajouter un switch de plus ? On regarde si il y a des obs en entrée :
        #      Si il y en a on fait de l'assimilatiob sinon c'est que ce n'est pas de l'assim
        # LFM: Et les autres types de données genre SAR. Pourquoi pas jouer sur
        # AD : je ne suis pas arrivée à récupérer la liste des effective_inputs ayant 
        # 'observation' pour rôle. Ma liste est toujours vide.
        if self.assim:
        # AD : par exemple la récupération ci-dessous d'altidata ne marche pas
        # le programme ne rentre pas dans la boucle
            for altisec in self.context.sequence.effective_inputs(sort='observation',kind = 'altidata'):
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
    
    def postfix(self,rh,opts):
        self.ticket.context.clear_promises()
        super(Mfwam,self).postfix(rh,opts)



class MfwamFilter(BlindRun):
    """ Filtering of altimeter data"""
    _footprint = dict(
        info = 'Filtering of altimeter data',
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
        #AD : J'ai vérifié et la tâche rentre 3 fois ici, mais ne traite qu'un sat à la fois
        # ce qui me va bien.
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

        # AD : j'ai temporairement commenté la vieille solution pour trier,
        # tant que le hook_sort ne marche pas dans la tâche. Je supprimerai après.
#        file_rejet = self.system.glob('rejet_*')
        filename_out_sorted = 'altidata'
        self.system.cp(filename_out,filename_out_sorted)
        # all the satellites have been filtered
#         if len(self.val_alti) == len(file_rejet):
#             logger.info("YAYA %s",self.val_alti)
#             # LFM: Idem. Du coup pas besoin d'ajouter sort dans l'objet system
#             self.system.sort('-k1', filename_out, output=filename_out_sorted)
#             if not self.system.path.exists(filename_out_sorted):
#                 raise IOError(filename_out_sorted + " must exists.")



class MfwamGauss2Grib(ParaBlindRun):
    """ Post-processing of MFWAM output gribs"""

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
        """ The algo component launchs a worker per output file """
        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        common_i.update(dict(fortinput=self.fortinput, fortoutput=self.fortoutput))
        tmout = False
        
        # verification of the namelists
        for dom in self.grid:
            if not self.system.path.exists(dom + ".nam"):
                raise IOError(dom + ".nam must exist.")
            
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


# LFM: file_exe supprimé -> normalement ne sert à rien !
#AD : j'ai remis file_exe pour citer le nom de l'exécutable lors de sa copie.
class _MfwamGauss2GribWorker(VortexWorkerBlindRun):
    """ Worker of the post-processing for MFWAM"""

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
            file_exe = dict(
                optional = True,
                default  = 'transfo_grib.exe',
            )
        )
    )

    def vortex_task(self, **kwargs):  # @UnusedVariable
        """Post-processing of a single output grib"""
        logger.info("Starting the post-processing")

        sh = self.system.sh
        logger.info("Post-processing of %s", self.file_in)

        # Prepare the working directory
        cwd = sh.pwd()
        output_files = set()
        with sh.cdcontext(sh.path.join(cwd, self.file_in + '.process.d'), create=True):

            sh.softlink(sh.path.join(cwd, self.file_in), self.fortinput)
            sh.cp(sh.path.join(cwd,self.file_exe),self.file_exe)

            for dom in self.grid:
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
