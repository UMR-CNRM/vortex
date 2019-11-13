#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from collections import defaultdict

import footprints
logger = footprints.loggers.getLogger(__name__)
from tnt.namadapter import BronxNamelistAdapter
import collections
import re, os, io
import glob
import copy
import time
import six

from vortex.algo.components import BlindRun, Parallel, ParaBlindRun
from common.algo.ifsroot import IFSParallel
from common.algo.eps import CombiPert
from vortex.tools import grib
from vortex.util.structs import ShellEncoder
from vortex.layout.dataflow import intent

from bronx.stdtypes.date import Time

#from vortex.tools.fortran import NamelistBlock
import vortex.util.structs
from common.tools.grib import GRIBFilter
from common.data.namelists import NamelistContent
from common.algo.stdpost import parallel_grib_filter, StandaloneGRIBFilter
from footprints.stdtypes import FPTuple
from taylorism import Boss
from taylorism.schedulers import MaxThreadsScheduler
from bronx.datagrip.namelist  import NamelistBlock, NamelistSet
from vortex.tools.parallelism import TaylorVortexWorker, VortexWorkerBlindRun, ParallelResultParser
from vortex.tools.systems     import ExecutionError
from vortex.layout.monitor    import BasicInputMonitor

  
class mfwam(Parallel, grib.EcGribDecoMixin):
    """."""
    _abstract = True
    _footprint = dict(
        attr = dict(
            list_guess = dict(
                type     = list,
                optional = True,
                default  = range(0,13,6),
            ),
            twowinds = dict(
                optional = True,
                type     = bool,
                default  = True,
            ),
            anabegin = dict(
                optional = True,
                default  = 6,
            ),
            currentbegin = dict(
                optional = True,
                default  = 6,
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
            fcterm = dict(
                type = int,
                optional = True,
            ),
            debretro = dict(
                type = bool,
                optional = True,
                default = True,
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
        super(mfwam, self).spawn_hook()
        if self.system.path.exists('fort.3'):
            self.system.subtitle('{0:s} : dump namelist <fort.3>'.format(self.realkind))
            self.system.cat('fort.3', output=False)

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(mfwam, self).prepare(rh, opts)
        ### setup MPI compatibilite
        self.env.update(
            I_MPI_COMPATIBILITY = 4,
        )

# Is there a analysis wind forcing ?
        if self.twowinds:
            # Check for input grib files to concatenate
            gpsec = [ x.rh for x in self.context.sequence.effective_inputs(role = re.compile('Gribin'),
                                                              kind = 'gridpoint') ]
            # Check for input grib files to concatenate
            for i, val in enumerate(gpsec):
                if val.resource.origin in ['ana', 'analyse']:
                    gpsec1 = i
                elif val.resource.origin in ['fcst', 'forecast']:
                    gpsec2 = i

            tmpout='sfcwindin'
            self.system.cp(gpsec[gpsec1].container.localpath(), tmpout, intent='inout', fmt='grib')
            self.system.cat(gpsec[gpsec2].container.localpath(), output=tmpout)
            rhgrib = gpsec[gpsec1]
            ## recuperation fcterm
            if self.fcterm:
                fcterm = self.fcterm
            else:
                fcterm = gpsec[gpsec2].resource.term
                logger.info('fcterm %s', fcterm)
            
             ## Tweak Namelist parameters
            namcandidate = self.context.sequence.effective_inputs(role=('Namelist'),kind=('namelist'))
            namcontents = namcandidate[0].rh.contents

            datefin = (rhgrib.resource.date + Time(fcterm)).compact()
            datedebana = rhgrib.resource.date - Time(self.anabegin)
            namcontents.setmacro('CBPLTDT', datedebana.compact()) # debut analyse 
            namcontents.setmacro('CDATEF', (rhgrib.resource.date).compact() ) # fin echeance analyse ici T0
            namcontents.setmacro('CEPLTDT', datefin)   # fin echeance prevision

        
        else:
            rhgrib=self.context.sequence.effective_inputs(role = re.compile('Gribin'),
                                                              kind = 'gridpoint')[0].rh
            self.system.cp(rhgrib.container.localpath(),'sfcwindin',intent='inout',fmt='grib')
            ## recuperation fcterm
            if self.fcterm:
                fcterm = self.fcterm
            else:
                fcterm = rhgrib.resource.term
                logger.info('fcterm %s', fcterm) 
            ## Tweak Namelist parameters
            namcandidate = self.context.sequence.effective_inputs(role=('Namelist'),kind=('namelist'))
            namcontents = namcandidate[0].rh.contents

            datefin = (rhgrib.resource.date + Time(fcterm)).compact()
            if self.debretro:
                datedebana = rhgrib.resource.date - Time(self.anabegin)
                datefinana = rhgrib.resource.date 
            else:
                datedebana = rhgrib.resource.date + Time(self.anabegin)
                datefinana = rhgrib.resource.date + Time(self.anabegin) 
            namcontents.setmacro('CBPLTDT', datedebana.compact()) # debut analyse 
            namcontents.setmacro('CDATEF', datefinana.compact() ) # fin echeance analyse ici T0
            namcontents.setmacro('CEPLTDT', datefin)   # fin echeance prevision
        

        ## sort altidata file
        if self.assim:
            for altisec in self.context.sequence.effective_inputs(role = re.compile('Altidata'),
                                                              kind = 'altidata'):

                r = altisec.rh
                paramct = r.contents
                paramct.sort()
                r.save()
                self.system.subtitle('{0:s} file sorted'.format(r.container.localpath()))
            namcontents.setmacro('IASSI',1)
        else:
            namcontents.setmacro('IASSI',0)


       
        if self.current_coupling: 
            namcontents.setmacro('CDATECURA', (datedebana - Time(self.currentbegin)).compact() )
            
        namcontents.setmacro('NUMOD', self.numod)

        if self.soce:
            namcontents.setmacro('SOCE', self.soce)

        for i in ['PATH', 'CPATH']:
          # namcontents.setmacro(i, namcandidate[0].rh.container.absdir) 
           namcontents.setmacro(i, '.')

        namcandidate[0].rh.save()

        tmpout = 'fort.3'
        ## Tweak Namelist guess dates
        dt = [ (rhgrib.resource.date + Time(x)).compact() for x in self.list_guess ]
        outstr0 = [ " &NAOS \n   CLSOUT='{0:s}', \n / \n".format(x) for x in dt ]
        outstr = ''.join(outstr0)
        
        filenam = open(tmpout, 'w')
        with filenam as nam:
            nam.write(outstr)   
        filenam.close()
                
        self.system.cat(namcandidate[0].rh.container.localpath(), output=tmpout, outmode='a')    
            
        if self.promises:
            self.io_poll_sleep = 20
            self.io_poll_kwargs = dict(model=rh.resource.model)
            self.flyput = True
        else:
            self.flyput = False

        logger.info("zorg")

class MfwamFilter(BlindRun):
  
    _footprint = dict(
        attr = dict( 
            kind = dict(
                values = ['MfwamAlti'],  
            ),
            val_alti = dict(
                default = 'jason2',
                type    = list,
            ),
        )
    )


    def postfix(self, rh, opts):
        """Set some variables according to target definition."""
        filename_out='obs_alti'
        if not os.path.exists(filename_out):
            raise IOError(filename_out + " must exists.")

        r_alti = [ x.rh for x in self.context.sequence.effective_inputs(role = re.compile('Altidata'),
                                                              kind = 'altidata') ]

        ultimate_alti = [ val.resource.satellite for i, val in enumerate(r_alti)
                             if val.resource.satellite not in self.val_alti ]
  
        ind = [ i for i, val in enumerate(r_alti)
                  if val.resource.satellite in ultimate_alti ]

        ## existence 3 fichier rejet* par satellite ??
        file_rejet = glob.glob('rejet_*')
        filename_out_sorted = 'altidata'
        if len(self.val_alti) == len(file_rejet):
            if ultimate_alti:  
                logger.info("new sat %s concat treatment", ultimate_alti)
                for ind0 in ind:
                    self.system.cat(r_alti[ind0].container.localpath(), output=filename_out, outmode='a')
            self.system.sort('-k1', filename_out,  output=filename_out_sorted) 
            if not os.path.exists(filename_out_sorted):
                raise IOError(filename_out_sorted + " must exists.")





class mfwamIMB(mfwam):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['MfwamImb'],
            ),
            soce = dict(
                type = int,
                optional = True,
                default = 70,
            ),
        )
    )

  
  ## liste des variables qui faudrait changer dans la namelist 
  ## numod, icourant
  
  
  

class MfwamGlob(mfwam):
    """"""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['MfwamGlob'],
            ),
#            gribcat = dict(
#                optional = True,
#                default = True,
#		 type = bool,
#            ),
            soce = dict(
                type = int,
                optional = True,
                default = 40,
            ),
        )
    )

    #@property
    #def nmod(self):
        #return 1

  ## liste des variables qui faudrait changer dans la namelist en DEV GLOB
  ## numod bouge pas c'est soche, icourant idelwo idelpro idelt IDELCUR 
  ## FFLAG 17e champ (True pour glocep01)
  ## specificite glocep01 derniere ligne rajouter pour lancement 2e job (NAOS CLSOUT="2018032100)
  

class MfwamGribingOp(BlindRun):
  
    _footprint = dict(
        attr = dict(
	    binary = dict(
	        values = ['mfwam'],
	    ),  
            kind = dict(
	        values = ['MfwamGribingOp'],  
	    ),
        )
    )


    def prepare(self, rh, opts):
        ### MPP -> M1 -> input
        gpsec = self.context.sequence.effective_inputs(role=('FilterGrib'))
        gpsec.sort(lambda a, b: cmp(a.rh.resource.term, b.rh.resource.term))
        
        for sec in gpsec:
            r = sec.rh
            print r
            t=Time(6)
            logger.info("ana term - %s", t)
	    logger.info("prv term max %s", r.resource.term)
	    datefin=(r.resource.date + r.resource.term).compact()
	    	    

    def postfix(self, rh, opts):
        """Set some variables according to target definition."""
        logger.info('coucou')
        ### output -> output_ech_(A/M)PP


        #outstr += 'XDELLA = {0:s}'.format(500)
        #outstr += 'TOTO = {0:s}'.format(500)
        #tmpout = 'fort.2'
        #filenam = open(tmpout, 'w')
        #with filenam as nam:
           #nam.write(outstr)   
        #filenam.close()

        #self.system.cat(namcandidate[0].rh.container.localpath(), output=tmpout, outmode='a')    






   
class MfwamPosDEB(VortexWorkerBlindRun, grib.EcGribDecoMixin):
  
    _footprint = dict(
        attr = dict(
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = True
            ),
        )
    )
	    
    def __init__(self, *kargs, **kwargs):
        super(MfwamPosDEB, self).__init__(*kargs, **kwargs)
        

    #def prepare(self, rh, opts):
        #"""Set some variables according to target definition."""
        #super(MfwamPos, self).prepare(rh, opts)


        #for x in self.context.sequence.effective_inputs(role = re.compile('master'),
                                                              #kind = 'MasterMFWAM'):

            #r = x.rh
            #logger.info("grille ?? %s", r.option["grille"])


         ### faire un lien sur chaque grib lien input


    def vortex_task(self, **kwargs):

        logger.info("Starting the Grib processing for tag=%s", self.name)

        thisoutput = 'GRIDOUTPUT'
        rdict = dict(rc=True)

        ## First, check that the hooks were applied
        for thisinput in [x for x in self.context.sequence.inputs()
                          if x.rh.container.localpath() == self.file_in]:
            if thisinput.rh.delayhooks:
                thisinput.rh.apply_get_hooks()

        ## Jump into a working directory
        cwd = self.system.pwd()
        tmpwd = self.system.path.join(cwd, self.file_out + '.process.d')
        self.system.mkdir(tmpwd)
        self.system.cd(tmpwd)


        self.system.softlink(self.system.path.join(cwd, self.file_in),
                             self.fortinput)

        ## Standard execution

        if self.system.path.exists(self.file_out):
            # Deal with promised resources
            expected = [x for x in self.context.sequence.outputs()
                        if x.rh.provider.expected and x.rh.container.localpath() == self.file_out]
            for thispromise in expected:
                thispromise.put(incache=True)



    def find_namelists(self, opts=None):
        """Find any namelists candidates in actual context inputs."""
        namcandidates = [x.rh for x in self.context.sequence.effective_inputs(kind='namelist')]
        self.system.subtitle('Namelist candidates')
        for nam in namcandidates:
            nam.quickview()

        return namcandidates




     ### ## Tweak Namelist guess dates
     
        #namcandidate = self.context.sequence.effective_inputs(role=('Namelist'),kind=('namelist'))
        #self.system.subtitle('Namelist candidate')
        #namcandidate[0].rh.quickview()
        #namcontents = namcandidate[0].rh.contents


        #namcontents.setmacro('IDELLA',) 
        #namcontents.setmacro('ISOUTH',) 
        #namcontents.setmacro('INORTH',)  
        #namcontents.setmacro('IEAST',)
        #namcontents.setmacro('IWEST',)       
     



    #def postfix(self, rh, opts):
        #"""Set some variables according to target definition."""



class MFwawwwwwwwwww(MfwamPosDEB):
  
    _footprint = dict(
            kind = dict(
                values = ['MfwamPost'],  
            ),
    )




class TaylorMfwamProcess(ParaBlindRun):
  
    _abstract = True

    def prepare(self, rh, opts):
        """Mostly used for setting environment."""
        super(TaylorMfwamProcess, self).prepare(rh, opts)
        self.export('gribex')
        self.export('bufr')
  
class MfwamGauss2Gribpara(TaylorMfwamProcess):
    """."""


    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['mfwamgauss2gribpara'],
            ),
            fortinput = dict(
                optional = True,
                default = 'input',
            ),
            verbose = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            ntasks = dict(
                info     = ("The maximum number of allowed concurrent task for "
                            "parallel execution."),
                default  = 7,
                optional = True,
            ),
        )
    )


    def _default_pre_execute(self, rh, opts):
        '''Change default initialisation to use LongerFirstScheduler'''
        # Start the task scheduler
        self._boss = Boss(verbose=self.verbose,
                          scheduler=footprints.proxy.scheduler(limit='threads',
                                                               max_threads=self.ntasks,
                                                               ))
        logger.info('coucou')
        self._boss.make_them_work()



    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        gpsec = self.context.sequence.effective_inputs(role=('GridParameters'))
        gpsec.sort(key=lambda s: s.rh.resource.term)
        logger.info("gpsec %s", gpsec)

        scheduler_instructions = defaultdict(list)
        sh = self.system.sh
        workdir = sh.pwd()
        thisoutput = 'output'

        for sec in gpsec:
            r = sec.rh

            with sh.cdcontext('wkdir_' + r.container.localpath(), create=True):

               logger.info('creating softlink: %s -> %s', r.container.localpath(),
                                    sh.path.join(workdir, r.container.localpath()))
               sh.softlink(sh.path.join(workdir, r.container.localpath()),
                                    r.container.localpath())

               logger.info('creating softlink: %s -> %s', 'main_post',
                                    sh.path.join(workdir, 'main_post'))
               sh.softlink(sh.path.join(workdir, 'main_post'),
                                    'main_post')


               self.system.title('Loop on files: {:s}'.format(r.container.localpath()))

               # Some preventive cleaning
               self.system.remove(thisoutput)
               self.system.remove('fort.2')

               # Build the local namelist block
               nb = NamelistBlock(name='NALINE')
               nb.IDELLA = 500
               nb['ISOUTH'] = -89500
               nb['INORTH'] = 89500
               nb['IWEST'] = 0
               nb['IEAST'] = 359500
               with io.open('fort.2', 'w') as namfd:
                   namfd.write(nb.dumps())

               self.system.header('{0:s} : local namelist {1:s} dump'.format(self.realkind, 'fort.2'))
               self.system.cat('fort.2', output=False)

               # Expect the input FP file source to be there...
             #  self.grab(sec, comment='fullpos source')

               # Finaly set the actual init file
               self.system.softlink(r.container.localpath(), self.fortinput)
               scheduler_instructions['name'].append('wkdir_{:s}'.format(r.container.localpath()))
               scheduler_instructions['progname'].append(sh.path.join(workdir, 'wkdir_' + r.container.localpath(),'main_post'))
               scheduler_instructions['base'].append(r.container.localpath())
               scheduler_instructions['memory'].append('1000')
               scheduler_instructions['expected_time'].append('100')
               scheduler_instructions['subdir'].append('wkdir_' + r.container.localpath())
               scheduler_instructions['progtaskset'].append('raw')

               # Freeze the current output
               logger.info('output cree %s',sh.path.join(workdir, 'wkdir_' + r.container.localpath(),'output'))
               if self.system.path.exists(sh.path.join(workdir, 'wkdir_' + r.container.localpath(),'output')):
                   logger.info('output cree %s',sh.path.join(workdir, 'wkdir_' + r.container.localpath(),'output'))
                   self.system.cp(thisoutput, '../regular_' + r.container.localpath(), fmt = r.container.actualfmt)
               else:
                   logger.warning('Missing some grib output for %s',
                               thisoutput)

               ## Some cleaning
               #self.system.rmall(self.fortinput)


        sh.title('Launching Transfo using taylorism...')
        self._default_pre_execute(rh, opts)
        common_i = self._default_common_instruction
        logger.info("common_i %s", common_i)
        # Update the common instructions
        common_i.update(dict(workdir=workdir, ))


        self._add_instructions(common_i, scheduler_instructions)
        logger.info('scheduler_instruction %s', scheduler_instructions)
        print('Intermediate report:', self._boss.get_report())
        self._boss.wait_till_finished()
        report = self._boss.get_report()
        for r in report['workers_report']:
            print(r)

  
class MfwamGauss2Grib2(ParaBlindRun):
    """."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['mfwamgauss2grib2'],
            ),
            fortinput = dict(
                optional = True,
                default = 'input',
            ),
            grille = dict(
                type     = list,
                default = "glob02",
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
            flyargs = dict(
                default = ('regMPP', 'regAPP',),
            ),
            flypoll = dict(
                default = 'iopoll_marine',
            ),
        )
    )


    def prepare(self, rh, opts):

        if self.promises:
            self.io_poll_sleep = 20
            self.io_poll_kwargs = dict(model=rh.resource.model)
            self.flyput = True
        else:
            self.flyput = False


    def execute(self, rh, opts):
        """"""
        gpexe = self.context.sequence.effective_inputs(role=('master'))
        logger.info("gpexe %s", gpexe)
        rhexe = gpexe[1].rh
        logger.info("yo %s",rhexe.container.localpath())
        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        # Update the common instructions
#        common_i.update(dict(fortinput=45))

        sh = self.system.sh
        thisoutput = 'output'
        tmout=False

        # Monitor for the input files
        bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                               role='GridParameters', kind='gridpoint')
        
        with bm:
            while not bm.all_done or len(bm.available) > 0:
                while bm.available:
                    gpsec = bm.pop_available().section
                    r = gpsec.rh
                    file_in=r.container.localpath()
                    self._add_instructions(common_i,dict(file_in=[file_in,]))
                        
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
                self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_file)),traceback=False)

        if tmout:
            raise IOError("The waiting loop timed out")
 
class _MfwamGauss2GribWorker(VortexWorkerBlindRun):
    """."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values  = ['mfwamgauss2grib2'],
            ),
            fortinput = dict(
                optional = True,
                default = 'input',
            ),
            # Input/Output data
            file_in = dict(),
#            file_out = dict(),
#            member = dict(
#                type = FmtInt,
#                optional = True,
#            )
        )
    )


    def vortex_task(self, **kwargs):
        """"""
        logger.info("Starting the post-processing")

        sh = self.system.sh
        thisoutput = 'output'
        logger.info("num : %d", self.num)
        logger.info("la difference : %s",self.file_in)
        
        #Prepare the working directory
        cwd=sh.pwd()
        tmpwd=sh.path.join(cwd,self.file_in+'.process.d')
        sh.mkdir(tmpwd)
        sh.softlink(sh.path.join(cwd,self.file_in),sh.path.joint(tmpwd,self.fortinput))
#        sh.cp(sh.path.join(cwd,self.file_in),sh.path.join(tmpwd,self.file_in))
        sh.cd(tmpwd)
        time.sleep(30)
        


#        for dom in self.grille:
#                        self.system.title('domain : {:s}'.format(dom))
        
#                        self.system.cp(dom+".nam",'fort.2')

                        
#                        r = gpsec.rh

                        # Some preventive cleaning
#                        self.system.remove(self.fortinput)
#                        self.system.remove(thisoutput)

#                        self.system.title('Loop on files: {:s}'.format(r.container.localpath()))
#                        self.system.softlink(r.container.localpath(), self.fortinput)


#                        super(MfwamGauss2Grib, self).execute(rh, opts)

                        ### copie output
#                        self.system.cp(thisoutput, "reg{0:s}_{1:s}".format(r.container.localpath(),dom), fmt = 'grib')
                        

        
        

class MfwamGauss2Grib(BlindRun):
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
            grille = dict(
                type     = list,
                default = "glob02",
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
            flyargs = dict(
                default = ('regMPP', 'regAPP',),
            ),
            flypoll = dict(
                default = 'iopoll_marine',
            ),
        )
    )


    def prepare(self, rh, opts):

        if self.promises:
            self.io_poll_sleep = 20
            self.io_poll_kwargs = dict(model=rh.resource.model)
            self.flyput = True
        else:
            self.flyput = False


    def execute(self, rh, opts):
        """"""
#        gpsec = self.context.sequence.effective_inputs(role=('GridParameters'))
#        gpsec.sort(key=lambda s: s.rh.resource.term)
#        logger.info("gpsec %s", gpsec)

        sh = self.system.sh
        thisoutput = 'output'
        tmout=False

        # Monitor for the input files
        bm = BasicInputMonitor(self.context, caching_freq=self.refreshtime,
                               role='GridParameters', kind='gridpoint')
        
        with bm:
            while not bm.all_done or len(bm.available) > 0:
                while bm.available:
                    gpsec = bm.pop_available().section
                    for dom in self.grille:
                        self.system.title('domain : {:s}'.format(dom))
        
                        self.system.cp(dom+".nam",'fort.2')

                        
                        r = gpsec.rh

                        # Some preventive cleaning
                        self.system.remove(self.fortinput)
                        self.system.remove(thisoutput)

                        self.system.title('Loop on files: {:s}'.format(r.container.localpath()))
                        self.system.softlink(r.container.localpath(), self.fortinput)


                        super(MfwamGauss2Grib, self).execute(rh, opts)

                        ### copie output
                        self.system.cp(thisoutput, "reg{0:s}_{1:s}".format(r.container.localpath(),dom), fmt = 'grib')
                        
                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ?
                    tmout = bm.is_timedout(self.timeout)
                if tmout:
                    break
                # Wait a little bit :-)
                time.sleep(1)
                bm.health_check(interval=30)            

        for failed_file in [e.section.rh.container.localpath() for e in six.itervalues(bm.failed)]:
            logger.error("We were unable to fetch the following file: %s", failed_file)
            if self.fatal:
                self.delayed_exception_add(IOError("Unable to fetch {:s}".format(failed_file)),traceback=False)

        if tmout:
            raise IOError("The waiting loop timed out")




