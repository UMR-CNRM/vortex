#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex

from vortex import toolbox
from vortex.tools import date
from vortex.data import geometries

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

rundate = date.today()
prvcst  = toolbox.provider(genv='cy37t1_op1.20', gspool=e.HOME + '/gco-tampon')

fp = toolbox.defaults(
    geometry=geometries.getbyname('globalsp'),
    namespace='open.archive.fr',
    date=rundate,
    cutoff='production',
    model='arpege',
)

print t.line, fp(), t.line

xxt = toolbox.input(
    provider = prvcst,
    role     = 'NamelistFPDef',
    kind     = 'namselectdef',
    local    = 'xxt.def',
    now      = True
)

if xxt:
    xxt = xxt[0]
    for k, v in sorted(xxt.contents.items()):
        print k, v

toolbox.fast_resolve = True

fpnams = toolbox.input(
    provider = prvcst,
    role     = 'NamelistFP',
    kind     = 'namselect',
    source   = '[helper::xxtsrc]',
    term     = (0, 1),
    local    = '[helper::xxtnam]',
    helper   = xxt.contents
)

for fp in fpnams:
    print t.prompt, fp.location(), '...', fp.get()

print t.prompt, sh.pwd()

sh.dir(output=False)
