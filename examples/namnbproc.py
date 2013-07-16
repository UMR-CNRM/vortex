#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex

from vortex import toolbox
from vortex.algo import mpitools

import common, olive, gco
from gco.tools import genv

t = vortex.ticket()
t.warning()

sh = t.context.system
e = t.context.env

print t.line

sh.cd(e.HOME + '/tmp/bidon')
print t.prompt, sh.pwd()

genv.genvbin = e.HOME  + '/bin/genvfake'
genv.autofill('cy37t1_op1.20')

print t.line
print t.prompt, 'CYCLES', genv.cycles()

prvcst  = toolbox.provider(genv='cy37t1_op1.20', gspool=e.HOME + '/gco-tampon')

fp = toolbox.defaults(
    namespace='open.archive.fr',
    model='arpege',
)

print t.line, fp(), t.line

nams = toolbox.input(
    provider = prvcst,
    role     = 'Namelist',
    kind     = 'namelist',
    source   = 'namelistfcp',
    local    = 'fort.4',
)

for namfc in nams:
    print 'GET', namfc.location(), '...', namfc.get()

sh.dir(output=False)

print t.line

mpi = mpitools.load(sysname=sh.sysname, mpiname='mpirun', mpiopts='-nnp 2 -nn 3')

print t.prompt, mpi

t.info()
mpi.setup(t.context)

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line

vortex.exit()
