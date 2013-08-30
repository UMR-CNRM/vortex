#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re

from iga.utilities import swissknife

def setup(**kw):
    """
    Open a new vortex session with an op profile,
    set behavior defaults and return the current ticket.
    """

    opd = kw.get('actual', dict())

    import vortex
    gl = vortex.sessions.glove(tag='opid', profile=opd.get('op_suite', 'oper'))
    t  = vortex.sessions.ticket(tag='opview', active=True, glove=gl, topenv=vortex.rootenv, prompt=vortex.__prompt__)

    t.warning()
    gl.setvapp(kw.get('vapp', opd.get('op_vapp', None)))
    gl.setvconf(kw.get('vconf', opd.get('op_vconf', None)))

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
    import resource
    resource.setrlimit(resource.RLIMIT_STACK, (-1, -1))

    # Define the actual running directory
    t.sh.subtitle('Switch to rundir')
    t.env.RUNDIR = kw.get('rundir', t.env.TMPDIR)
    t.sh.cd(t.env.RUNDIR)
    t.sh.pwd(output=False)

    # Set toolbox verbosity
    vortex.toolbox.verbose = 2
    # Allow extended footprints resolution
    vortex.toolbox.setfpext(True)

    #some usefull import for footprint resolution
    import olive.data.providers
    from iga.data import containers, providers, stores

    return t

def setenv(t, **kw):
    """Set up common environment for all oper execs"""

    # Nice display of current batch environment
    t.sh.header('SLURM Env')
    e = t.env
    for envslurm in sorted([ x for x in e.keys() if x.startswith('SLURM') ]):
        print '{0:s}="{1:s}"'.format(envslurm, e[envslurm])

    # Set top levels OP variables from the job itself
    t.sh.header('TOP OP Env')
    opd = kw.get('actual', dict())
    for opvar in sorted([x for x in opd.keys() if x.startswith('op_') ]):
        e.setvar(opvar, opd[opvar])

    # Force some default values that should be valid accross most of the configurations.
    import vortex
    mpi, rkw = swissknife.slurm_parameters(t, **kw)
    t.sh.header('GUESS Env')
    e.update(
        DATE=swissknife.bestdate(),
        MPIOPTS=mpi,
        VORTEX=vortex.__version__,
    )

    return e.clone()

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

