#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from tempfile import mkdtemp

import footprints
logger = footprints.loggers.getLogger(__name__)

import vortex.tools.actions
import iga.tools.services

from iga.util import swissknife

def setup(**kw):
    """
    Open a new vortex session with an op profile,
    set behavior defaults and return the current ticket.
    """

    opd = kw.get('actual', dict())

    import vortex
    footprints.proxy.targets.discard_onflag('is_anonymous', verbose=False)

    t = vortex.sessions.get()
    t.sh.subtitle('OP setup')

    t.sh.prompt = t.prompt
    t.info()

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Set a new glove')

    gl = vortex.sessions.getglove(
        tag     = 'opid',
        profile = opd.get('op_suite', 'oper')
    )

    print gl.idcard()

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Activate a new session with previous glove')

    t  = vortex.sessions.get(
        tag     = 'opview',
        active  = True,
        glove   = gl,
        topenv  = vortex.rootenv,
        prompt  = vortex.__prompt__
    )

    print t.idcard()

    t.sh.prompt = t.prompt

    gl.vapp  = kw.get('vapp',  opd.get('op_vapp',  None))
    gl.vconf = kw.get('vconf', opd.get('op_vconf', None))

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Toolbox description')

    print '+ Root directory =', t.glove.siteroot
    print '+ Path directory =', t.glove.sitesrc
    print '+ Conf directory =', t.glove.siteconf

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Op session')

    print '+ Session Ticket =', t
    print '+ Session Glove  =', t.glove
    print '+ Session System =', t.sh
    print '+ Session Env    =', t.env

    #--------------------------------------------------------------------------------------------------
    t.sh.header('This target')

    tg = vortex.proxy.target(hostname = t.sh.hostname)
    print '+ Target name    =', tg.hostname
    print '+ Target system  =', tg.sysname
    print '+ Target inifile =', tg.inifile

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Verbosity settings')

    t.sh.trace = True
    t.env.verbose(True, t.sh)

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Stack settings')

    t.sh.setulimit('stack')

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Add-ons to the shell')

    import vortex.tools.lfi
    shlfi = footprints.proxy.addon(kind='lfi', shell=t.sh)
    print '+ Add-on LFI', shlfi
    shio = footprints.proxy.addon(kind='iopoll', shell=t.sh)
    print '+ Add-on IO POLL', shio

    import vortex.tools.odb
    shodb = footprints.proxy.addon(kind='odb', shell=t.sh)
    print '+ Add-on ODB', shodb

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Actual running directory')

    t.env.RUNDIR = kw.get('rundir', mkdtemp(prefix=t.glove.tag + '-'))
    t.sh.cd(t.env.RUNDIR, create=True)
    t.rundir = t.sh.getcwd()

    logger.info('Current rundir <%s>', t.rundir)

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Toolbox module settings')

    vortex.toolbox.active_verbose = True
    vortex.toolbox.active_now     = True
    vortex.toolbox.active_insitu  = True
    vortex.toolbox.active_clear   = True

    for activeattr in [ x for x in dir(vortex.toolbox) if x.startswith('active_') ]:
        print '+', activeattr.ljust(16), '=', getattr(vortex.toolbox, activeattr)

    #--------------------------------------------------------------------------------------------------
    t.sh.header('External imports')

    import common
    import olive.data.providers
    from iga.data import containers, providers, stores

    print '+ common               =', common.__file__
    print '+ olive.data.providers =', olive.data.providers.__file__
    print '+ iga.data.containers  =', containers.__file__
    print '+ iga.data.providers   =', providers.__file__
    print '+ iga.data.stores      =', stores.__file__

    #--------------------------------------------------------------------------------------------------
    t.sh.header('Op Actions')
    ad = vortex.tools.actions.actiond
    ad.add(vortex.tools.actions.SmsGateway())

    print '+ SMS candidates =', ad.candidates('sms')

    #--------------------------------------------------------------------------------------------------
    t.sh.header('SMS Settings')
    ad.sms_info()

    if t.env.SMSPASS is None:
        ad.sms_off()

    ad.sms_init(t.env.SLURM_JOBID)

    return t


def setenv(t, **kw):
    """Set up common environment for all oper execs"""

    t.sh.subtitle('OP setenv')

    import vortex
    t.env.OP_VORTEX = vortex.__version__

    #--------------------------------------------------------------------------------------------------
    t.sh.header('SLURM Environment')

    nb_slurm = 0
    for envslurm in sorted([ x for x in t.env.keys() if x.startswith('SLURM') ]):
        print '{0:s}="{1:s}"'.format(envslurm, t.env[envslurm])
        nb_slurm += 1

    logger.info('Batch variables found: %d', nb_slurm)

    #--------------------------------------------------------------------------------------------------
    t.sh.header('OP Environment')
    opd = kw.get('actual', dict())
    nb_op = 0
    for opvar in sorted([ x for x in opd.keys() if x.startswith('op_') ]):
        t.env.setvar(opvar, opd[opvar])
        nb_op += 1

    logger.info('Global op variables found: %d', nb_op)

    #--------------------------------------------------------------------------------------------------
    t.sh.header('MPI Environment')

    mpi, rkw = swissknife.slurm_parameters(t, **kw)
    t.env.OP_MPIOPTS = mpi

    #--------------------------------------------------------------------------------------------------
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

    return t.env.clone()


def complete(t, **kw):
    """Exit from OP session."""
    ad = vortex.tools.actions.actiond
    ad.sms_complete()
    t.close()


def register(t, cycle, dump=True):
    """Load and register a GCO cycle contents."""
    from gco.tools import genv
    if cycle in genv.cycles():
        logger.warning('Cycle %s already registred', cycle)
    else:
        if t.env.OP_ROOTAPP:
            genvdef = t.sh.path.join(t.env.OP_ROOTAPP, 'genv', cycle + '.genv')
            if t.sh.path.exists(genvdef):
                logger.info('Fill GCO cycle with file <%s>', genvdef)
                genv.autofill(cycle, t.sh.cat(genvdef, output=True))
            else:
                logger.error('No contents defined for cycle %s', cycle)
                raise ValueError('Bad cycle value')
        else:
            logger.warning('OP context without OP_ROOTAPP variable')
            genv.autofill(cycle)
        if dump:
            print genv.as_rawstr(cycle=cycle)


def rescue(**kw):
    """Something goes wrong... so, do your best to save current state."""
    ad = vortex.tools.actions.actiond
    ad.sms_abort()
    print 'Bad luck...'


def fulltraceback(localsd=None):
    """Produce some nice traceback at the point of failure."""

    if not localsd:
        localsd = dict()

    if 't' in localsd:
        sh = localsd['t'].sh
    else:
        sh = None

    if sh:
        sh.title('Handling exception')
    else:
        print '-' * 100

    import sys, traceback
    (exc_type, exc_value, exc_traceback) = sys.exc_info()

    print 'Exception type: ' + str(exc_type)
    print 'Exception info: ' + str(localsd.get('trouble', None))
    if sh:
        sh.header('Traceback Error / BEGIN')
    else:
        print '-' * 100
    print "\n".join(traceback.format_tb(exc_traceback))
    if sh:
        sh.header('Traceback Error / END')
    else:
        print '-' * 100

