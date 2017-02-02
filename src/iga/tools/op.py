#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from tempfile import mkdtemp

import footprints
logger = footprints.loggers.getLogger(__name__)

import vortex.tools.actions
import iga.tools.services
from vortex.tools.actions import actiond as ad

from iga.util import swissknife


def OpJobAssistant(JobAssistant):

    def _env_setup(self, t, **kw):
        """OP session's environment setup."""
        super(JobAssistant, self)._env_setup(*args, **kw)        

        t.sh.subtitle('OP setup')

        #Symlink to job's last execution log in op's resul directory
        if "SLURM_JOB_NAME" in t.env():
            if t.sh.path.islink('/home/ch/mxpt001/resul/' + t.env["SLURM_JOB_NAME"] + '.dayf'):
                t.sh.unlink('/home/ch/mxpt001/resul/' + t.env["SLURM_JOB_NAME"] + '.dayf')
            if "LOG_SBATCH" in t.env():
                t.sh.softlink(t.env["LOG_SBATCH"], '/home/ch/mxpt001/resul/' + t.env["SLURM_JOB_NAME"] + '.dayf')

        t.sh.header('Actual running directory')

        t.env.RUNDIR = kw.get('rundir', mkdtemp(prefix=t.glove.tag + '-'))
        t.sh.cd(t.env.RUNDIR, create=True)
        t.sh.chmod(t.env.RUNDIR, 0755)
        t.rundir = t.sh.getcwd()
        logger.info('Current rundir <%s>', t.rundir)

        t.sh.header('SLURM Environment')

        nb_slurm = 0
        for envslurm in sorted([ x for x in t.env.keys() if x.startswith('SLURM') ]):
            print '{0:s}="{1:s}"'.format(envslurm, t.env[envslurm])
            nb_slurm += 1
        logger.info('Batch variables found: %d', nb_slurm)

        t.sh.header('OP Environment')

        opd = kw.get('actual', dict())
        nb_op = 0
        for opvar in sorted([ x for x in opd.keys() if x.startswith('op_') ]):
            t.env.setvar(opvar, opd[opvar])
            nb_op += 1
        tg = vortex.sh().target()

        # Set some more environment variables from the 'target*.ini' file 
        if "LUSTRE_OPER" in t.env:
            lustre_oper = "/" + t.env["LUSTRE_OPER"]
            t.env.setvar("MTOOLDIR", lustre_oper + tg.get('op:MTOOLDIR'))
            t.env.setvar("DATADIR", lustre_oper + tg.get('op:datadir'))
            if t.env.OP_GCOCACHE is None:
                t.env.setvar("OP_GCOCACHE", lustre_oper + tg.get('gco:gcocache'))
        else:
            logger.warning('No "LUSTRE_OPER" variable in the environment, unable to export MTOOLDIR and datadir')

        if "LOG_SBATCH" in t.env():
            t.env.setvar("LOG", t.env["LOG_SBATCH"])
        elif nb_slurm > 0:
            t.env.setvar("LOG", t.env["SLURM_SUBMIT_DIR"] + '/slurm-' + t.env["SLURM_JOB_ID"] + '.out')
        else:
            t.env.setvar("LOG", None)
        logger.info('Global op variables found: %d', nb_op)

        t.sh.header('MPI Environment')

        mpi, rkw = swissknife.slurm_parameters(t, **kw)
        t.env.OP_MPIOPTS = mpi

        t.sh.header('Setting rundate')

        if t.env.OP_RUNDATE:
            if not isinstance(t.env.OP_RUNDATE, vortex.tools.date.Date):
                t.env.OP_RUNDATE = vortex.tools.date.Date(t.env.OP_RUNDATE)
        else:
            anydate = kw.get('rundate', t.env.get('DMT_DATE_PIVOT', None))
            if anydate is None:
                anytime = kw.get('runtime', t.env.get('OP_RUNTIME', None))
                anystep = kw.get('runstep', t.env.get('OP_RUNSTEP', 6))
                rundate = vortex.tools.date.synop(delta=kw.get('delta', '-PT2H'), time=anytime, step=anystep)
            else:
                rundate = vortex.tools.date.Date(anydate)
            t.env.OP_RUNDATE = rundate
        t.env.OP_RUNTIME = t.env.OP_RUNDATE.time()
        logger.info('Effective rundate = %s', t.env.OP_RUNDATE.ymdhm)
        logger.info('Effective time    = %s', t.env.OP_RUNTIME)

        t.sh.header('Setting suitebg')

        if not t.env.OP_SUITEBG:
            t.env.OP_SUITEBG = t.env.get('OP_XPID', None)

        t.sh.header('Setting member')

        if not t.env.OP_MEMBER:
            t.env.OP_MEMBER = t.env.get('DMT_ECHEANCE', None)[-3:]
        logger.info('Effective member  = %s', t.env.OP_MEMBER)


    def _actions_setup(self, t, **kw):
        """Setup the OP action dispatcher."""
      
        t.sh.header('Op Actions')

        ad = vortex.tools.actions.actiond
        ad.add(vortex.tools.actions.SmsGateway())

        print '+ SMS candidates =', ad.candidates('sms')

        vortex.toolbox.defaults(
            jname = opd.get('op_jeeves', None)
        )

        print '+ JEEVES candidates =', ad.candidates('jeeves')
        print '+ JEEVES default =', vortex.toolbox.defaults.get('jname')

        #--------------------------------------------------------------------------------------------------
        t.sh.header('START message to op MESSDAYF reporting file')
        ad.report(kind='dayfile', mode='DEBUT')

        #--------------------------------------------------------------------------------------------------

        t.sh.header('SMS Settings')
        ad.sms_info()

        if t.env.SMSPASS is None:
            ad.sms_off()

        ad.sms_init(t.env.SLURM_JOBID)
        t.sh.signal_intercept_on()


    def report(self, t, try_ok=True, **kw):
        """Report status of the OP session (input review, mail diffusion...)."""
        step    = kw.get('step', 'unknown_step')
        reseau  = t.env.getvar('OP_RUNDATE').hh
        task    = kw.get('task', 'unknown_task')
        report  = t.context.sequence.inputs_report()
        logpath = t.env.getvar('LOG')
        rundir  = t.env.getvar('RUNDIR') + '/opview/' + task
        model   = t.env.getvar('OP_VAPP').upper()
        conf    = t.env.getvar('OP_VCONF').lower()
        xpid    = t.env.getvar('OP_XPID').lower()
        report.print_report(detailed=True)
        if try_ok:
            t.sh.header('Input review')
            if any(report.active_alternates()):
                t.sh.header('Input informations: active alternates were found')
                ad.opmail(reseau=reseau, task=task, id='mode_secours', report=report.synthetic_report(), log=logpath, rundir=rundir, model=model, conf=conf, xpid=xpid)
            else:
                t.sh.header('Input informations: everything is ok')
        else:
            t.sh.header('Input informations: {0:s} fail'.format(step))
            mail_id = '{0:s}_fail'.format(step)
            ad.opmail(reseau=reseau, task=task, id=mail_id, report=report.synthetic_report(), log=logpath, rundir=rundir, model=model, conf=conf, xpid=xpid)

    def complete(self, t, **kw):
        """Exit from OP session."""
        ad = vortex.tools.actions.actiond
        ad.report(kind='dayfile', mode='FIN')
        ad.sms_complete()
        t.sh.signal_intercept_off()
        t.close()

    def simulate_complete(self, t, **kw):
        """Exit from OP session after a crash but simulating a happy ending. Use only in a test environment."""
        ad = vortex.tools.actions.actiond
        ad.sms_abort()
        t.close()

    def rescue(self, **kw):
        """Something goes wrong... so, do your best to save current state."""
        ad = vortex.tools.actions.actiond
        ad.report(kind='dayfile', mode='ERREUR')
        ad.sms_abort()
        print 'Bad luck...'
        super(JobAssistantPlugin, self).rescue()        


class InputReportContext(object):
    """Context manager that print a report on inputs."""

    def __init__(self, task, ticket):
        self._task = task
        self._ticket = ticket

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if isinstance(exc_value, StandardError):
            fulltraceback(dict(t=self._ticket))
        report(self._ticket, exc_type is None, task=self._task.tag, step='input')

class OutputReportContext(object):
    """Context manager that print a report on outputs."""

    def __init__(self, task, ticket):
        self._task = task
        self._ticket = ticket

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if isinstance(exc_value, StandardError):
            fulltraceback(dict(t=self._ticket))
        report(self._ticket, exc_type is None, task=self._task.tag, step='output')


def oproute_hook_factory(kind, productid, sshhost, areafilter=None, soprano_target=None, routingkey=None):
    """Hook functions factory to route files while the execution is running"""

    def hook_route(t, rh):
        if (areafilter is None) or (rh.resource.geometry.area in areafilter):
            ad.route(kind=kind, productid=productid, sshhost=sshhost, domain=rh.resource.geometry.area, term=rh.resource.term,
                    filename=rh.container.basename, soprano_target=soprano_target, routingkey=routingkey)
            print t.prompt, 'routing file = ', rh

    return hook_route

