#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from iga.utilities import swissknife

def setup(**kw):
    """Open vortex session and return ticket, shell interface and environment gateway."""
    t = vortex.ticket()
    t.warning()

    sh = t.context.system
    e = t.context.env

    print t.line

    print t.prompt, 'Session Ticket =', t
    print t.prompt, 'Session System =', sh
    print t.prompt, 'Session Env    =', e

    sh.trace = True

    print t.line

    sh.cd(e.TMPDIR)
    sh.pwd(output=False)

    #some usefull import for footprint resolution
    import olive.data.providers
    from iga.data import containers, providers, stores

    return t, sh, e

def setenv(t, **kw):
    """Set up common environment for all oper execs"""
    t.context.env.update(
        DATE=swissknife.bestdate(),
        TOOLBOX_VERSION=vortex.__version__,
        ARCHIVE_HOSTNAME='cougar',
        CONTEXT='Op',
        SUITE='oper',
    )

