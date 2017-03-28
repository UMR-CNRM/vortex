#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

#: No automatic export
__all__ = []

import sys, os
import traceback
import shlex
import multiprocessing

from taylorism import Boss
from taylorism.schedulers import MaxThreadsScheduler
import footprints
logger = footprints.loggers.getLogger(__name__)

import vortex
from vortex.algo  import mpitools
from vortex.tools.date import Date
from vortex.syntax.stdattrs import a_date, term
from vortex.tools.parallelism import ParallelResultParser
from vortex.syntax.stdattrs import DelayedEnvValue
from vortex.algo.components import ExecutableAlgoComponent, ParaBlindRun, TaylorRun
from vortex.tools.parallelism import VortexWorkerBlindRun
from vortex.layout.monitor    import BasicInputMonitor
from vortex.syntax.stdattrs import FmtInt
from vortex.tools.systems import ExecutionError
from vortex.algo.components import AlgoComponentError
from vortex.util.helpers import InputCheckerError

_OP_files_common = dict(alp=['OPlisteo', 'OPlistem', 'OPlisteml', 'OPclim'], 
                 pyr=['OPlysteo', 'OPlystem', 'OPlysteml', 'OPclim'],)
_OP_files_individual = ['OPguess', 'OPprevi', 'OPMET', 'OPSA', 'OPSAP', 'OPSAN']


class Pearp2SafranWorker(VortexWorkerBlindRun):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'pearp2safran' ],
            ),
            member =  dict(
                type = FmtInt,
            ),
            interpreter = dict(
                info   = 'The interpreter needed to run the script.',
                values = ['awk', 'ksh', 'bash', 'perl', 'python']
            ),
        )
    )

    def spawn(self, args):
        """
        Spawn in the current system the command as defined in raw ``args``.

        The followings environment variables could drive part of the execution:

          * VORTEX_DEBUG_ENV : dump current environment before spawn
        """
        sh = self.system

        sh.subtitle('{0:s} : directory listing (pre-execution)'.format(self.realkind))
        sh.remove('core')
        sh.softlink('/dev/null', 'core')
        sh.dir(output=False, fatal=False)
        sh.subtitle('{0:s} : start execution'.format(self.realkind))
        sh.spawn(args, output=False, fatal=True)


    def vortex_task(self, **kw):
        self._status = True

        # Get instance shorcuts to context and system objects
        t = vortex.sessions.current()
        self.context = t.context
        self.system  = self.context.system
        self.target  = kw.pop('target', None)
        if self.target is None:
            self.target = self.system.target()
       
        self.rundir = t.sh.getcwd()
        member = self.member
        if not os.path.exists('mb{0:03d}'.format(member)):
            t.sh.mkdir('mb{0:03d}'.format(member))
        t.sh.cd('mb{0:03d}'.format(member))
 
        executable = self.progname.split('/')[-1]
        if not os.path.islink(executable):
            t.sh.symlink('../' + executable, executable)

        args = [self.interpreter, executable]
        args.extend(self.progargs)
        logger.debug('Run script %s', args)
        self.spawn(args)


class SafranWorker(VortexWorkerBlindRun):

    _abstract  = True
    _footprint = dict(
        attr = dict(
            date = a_date,
            member =  dict(
                type = FmtInt,
            ),
            terms = dict(
                type        = footprints.FPList,
            ),
            vconf = dict(),
        )
    )

    def terms_manager(self, date, terms=list()):
        """Guess the number of days that are to be covered by the forecast"""
        
        days = dict()

        first_term = (i for i,v in enumerate(terms) if Date('{0:s}/+PT{1:s}H'.format(date.ymdh, str(v))).hh=='06').next()
        new_terms = terms[first_term:] # Start simulation at first 06h term
        i = 0
        while i < len(new_terms)/4:
            days[i+1] = new_terms[4*i:4*(i+1)+1] # Safran needs 5 terms per day, with a term common beetwen two consecutive days
            i += 1

        if days == dict():
            logger.warning('No terms to process, doing nothing.')

        return days


    def vortex_task(self, **kw):
        self._status = True

        # Get instance shorcuts to context and system objects
        t = vortex.sessions.current()
        self.context = t.context
        self.system  = self.context.system
        self.target  = kw.pop('target', None)
        if self.target is None:
            self.target = self.system.target()

        self.days = self.terms_manager(self.date, self.terms) 

        self.rundir = t.sh.getcwd()
        member = self.member
        if not os.path.exists('mb{0:03d}'.format(member)):
            t.sh.mkdir('mb{0:03d}'.format(member))
        t.sh.cd('mb{0:03d}'.format(member))

        executable = self.progname.split('/')[-1]
        if not os.path.islink(executable):
            t.sh.symlink('../' + executable, executable)


class SafraneWorker(SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['safrane']
            ),
        )
    )

    def vortex_task(self, **kw):
        super(SafraneWorker, self).vortex_task(**kw)
    
        t = vortex.sessions.current()
        member = self.member       
        rdict = dict(rc=True)
        thisdir = t.sh.getcwd()

        # Generate the 'OPxxxxx' files containing links for the safran execution.
        for op_file in _OP_files_common[self.vconf]:
            with open(op_file, 'w') as f:
                f.write(self.rundir + '@')

        for op_file in _OP_files_individual:
            with open(op_file, 'w') as f:
                f.write(thisdir + '@')
 
        for term in self.terms:
            t.sh.subtitle('Running term : {0:s}'.format(str(term)))

            # Creation of the 'sapdat' file containing the exact date of the file to be processed.
            startdate = Date('{0:s}/+PT{1:s}H'.format(self.date.ymdh, str(term)))
            year  = startdate.strftime('%y')
            month = startdate.strftime('%m')
            day   = startdate.strftime('%d')
            hour  = startdate.hh
            sapdat = 'sapdat'
            if os.path.isfile(sapdat):
                os.remove(sapdat)
            with open(sapdat, 'w') as d:
                d.write('{},{},{},{}\n'.format(year, month, day, hour))
                d.write('0,0,0\n')
                d.write('3,1,3,3\n')
                d.write('0\n')
                d.write('1,1,0,0,1\n')

            # Création of the 'sapfich' file containing the name of the output file
            with open('sapfich', 'w') as f:
                f.write('SAF' + str(term))

            list_name = self.system.path.join(thisdir, 'listsaf' + str(term))
            try:
                self.local_spawn(list_name)
            except ExecutionError as e:
                rdict['rc'] = e

        t.sh.cd(self.rundir)
        self.system = None

        return rdict

class SyrpluieWorker(SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syrpluie']
            ),
        )
    )


    def vortex_task(self, **kw):
        super(SyrpluieWorker, self).vortex_task(**kw)

        t = vortex.sessions.current()
        member = self.member
        rdict = dict(rc=True)
        thisdir = t.sh.getcwd()

        # Generate the 'OPxxxxx' files containing links for the safran execution.
        for op_file in _OP_files_common[self.vconf]:
            with open(op_file, 'w') as f:
                f.write(self.rundir + '@')

        for op_file in _OP_files_individual:
            with open(op_file, 'w') as f:
                f.write(thisdir + '@')

        if os.path.isfile('sapfich'):
            os.remove('sapfich')

        for ech in self.days: 
            t.sh.subtitle('Running term : {0:s}'.format(str(term)))

            lastech = Date('{0:s}/+PT{1:s}H'.format(self.date.ymdh, str(self.days[ech][-1])))
            year  = lastech.strftime('%y')
            month = lastech.strftime('%m')
            day   = lastech.strftime('%d')
            hour  = lastech.hh
            sapdat = 'sapdat'
            if os.path.isfile(sapdat):
                os.remove(sapdat)
            with open(sapdat, 'w') as d:
                d.write('{},{},{},{}\n'.format(year, month, day, hour))
                d.write('0,0,0\n')
                d.write('3,1,3,3\n')
                d.write('0\n')
                d.write('1,1,0,0,1\n')

            list_name = self.system.path.join(thisdir, 'listpluie' + str(ech))
            try:
                self.local_spawn(list_name)
            except ExecutionError as e:
                rdict['rc'] = e
            
            if os.path.isfile('fort.21'):
                t.sh.mv('fort.21', 'SAPLUI5' + str(ech))

        t.sh.cd(self.rundir)
        self.system = None

        return rdict


class SyrmrrWorker(SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['syrmrr']
            ),
        )
    )


    def vortex_task(self, **kw):
        super(SyrmrrWorker, self).vortex_task(**kw)

        t = vortex.sessions.current()
        member = self.member
        rdict = dict(rc=True)
        thisdir = t.sh.getcwd()

        # Generate the 'OPxxxxx' files containing links for the safran execution.
        for op_file in _OP_files_common[self.vconf]:
            with open(op_file, 'w') as f:
                f.write(self.rundir + '@')

        for op_file in _OP_files_individual:
            with open(op_file, 'w') as f:
                f.write(thisdir + '@')
       
        if os.path.isfile('sapfich'):
            os.remove('sapfich')

        for ech in self.days: 

            t.sh.subtitle('Running term : {0:s}'.format(str(term)))

            if os.path.isfile('SAPLUI5' + str(ech)):
                t.sh.cp('SAPLUI5' + str(ech), 'fort.11')
                t.sh.cp('SAPLUI5' + str(ech), 'fort.12')
            else:
                rdict['rc'] = InputCheckerError("Some of the mandatory flow resources are missing.")

            lastech = Date('{0:s}/+PT{1:s}H'.format(self.date.ymdh, str(self.days[ech][-1])))
            year  = lastech.strftime('%y')
            month = lastech.strftime('%m')
            day   = lastech.strftime('%d')
            hour  = lastech.hh
            sapdat = 'sapdat'
            if os.path.isfile(sapdat):
                os.remove(sapdat)
            with open(sapdat, 'w') as d:
                d.write('{},{},{},{}\n'.format(year, month, day, hour))
                d.write('0,0,0\n')
                d.write('3,1,3,3\n')
                d.write('0\n')
                d.write('1,1,0,0,1\n')


            list_name = self.system.path.join(t.sh.getcwd(), 'listrr' + str(ech))
            try:
                self.local_spawn(list_name)
            except ExecutionError as e:
                rdict['rc'] = e

            if os.path.isfile('fort.13'):
                t.sh.mv('fort.13', 'SAPLUI5' + str(ech))

            if os.path.isfile('fort.14'):
                t.sh.mv('fort.14', 'SAPLUI5_ARP' + str(ech))

            if os.path.isfile('fort.15'):
                t.sh.mv('fort.15', 'SAPLUI5_ANA' + str(ech))


        t.sh.cd(self.rundir)
        self.system = None

        return rdict


class SytistWorker(SafranWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['sytist']
            ),
        )
    )


    def vortex_task(self, **kw):
        super(SytistWorker, self).vortex_task(**kw)

        t = vortex.sessions.current()
        member = self.member
        rdict = dict(rc=True)
        thisdir = t.sh.getcwd()

        # Generate the 'OPxxxxx' files containing links for the safran execution.
        for op_file in _OP_files_common[self.vconf]:
            with open(op_file, 'w') as f:
                f.write(self.rundir + '@')

        for op_file in _OP_files_individual:
            with open(op_file, 'w') as f:
                f.write(thisdir + '@')
       
        if os.path.isfile('sapfich'):
            os.remove('sapfich')

        for ech in self.days: 

            t.sh.subtitle('Running term : {0:s}'.format(str(term)))

            if os.path.isfile('SAPLUI5' + str(ech)):
                t.sh.cp('SAPLUI5' + str(ech), 'SAPLUI5')
            else:
                rdict['rc'] = InputCheckerError("Some of the mandatory flow resources are missing.")

            if os.path.isfile('SAPLUI5_ARP' + str(ech)):
                t.sh.cp('SAPLUI5_ARP' + str(ech), 'SAPLUI5_ARP')
            else:
                rdict['rc'] = InputCheckerError("Some of the mandatory flow resources are missing.")
        
            if os.path.isfile('SAPLUI5_ANA' + str(ech)):
                t.sh.cp('SAPLUI5_ANA' + str(ech), 'SAPLUI5_ANA')
            else:
                rdict['rc'] = InputCheckerError("Some of the mandatory flow resources are missing.")

            for i,echeance in enumerate(self.days[ech]):
                if os.path.isfile('SAF' + str(echeance)):
                    t.sh.cp('SAF' + str(echeance), 'SAFRAN' + str(i+1))
                else:
                    rdict['rc'] = InputCheckerError("Some of the mandatory flow resources are missing.")


            lastech = Date('{0:s}/+PT{1:s}H'.format(self.date.ymdh, str(self.days[ech][-1])))
            year  = lastech.strftime('%y')
            month = lastech.strftime('%m')
            day   = lastech.strftime('%d')
            hour  = lastech.hh
            sapdat = 'sapdat'
            if os.path.isfile(sapdat):
                os.remove(sapdat)
            with open(sapdat, 'w') as d:
                d.write('{},{},{},{}\n'.format(year, month, day, hour))
                d.write('0,0,0\n')
                d.write('3,1,3,3\n')
                d.write('0\n')
                d.write('1,1,0,0,1\n')


            list_name = self.system.path.join(thisdir, 'listist' + str(ech))
            try:
                self.local_spawn(list_name)
            except ExecutionError as e:
                rdict['rc'] = e

#        t.sh.subtitle('Worker {0:s} directory listing (post-execution)'.format(str(member)))
#        t.sh.dir(output=False, fatal=False)  
        t.sh.cd(self.rundir)
        self.system = None

        return rdict


class Pearp2Safran(TaylorRun):

    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            kind = dict(
                values = [ 'pearp2safran' ],
            ),
            refreshtime = dict(
                type = int,
                optional = True,
                default = 20,
            ),
            members =  dict(
                info = "The members that will be processed",
                type = footprints.FPList,
            ),
            interpreter = dict(
                info   = 'The interpreter needed to run the script.',
                values = ['awk', 'ksh', 'bash', 'perl', 'python']
            ),
            engine = dict(
                values = ['parallel']
            ),
        )
    )

    def _default_common_instructions(self, rh, opts):
        ddict = super(Pearp2Safran, self)._default_common_instructions(rh, opts)
        ddict['progname']    = self.absexcutable(rh.container.localpath())
        ddict['progargs']    = footprints.FPList(self.spawn_command_line(rh))
        ddict['interpreter'] = self.interpreter
        return ddict

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        t = vortex.sessions.current()
        context = t.context

        self._default_pre_execute(rh, opts)

        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)

        boss = Boss(scheduler=MaxThreadsScheduler(max_threads=len(self.members)))
        boss.set_instructions(common_i, dict(member=self.members))

        boss.make_them_work()
        boss.wait_till_finished()
        logger.info("All files are processed.")
        report = boss.get_report()
        prp = ParallelResultParser(context)
        for r in report['workers_report']:
            if isinstance(prp(r), Exception):
                raise AlgoComponentError("An error occured during the creation of the SAFRAN ebauche files.")
 

class Safran(ParaBlindRun):

    _abstract = True
    _footprint = dict(
        info = 'AlgoComponent that runs several executions in parallel.',
        attr = dict(
            date   = a_date,
            engine = dict(
                values = ['parallel']
            ),
            refreshtime = dict(
                type = int,
                optional = True,
                default = 20,
            ),
            members =  dict(
                info = "The members that will be processed",
                type = footprints.FPList,
            ),
            terms = dict(
                info = "The list of terms that require an execution.",
                type = footprints.FPList,
            ),
            timeout = dict(
                type = int,
                optional = True,
                default = 300,
            ),
            vconf = dict(
                info    = "The configuration's identifier.",
                alias   = ('configuration',),
                default = '[glove::vconf]',
            ),
        )
    )


    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(Safran, self)._default_common_instructions(rh, opts)
        ddict['date']  = self.date
        ddict['vconf'] = self.vconf
        ddict['terms'] = self.terms
        return ddict


    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        t = vortex.sessions.current()
        context = t.context

        # Before trying to do anything, check the executable
        if not self.valid_executable(rh):
            logger.warning('Resource %s is not a valid executable', rh.resource)
        else:
            t.sh.title('Processing {0:s}'.format(self.kind))

        self._default_pre_execute(rh, opts)

        # Update the common instructions
        common_i = self._default_common_instructions(rh, opts)

        boss = Boss(scheduler=MaxThreadsScheduler(max_threads=len(self.members))) 
        boss.set_instructions(common_i, dict(member=self.members))

        boss.make_them_work()
        boss.wait_till_finished()
        logger.info("All files are processed.")
        report = boss.get_report()
        prp = ParallelResultParser(context)
        for r in report['workers_report']:
            if isinstance(prp(r), Exception):
                raise AlgoComponentError("An error occured in Safran.")


class Safrane(Safran):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'safrane' ],
            ),
        )
    )


class Syrpluie(Safran):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'syrpluie' ],
            ),
        )
    )


class Syrmrr(Safran):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'syrmrr' ],
            ),
        )
    )

class Sytist(Safran):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'sytist' ],
            ),
        )
    )



#class Safrane(ExecutableAlgoComponent):
#    """
#    Run any executable resource many times in the current environment. Mandatory argument is:
#     * engine ( values =  multi )
#    """
#
#    _footprint = dict(
#        info = 'AlgoComponent that runs a serial binary several times in a raw',
#        attr = dict(
#            engine = dict(
#                values = ['safrane']
#            ),
#            date   = a_date,
#            vconf = dict(
#                info        = "The configuration's identifier.",
#                alias       = ('configuration',),
#                default     = '[glove::vconf]',
#            ),
#            terms = dict(
#                info        = "The list of terms that require an execution.",
#                type        = footprints.FPList,
#            ),
#            members = dict(
#                info        = "The list of members that require an execution.",
#                type        = footprints.FPList,
#            ),
#        ),
#    )
#
#
#    def run(self, rh=None, **kw):
#        """Sequence for execution : prepare / execute / postfix."""
#        self._status = True
#
#        # Before trying to do anything, check the executable
#        if not self.valid_executable(rh):
#            logger.warning('Resource %s is not a valid executable', rh.resource)
#            return False
#
#        # Get instance shorcuts to context and system objects
#        t = vortex.sessions.current()
#        self.context = t.context
#        self.system  = self.context.system
#        self.target  = kw.pop('target', None)
#        if self.target is None:
#            self.target = self.system.target()
#
#        rundir = t.sh.getcwd()
#        for member in self.members:
#            t.sh.cd(rundir)
#            if not os.path.exists('mb{0:03d}'.format(member)):
#                t.sh.mkdir('mb{0:03d}'.format(member))
#            t.sh.cd('mb{0:03d}'.format(member))
#            for term in self.terms:
#                t.sh.subtitle('Running term : {0:s}'.format(str(term))) 
#                # A cloned environment will be bound to the OS
#                self.env = self.context.env.clone()
#                with self.env:
#
#                    # The actual "run" recipe
#                    self.prepare(rh, t, term, rundir, kw)            #1
#                    self.fsstamp(kw)                #2
#                    try:
#                        self.execute(rh, kw)        #3
#                    finally:
#                        self.execute_finalise(kw)   #3.1
#                    self.fscheck(kw)                #4
#                    self.postfix(rh, kw)            #5
#                    self.dumplog(kw)                #6
#                    self.delayed_exceptions(kw)     #7
#
#                    # Free local references
#                    self.env = None
#        t.sh.cd(rundir)
#        self.system = None
#
#        return self._status
#
#
#
#    def prepare(self, rh, t, term, rundir, opts):
#        """Set some last minute information for the execution."""
#        super(Safrane, self).prepare(rh, opts)
#        # Creation of the 'sapdat' file containing the exact date of the file to be processed.
#        startdate = Date('{0:s}/+PT{1:s}H'.format(self.date.ymdh, str(term)))
#        year  = startdate.strftime('%y')
#        month = startdate.strftime('%m')
#        day   = startdate.strftime('%d')
#        hour  = startdate.hh        
#        sapdat = 'sapdat'
#        if os.path.isfile(sapdat):
#            os.remove(sapdat)
#        with open(sapdat, 'w') as d:
#            d.write('{},{},{},{}\n'.format(year, month, day, hour))
#            d.write('0,0,0\n')
#            d.write('3,1,1,3\n')
#            d.write('0\n')
#            d.write('1,1,1,1\n')
##            d.write("{},{},{},{},0,0,0,3,1,1,3\n".format(year, month, day, hour))
#        
#        # Création of the 'sapfich' file containing the name of the output file
#        with open('sapfich', 'w') as f:
#            f.write('SAF' + str(term))
#
#        # Generate the 'OPxxxxx' files containing links for the safran execution.
#        
#        for op_file in _OP_files[self.vconf]:
#            with open(op_file, 'w') as f:
#                f.write(rundir + '@')
#
#        executable = rh.container.localpath()
#        if not os.path.islink(executable):
#            t.sh.symlink('../' + executable, executable)
#
#
#    def execute_single(self, rh, opts):
#        """
#        Run the specified resource handler as an absolute executable,
#        using the resource command_line method as args.
#        """
#
#        args = [self.absexcutable(rh.container.localpath())]
#        args.extend(self.spawn_command_line(rh))
#        logger.debug('BlindRun executable resource %s', args)
#        self.spawn(args, opts)
#
