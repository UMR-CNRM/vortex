#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import re
import six
from tempfile import mkdtemp

from bronx.fancies import loggers
import bronx.stdtypes.date

import vortex  # @UnusedImport
from vortex.tools.actions import actiond as ad
from iga.util import swissknife
from vortex.layout.dataflow import InputsReportStatus as rStatus
from vortex.layout.jobs import JobAssistant

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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

        print(gl.idcard())

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
                t.sh.softlink(t.env["LOG_SBATCH"],
                              '/home/ch/mxpt001/resul/' + t.env["SLURM_JOB_NAME"] + '.dayf')

        nb_slurm = self.print_somevariables(t, 'SLURM')
        tg = vortex.sh().default_target
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
            logger.warning('No "LUSTRE_OPER" variable in the environment, '
                           'unable to export MTOOLDIR and datadir')

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

        mpi, u_rkw = swissknife.slurm_parameters(t, **kw)  # @UnusedVariable
        t.env.OP_MPIOPTS = mpi

        t.sh.header('Setting up the rundate')

        if t.env.OP_RUNDATE:
            if not isinstance(t.env.OP_RUNDATE, bronx.stdtypes.date.Date):
                t.env.OP_RUNDATE = bronx.stdtypes.date.Date(t.env.OP_RUNDATE)
        else:
            anydate = kw.get('rundate', t.env.get('DMT_DATE_PIVOT', None))
            if anydate is None:
                anytime = kw.get('runtime', t.env.get('OP_RUNTIME', None))
                anystep = kw.get('runstep', t.env.get('OP_RUNSTEP', 6))
                rundate = bronx.stdtypes.date.synop(delta=kw.get('delta', '-PT2H'), time=anytime, step=anystep)
            else:
                rundate = bronx.stdtypes.date.Date(anydate)
                if t.env.OP_VAPP == 'mocage' and t.env.OP_VCONF == 'camsfcst':
                    rundate = bronx.stdtypes.date.Date(rundate.ymdh + '/+PT12H')

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

        t.sh.header("Setting up the s2m path")
        t.env.setvar("SNOWTOOLS_CEN", '/home/ch/mxpt001/vortex/snowtools')

    def _extra_session_setup(self, t, **kw):
        super(OpJobAssistantTest, self)._extra_session_setup(t, **kw)

        t.sh.subtitle('Setting up the actual running directory')

        t.env.RUNDIR = kw.get('rundir', mkdtemp(prefix=t.glove.tag + '-'))
        t.sh.cd(t.env.RUNDIR, create=True)
        t.sh.chmod(t.env.RUNDIR, 0o755)
        t.rundir = t.sh.getcwd()
        logger.info('Current rundir <%s>', t.rundir)

    def _toolbox_setup(self, t, **kw):
        super(OpJobAssistantTest, self)._toolbox_setup( t, **kw)
        opd = kw.get('actual', dict())
        vortex.toolbox.defaults(
            jname = opd.get('op_jeeves', None),
            smtpserver='smtp.meteo.fr',
            sender='admin_prod_sc@meteo.fr',
        )

    def _actions_setup(self, t, **kw):
        """Setup the OP action dispatcher."""
        super(OpJobAssistantTest, self)._actions_setup(t, **kw)

        t.sh.subtitle('Setting up OP Actions')
        import iga.tools.services  # @UnusedImport
        import iga.tools.actions  # @UnusedImport

        ad.add(vortex.tools.actions.EcflowGateway())

        print('+ ECFLOW candidates =', ad.candidates('ecflow'))

        print('+ JEEVES candidates =', ad.candidates('jeeves'))
        print('+ JEEVES default =', vortex.toolbox.defaults.get('jname'))

        # ----------------------------------------------------------------------
        t.sh.header('START message to op MESSDAYF reporting file')
        ad.report(kind='dayfile', mode='DEBUT')

        # ----------------------------------------------------------------------
        t.sh.header('ECFLOW Settings')
        ad.ecflow_info()
        ad.ecflow_off()

        if t.env['ECF_PASS'] is not None:
            ad.ecflow_on()
            ad.ecflow_init(t.env.SLURM_JOBID)

    def _system_setup(self, t, **kw):
        """Set usual settings for the system shell."""
        super(OpJobAssistantTest, self)._system_setup( t, **kw)
        t.sh.allow_cross_users_links = False

    def register_cycle(self, cycle):
        """Load and register a GCO cycle contents."""
        t = vortex.ticket()
        from gco.tools import genv
        if cycle in genv.cycles():
            logger.info('Cycle %s already registered', cycle)
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
            print(genv.as_rawstr(cycle=cycle))

    def complete(self):
        """Exit from OP session."""
        ad.report(kind='dayfile', mode='FIN')
        ad.ecflow_complete()
        print('Well done Denis !')
        super(OpJobAssistantTest, self).complete()

    def rescue(self):
        """Exit from OP session after a crash but simulating a happy ending. Use only in a test environment."""
        ad.ecflow_abort()
        print('Bad luck...')
        super(OpJobAssistantTest, self).rescue()

    def finalise(self):
        super(OpJobAssistantTest, self).finalise()
        print('Bye bye Op...')


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
            print(tfile)
            print(option_insertion)
            with io.open(tfile, "w") as f:
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

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self._report(self._ticket, exc_type is None)

    def _report(self, t, try_ok=True):
        """Report status of the OP session (input review, mail diffusion...)."""
        raise NotImplementedError("To be overwritten...")


class InputReportContext(_ReportContext):
    """Context manager that print a report on inputs."""

    def __init__(self, task, ticket,
                 alternate_tplid='mode_secours',
                 nonfatal_tplid='input_nonfatal_error',
                 fatal_tplid='input_error'):
        super(InputReportContext, self).__init__(task, ticket)
        self._alternate_tplid = alternate_tplid
        self._nonfatal_tplid = nonfatal_tplid
        self._fatal_tplid = fatal_tplid

    def _report(self, t, try_ok=True, **kw):
        """Report status of the OP session (input review, mail diffusion...)."""
        t.sh.header('Input review')
        report = t.context.sequence.inputs_report()
        report.print_report(detailed=True)
        mail_statuses = [rStatus.PRESENT, rStatus.EXPECTED, rStatus.MISSING]
        if try_ok:
            if any(report.active_alternates()):
                t.sh.header('Input informations: active alternates were found')
                if self._alternate_tplid:
                    ad.opmail(task=self._task.tag, id=self._alternate_tplid,
                              report=report.synthetic_report(only=mail_statuses))
            elif any(report.missing_resources()):
                t.sh.header('Input informations: missing resources')
                if self._nonfatal_tplid:
                    ad.opmail(task=self._task.tag, id=self._nonfatal_tplid,
                              report=report.synthetic_report(only=rStatus.MISSING))
            else:
                t.sh.header('Input informations: everything is ok')
        else:
            t.sh.header('Input informations: one of the input failed')
            if self._fatal_tplid:
                ad.opmail(task=self._task.tag, id=self._fatal_tplid,
                          report=report.synthetic_report(only=mail_statuses))


class OutputReportContext(_ReportContext):
    """Context manager that print a report on outputs."""

    def __init__(self, task, ticket, fatal_tplid='output_error'):
        super(OutputReportContext, self).__init__(task, ticket)
        self._fatal_tplid = fatal_tplid

    def _report(self, t, try_ok=True, **kw):
        """Report status of the OP session (input review, mail diffusion...)."""
        if try_ok:
            t.sh.header('Output informations: everything is ok')
        else:
            t.sh.header('Output informations: one of the output failed')
            ad.opmail(task=self._task.tag, id=self._fatal_tplid)


def get_resource_value(r, key):
    """ this function returns the resource value """
    try:
        kw = dict(area=lambda r: r.resource.geometry.area,
                  term=lambda r: r.resource.term,
                  fields=lambda r: r.resource.fields)
        return kw[key](r)
    except AttributeError as e:
        logger.error(e)


def filteractive(r, dic):
    """ this function returns the filter status """
    filter_active = True
    if dic is not None:
        for k, w in six.iteritems(dic):
            if not get_resource_value(r, k) in w:
                logger.info('filter not active : {} = {} actual value : {}'.
                            format(k, w, get_resource_value(r, k)))
                filter_active = False
    return filter_active


def oproute_hook_factory(kind, productid, sshhost, optfilter=None, soprano_target=None,
                         routingkey=None, selkeyproductid=None, targetname=None, transmet=None,
                         header_infile=True, **kw):
    """Hook functions factory to route files while the execution is running.

    :param str kind: kind use to route
    :param str or dict productid: (use selkeyproductid to define the dictionary key)
    :param str shhost: tranfertnode
    :param dict optfilter: dictionary (used to allow routing)
    :param str soprano_target: str (piccolo or piccolo-int)
    :param str routingkey: the BD routing key
    :param str selkeyproductid: (example: area, term, fields ...)
    :param str targetname:
    :param dict transmet:
    :param bool header_infile: use to add transmet header in routing file
    """

    def hook_route(t, rh):
        kwargs = dict(kind=kind, productid=productid, sshhost=sshhost,
                      filename=rh.container.abspath, soprano_target=soprano_target,
                      routingkey=routingkey, targetname=targetname, transmet=transmet,
                      header_infile=header_infile, **kw)

        if selkeyproductid:
            if isinstance(productid, dict):
                kwargs['productid'] = productid[get_resource_value(rh, selkeyproductid)]
                logger.info('productid key : %s ', get_resource_value(rh, selkeyproductid))
            else:
                logger.warning('productid is not a dict : %s', productid)

        if hasattr(rh.resource, 'geometry'):
            kwargs['domain'] = rh.resource.geometry.area
        if hasattr(rh.resource, 'term'):
            kwargs['term'] = rh.resource.term
            if kwargs['transmet']:
                kwargs['transmet']['ECHEANCE'] = rh.resource.term.fmth

        if filteractive(rh, optfilter):
            ad.route(** kwargs)
            print(t.prompt, 'routing file = ', rh)

    return hook_route


def opphase_hook_factory(optfilter=None):
    """Hook functions factory to phase files while the execution is running.

    :param dict optfilter: (used to allow routing) """

    def hook_phase(t, rh):
        if filteractive(rh, optfilter):
            ad.phase(rh)
            print(t.prompt, 'phasing file = ', rh)

    return hook_phase


def opecfmeter_hook_factory(maxvalue, sharedadvance=None, useterm=False):
    """
    Hook functions factory to update an ecflow progress bar while the execution
    is running.

    :param int maxvalue:  total number of items
    :param bool useterm: if True use rh.resource.term for progress bar
    :param sharedadvance: <class 'multiprocessing.sharedctypes.Synchronized'>

    example of use for 'sharedadvance'(this code must be implemented in the task.py)::

        >>> import multiprocessing as mp
        >>> avancement = mp.Value('i', 0)
        >>> hook_ecfmeter = op.opecfmeter_hook_factory(len(tb01), sharedadvance=avancement)

    """
    def hook_ecfmeter(t, rh):  # @UnusedVariable
        max_value = int(maxvalue)
        current_value = 0
        if hasattr(rh.resource, 'term') and useterm:
                current_value = rh.resource.term.hour
        if sharedadvance:
            if useterm:
                if sharedadvance.value < current_value:
                    with sharedadvance.get_lock():
                        sharedadvance.value = current_value
                else:
                    return
            else:
                with sharedadvance.get_lock():
                    sharedadvance.value += 1
            current_value = sharedadvance.value

        progress = (current_value * 100.0) / max_value
        ad.ecflow_meter('avancement', int(progress + 0.5))

    return hook_ecfmeter
