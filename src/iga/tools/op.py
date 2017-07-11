#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re
from tempfile import mkdtemp

import vortex  # @UnusedImport
import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.actions import actiond as ad
from iga.util import swissknife
from vortex.layout.jobs import JobAssistant


class OpJobAssistantTest(JobAssistant):

    _footprint = dict(
        info = 'Op Job assistant.',
        attr = dict(
            kind = dict(
                values = ['op_test'],
            ),
        ),
    )

    def _early_session_setup(self, t, **kw):
        """Create a now session, set important things, ..."""

        t.sh.subtitle('Setting up a new glove')

        opd = kw.get('actual', dict())
        gl = vortex.sessions.getglove(
            tag     = 'opid',
            profile = opd.get('op_suite', 'oper')
        )

        print gl.idcard()

        # ----------------------------------------------------------------------
        t.sh.header('Activate a new session with previous glove')

        t  = vortex.sessions.get(
            tag     = 'opview',
            active  = True,
            glove   = gl,
            topenv  = vortex.rootenv,
            prompt  = vortex.__prompt__
        )

        return super(OpJobAssistantTest, self)._early_session_setup(t, **kw)

    def _env_setup(self, t, **kw):
        """OP session's environment setup."""
        super(OpJobAssistantTest, self)._env_setup(t, **kw)

        t.sh.subtitle('OP setup')

        # Symlink to job's last execution log in op's resul directory
        if "SLURM_JOB_NAME" in t.env():
            if t.sh.path.islink('/home/ch/mxpt001/resul/' + t.env["SLURM_JOB_NAME"] + '.dayf'):
                t.sh.unlink('/home/ch/mxpt001/resul/' + t.env["SLURM_JOB_NAME"] + '.dayf')
            if "LOG_SBATCH" in t.env():
                t.sh.softlink(t.env["LOG_SBATCH"], '/home/ch/mxpt001/resul/' + t.env["SLURM_JOB_NAME"] + '.dayf')

        nb_slurm = self.print_somevariables(t, 'SLURM')
        tg = vortex.sh().target()
        # Set trace
        self.add_extra_traces(t)
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

        # Set a new variable for availability notifications
        
      
        if "SLURM_JOB_NAME" in t.env:
            t.env.setvar("OP_DISP_NAME", "_".join(t.env["SLURM_JOB_NAME"].split("_")[:-1]))
        else:
            t.env.setvar("OP_DISP_NAME", None)
        

        t.sh.header('Setting up the MPI Environment')

        mpi, rkw = swissknife.slurm_parameters(t, **kw)
        t.env.OP_MPIOPTS = mpi

        t.sh.header('Setting up the rundate')

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

        t.sh.header('Setting up suitebg')

        if t.env.OP_SUITEBG is None:
            t.env.OP_SUITEBG = t.env.get('OP_XPID', None)

        t.sh.header("Setting up the member's number")
        if not t.env.OP_MEMBER and t.env.get('DMT_ECHEANCE'):
            t.env.OP_MEMBER = t.env.get('DMT_ECHEANCE')[-3:]
        logger.info('Effective member  = %s', t.env.OP_MEMBER)

    def _extra_session_setup(self, t, **kw):
        super(OpJobAssistantTest, self)._extra_session_setup(t, **kw)

        t.sh.subtitle('Setting up the actual running directory')

        t.env.RUNDIR = kw.get('rundir', mkdtemp(prefix=t.glove.tag + '-'))
        t.sh.cd(t.env.RUNDIR, create=True)
        t.sh.chmod(t.env.RUNDIR, 0755)
        t.rundir = t.sh.getcwd()
        logger.info('Current rundir <%s>', t.rundir)

    def _toolbox_setup(self, t, **kw):
        super(OpJobAssistantTest, self)._toolbox_setup( t, **kw)
        opd = kw.get('actual', dict())
        vortex.toolbox.defaults(
            jname = opd.get('op_jeeves', None),
            smtpserver='smtp.meteo.fr',
            sender='dt_dsi_op_iga_sc@meteo.fr',
        )

    def _actions_setup(self, t, **kw):
        """Setup the OP action dispatcher."""
        super(OpJobAssistantTest, self)._actions_setup(t, **kw)

        t.sh.subtitle('Setting up OP Actions')
        import iga.tools.services
        import iga.tools.actions

        ad.add(vortex.tools.actions.SmsGateway())

        print '+ SMS candidates =', ad.candidates('sms')

        print '+ JEEVES candidates =', ad.candidates('jeeves')
        print '+ JEEVES default =', vortex.toolbox.defaults.get('jname')

        # ----------------------------------------------------------------------
        t.sh.header('START message to op MESSDAYF reporting file')
        ad.report(kind='dayfile', mode='DEBUT')

        # ----------------------------------------------------------------------
        t.sh.header('SMS Settings')
        ad.sms_info()

        if t.env.SMSPASS is None:
            ad.sms_off()

        ad.sms_init(t.env.SLURM_JOBID)

    def register_cycle(self, cycle):
        """Load and register a GCO cycle contents."""
        t = vortex.ticket()
        from gco.tools import genv
        if cycle in genv.cycles():
            logger.info('Cycle %s already registred', cycle)
        else:
            if t.env.OP_GCOCACHE:
                genvdef = t.sh.path.join(t.env.OP_GCOCACHE, 'genv', cycle + '.genv')
            else:
                logger.warning('OP context without OP_GCOCACHE variable')
                genv.autofill(cycle)
            if t.sh.path.exists(genvdef):
                logger.info('Fill GCO cycle with file <%s>', genvdef)
                genv.autofill(cycle, t.sh.cat(genvdef, output=True))
            else:
                logger.error('No contents defined for cycle %s or bad opcycle path %s', cycle, genvdef)
                raise ValueError('Bad cycle value')
            print genv.as_rawstr(cycle=cycle)

    def complete(self):
        """Exit from OP session."""
        ad.report(kind='dayfile', mode='FIN')
        ad.sms_complete()
        print 'Well done Denis !'
        super(OpJobAssistantTest, self).complete()

    def rescue(self):
        """Exit from OP session after a crash but simulating a happy ending. Use only in a test environment."""
        ad.sms_abort()
        print 'Bad luck...'
        super(OpJobAssistantTest, self).rescue()

    def finalise(self):
        super(OpJobAssistantTest, self).finalise()
        print 'Bye bye Op...'


class OpJobAssistant(OpJobAssistantTest):

    _footprint = dict(
        info = 'Op Job assistant.',
        attr = dict(
            kind = dict(
                values = ['op_default'],
            ),
        ),
    )

    def finalise(self):
        super(OpJobAssistant, self).finalise()
        t = vortex.ticket()
        ad.phase_flush()
        if 'DMT_PATH_EXEC' in t.env():
            option_insertion = ('--id ' + t.env['SLURM_JOB_ID'] + ' --date-pivot=' +
                                t.env['DMT_DATE_PIVOT'] + ' --job-path=' +
                                re.sub(r'.*vortex/', '', t.env['DMT_PATH_EXEC'] + '/' + t.env['DMT_JOB_NAME']) +
                                ' --log=' +
                                re.sub(r'.*oldres/', '', t.env['LOG_SBATCH'] + ' --machine ' + t.env['CALCULATEUR']))
            if 'DATA_OUTPUT_ARCH_PATH' in t.env:
                option_insertion = option_insertion + ' --arch-path=' + t.env['DATA_OUTPUT_ARCH_PATH']
            tfile = t.env['HOME'] + '/tempo/option_insertion.' + t.env['SLURM_JOB_ID'] + '.txt'
            print tfile
            print option_insertion
            with open(tfile, "w") as f:
                f.write(option_insertion)

    def rescue(self):
        """Something goes wrong... so, do your best to save current state."""
        ad.report(kind='dayfile', mode='ERREUR')
        super(OpJobAssistant, self).rescue()


class _ReportContext(object):
    """Context manager that print a report."""

    def __init__(self, task, ticket):
        self._task = task
        self._ticket = ticket
        self._step = None

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self._report(self._ticket, exc_type is None, task=self._task.tag, step=self._step)

    def _report(self, t, try_ok=True, **kw):
        """Report status of the OP session (input review, mail diffusion...)."""
        step      = kw.get('step', 'unknown_step')
        reseau    = t.env.getvar('OP_RUNDATE').hh
        task      = kw.get('task', 'unknown_task')
        report    = t.context.sequence.inputs_report()
        logpath   = t.env.getvar('LOG')
        rundir    = t.env.getvar('RUNDIR') + '/opview/' + task
        vapp      = t.env.getvar('OP_VAPP').upper()
        vconf     = t.env.getvar('OP_VCONF').lower()
        xpid      = t.env.getvar('OP_XPID').lower()
        hasmember = t.env.getvar('OP_HASMEMBER')
        

        report.print_report(detailed=True)
        if try_ok:
            t.sh.header('Input review')
            if any(report.active_alternates()):

                if hasmember:
                    member = t.env.getvar('OP_MEMBER')
                    t.sh.header('Input informations: active alternates were found')
                    subject = "{0:s} {1:s} {2:s} : Utilisation de la tâche alternative {3:s} pour le membre {4:s} du réseau {5:s}h.".format(xpid.upper(),vapp,vconf,task,str(member),reseau)
                    ad.opmail(subject=subject, reseau=reseau, task=task, member=str(member), id='mode_secours', report=report.synthetic_report(), log=logpath, rundir=rundir, vapp=vapp, vconf=vconf, xpid=xpid)
                else: 
                    t.sh.header('Input informations: active alternates were found')
                    subject = "{0:s} {1:s} {2:s} : Utilisation de la tâche alternative {3:s} pour le réseau {4:s}h.".format(xpid.upper(),vapp,vconf,task,reseau)
                    ad.opmail(reseau=reseau, task=task, id='mode_secours', report=report.synthetic_report(), log=logpath, rundir=rundir, vapp=vapp, vconf=vconf, xpid=xpid)
            else:
                t.sh.header('Input informations: everything is ok')
        else:
            t.sh.header('Input informations: {0:s} fail'.format(step)) 
            mail_id = 'error'
            
            if hasmember:
                member    = t.env.getvar('OP_MEMBER')   
                if step == 'input':
                    msg       = "La récupération des inputs de la tâche {0:s} du membre {1:s}".format(task,str(member)) 
                    subject   = "{0:s} {1:s} {2:s} : Problème de récupération des inputs de la tâche {3:s} du membre {4:s} pour le réseau {5:s}h".format(xpid.upper(),vapp,vconf,task,str(member),reseau)
                elif step == 'output':
                    msg     = "L'archivage des outputs de la tâche {0:s} du membre {1:s}".format(task,str(member))
                    subject = "{0:s} {1:s} {2:s} : Problème d'archivage des outputs de la tâche {0:s} du membre {1:s} pour le réseau {2:s}h.".format(xpid.upper(),vapp,vconf,task,str(member),reseau)
                ad.opmail(subject=subject, reseau=reseau, msg=msg, task=task, member=str(member), id=mail_id, report=report.synthetic_report(), log=logpath, rundir=rundir, vapp=vapp, vconf=vconf, xpid=xpid)
            else:
                if step == 'input':
                    msg        = "La récupération des inputs de la tâche {0:s}".format(task)
                    subject = "{0:s} {1:s} {2:s} : Problème de récupération des inputs de la tâche {3:s} du réseau {4:s}h".format(xpid.upper(),vapp,vconf,task,reseau)
                elif step == 'output':
                    msg     = "L'archivage des outputs de la tâche {0:s}".format(task)
                    subject = "{0:s} {1:s} {2:s} : Problème d'archivage des outputs de la tâche {0:s} du réseau {1:s}h.".format(xpid.upper(),vapp,vconf,task,reseau)
                ad.opmail(subject=subject, reseau=reseau, msg=msg, task=task, id=mail_id, report=report.synthetic_report(), log=logpath, rundir=rundir, vapp=vapp, vconf=vconf, xpid=xpid)

class InputReportContext(_ReportContext):
    """Context manager that print a report on inputs."""

    def __init__(self,task, ticket):
        super(InputReportContext, self).__init__(task, ticket)
        self._step = 'input'

class OutputReportContext(_ReportContext):
    """Context manager that print a report on outputs."""

    def __init__(self, task, ticket):
        super(OutputReportContext, self).__init__(task, ticket)
        self._step = 'output'

def get_resource_value(r,key):
    """ this function returns the resource value """
    try:
        kw = dict(area=lambda r:r.resource.geometry.area, term=lambda r:r.resource.term, fields=lambda r:r.resource.fields)
        return kw[key](r)
    except AttributeError as e:
        logger.error(e)
    
def filteractive(r,dic):
    """ this function returns the filter status """
    filter_active = True
    for k,w in dic.iteritems():
        if not get_resource_value(r,k) in w:
            logger.info('filter not active : {} = {} actual value : {}'.format(k, w, get_resource_value(r,k)))
            filter_active=False
    return filter_active    

def oproute_hook_factory(kind, productid, sshhost, optfilter=None, soprano_target=None, routingkey=None, selkeyproductid=None):
    """Hook functions factory to route files while the execution is running"""
        

    """
        :param kind: str kind use to route
        :param productid: str or dictionary (use selkeyproductid to define the dictionary key)
        :param sshhost: tranfertnode
        :param optfilter: dictionary (used to allow routing)
        :param soprano_target: str (piccolo or piccolo-int)
        :param routingkey : str
        :param selkeyproductid :str (example: area, term, fields ...) 
    """

    def hook_route(t, rh):
        kwargs= dict(kind=kind, productid=productid, sshhost=sshhost,
                    filename=rh.container.abspath, soprano_target=soprano_target, routingkey=routingkey)
        route_active = True
        if selkeyproductid:
            if isinstance(productid, dict):
                kwargs['productid'] = productid[get_resource_value(rh,selkeyproductid)]
                logger.info('productid key : %s ',get_resource_value(rh,selkeyproductid))
            else:
                logger.warning('productid is not a dict : %s', productid)

        if hasattr(rh.resource, 'geometry'):
            kwargs['domain'] = rh.resource.geometry.area
        if hasattr(rh.resource, 'term'):
            kwargs['term'] = rh.resource.term

        if optfilter:
            route_active = filteractive(rh,optfilter)

        if route_active:
            ad.route(** kwargs)
            print t.prompt, 'routing file = ', rh

    return hook_route

def opphase_hook_factory(optfilter=None):
    """Hook functions factory to phase files while the execution is running"""

    """ :param optfilter: dictionary (used to allow routing) """

    def hook_phase(t, rh):
        route_active = True
        if optfilter:
            route_active = filteractive(rh,optfilter)

        if route_active:
            ad.phase(rh)
            print t.prompt, 'phasing file = ', rh

    return hook_phase
