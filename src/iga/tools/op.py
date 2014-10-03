#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from tempfile import mkdtemp

from iga.util import swissknife


def setup(**kw):
    """
    Open a new vortex session with an op profile,
    set behavior defaults and return the current ticket.
    """

    opd = kw.get('actual', dict())

    import vortex
    gl = vortex.sessions.glove(
        tag     = 'opid',
        profile = opd.get('op_suite', 'oper')
    )

    t  = vortex.sessions.ticket(
        tag     = 'opview',
        active  = True,
        glove   = gl,
        topenv  = vortex.rootenv,
        prompt  = vortex.__prompt__
    )

    t.warning()

    gl.vapp  = kw.get('vapp',  opd.get('op_vapp',  None))
    gl.vconf = kw.get('vconf', opd.get('op_vconf', None))

    # A nice summary of active session components
    t.sh.title('Op session')
    print t.prompt, 'Session Ticket =', t
    print t.prompt, 'Session Glove  =', t.glove
    print t.prompt, 'Session System =', t.sh
    print t.prompt, 'Session Env    =', t.env

    # Activate trace verbosity for os interface
    t.sh.trace = True
    t.env.verbose(True, t.sh)

    # Unlimited stack
    t.sh.setulimit('stack')

    # Define the actual running directory
    t.sh.subtitle('Switch to rundir')
    t.env.RUNDIR = kw.get('rundir', mkdtemp(prefix=t.glove.tag + '-'))
    t.sh.cd(t.env.RUNDIR, create=True)
    t.sh.pwd(output=False)

    # Set toolbox verbosity and default behavior
    vortex.toolbox.verbose   = 2
    vortex.toolbox.justdoit  = True
    vortex.toolbox.getinsitu = True

    #some usefull import for footprint resolution
    import common
    import olive.data.providers
    from iga.data import containers, providers, stores

    return t


def setenv(t, **kw):
    """Set up common environment for all oper execs"""

    t.sh.title('Op setenv')

    import vortex
    t.env.OP_VORTEX = vortex.__version__

    # Nice display of current batch environment
    t.sh.header('SLURM Env')
    nb_slurm = 0
    for envslurm in sorted([ x for x in t.env.keys() if x.startswith('SLURM') ]):
        print '{0:s}="{1:s}"'.format(envslurm, t.env[envslurm])
        nb_slurm += 1
    print 'Looking for automatic batch variables:', nb_slurm, 'found.'

    # Set top levels OP variables from the job itself
    t.sh.header('TOP OP Env')
    opd = kw.get('actual', dict())
    nb_op = 0
    for opvar in sorted([x for x in opd.keys() if x.startswith('op_') ]):
        t.env.setvar(opvar, opd[opvar])
        nb_op += 1
    print 'Looking for global op variables:', nb_op, 'found.'

    # Get default MPI options from current SLURM env
    t.sh.header('MPI Env')
    mpi, rkw = swissknife.slurm_parameters(t, **kw)
    t.env.OP_MPIOPTS = mpi

    # Set a default date according to DATE_PIVOT or last synoptic hour
    t.sh.header('DATE Env')
    if t.env.OP_RUNDATE:
        if not isinstance(t.env.OP_RUNDATE, vortex.tools.date.Date):
            t.env.OP_RUNDATE = vortex.tools.date.Date(t.env.OP_RUNDATE)
    else:
        anytime = kw.get('runtime', t.env.get('OP_RUNTIME', None))
        anydate = kw.get(
            'rundate',
            t.env.get(
                'DMT_DATE_PIVOT',
                vortex.tools.date.synop(delta=kw.get('delta', '-PT2H'), time=anytime)
            )
        )
        rundate = vortex.tools.date.Date(anydate)
        t.env.OP_RUNDATE = rundate
        t.env.OP_RUNTIME = rundate.time()

    return t.env.clone()


def complete(t, **kw):
    """Exit from OP session."""
    t.close()


def rescue(**kw):
    """Something goes wrong... so, do your best to save current state."""
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
    print 'Exception info: ' + str(localsd.get('last_error', None))
    if sh:
        sh.header('Traceback Error / BEGIN')
    else:
        print '-' * 100
    print "\n".join(traceback.format_tb(exc_traceback))
    if sh:
        sh.header('Traceback Error / END')
    else:
        print '-' * 100

