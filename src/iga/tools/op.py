#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex

def setup(*args):
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

    return t, sh, e

def submit(*args):
    return ( True, 0 )
