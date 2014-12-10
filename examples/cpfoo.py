#!/usr/bin/env python
# -*- coding:Utf-8 -*-

# Status : Looks OK (v0.6.21)

import vortex
import olive
import sandbox.data
from vortex.data import geometries

t = vortex.ticket()
t.warning()

ra = dict(
    model='arpege', kind='analysis', date='2011112800', cutoff='long',
    geometry=geometries.get(tag='globalsp')
)

print t.line

e = t.env
sh = t.system()
sh.cd(e.HOME + '/tmp/rundir', create=True)

thefile = 'titi'
if sh.path.exists(thefile):
    print 'Remove', thefile
    sh.unlink(thefile)

rl = vortex.toolbox.rh

with open('/tmp/toto', 'w') as fp:
    fp.write('not empty')

a = rl(ra, remote='/tmp/toto', file=thefile)

print t.line
print a.idcard()
print t.line
print t.prompt, 'LOC', a.locate()
print t.prompt, 'GET', a.location(), '...', a.get()
print t.prompt, 'CLEAR', '...', a.clear()
print t.prompt, 'GET', '...', a.get()
print t.prompt, a.history()
sh.dir(output=False)

print t.line

a = rl(ra, remote='/tmp/toto', file='tmp/' + thefile)

print t.line
print a.idcard()
print t.line
print t.prompt, 'LOC', a.locate()
print t.prompt, 'GET', a.location(), '...', a.get()
print t.prompt, a.history()
sh.dir(output=False)

# user = 'mrpm631'
user = 'mcdi004'
sh.ftp('cougar.meteo.fr', user).put(thefile, 'tmp/titi')

a = rl(ra, tube='ftp', hostname='cougar.meteo.fr', remote='tmp/titi', file='bidon/' + thefile)

print t.line
print a.idcard()
print t.line
print t.prompt, 'LOC', a.locate()
print t.prompt, 'GET', a.location(), '...', a.get()
print t.prompt, a.history()
sh.dir(output=False)

print t.line

thefile = 'signum'
if sh.path.exists(thefile):
    print 'Remove', thefile
    sh.unlink(thefile)

a = rl(ra, remote='tmp/signum', file=thefile, hostname='cougar.meteo.fr', tube='ftp')

print t.line
print a.idcard()
print t.line
print t.prompt, 'LOC', a.locate()
print t.prompt, 'GET', a.location(), '...', a.get()
print t.prompt, a.history()
sh.dir(output=False)

print t.line

a = rl(ra, experiment='A001', block='canari', file='titi', namespace='olive.cache.fr')

print t.line
print a.idcard()
print t.line
print t.prompt, 'LOC', a.locate()
print t.prompt, 'GET', a.location(), '...', a.put()
print t.prompt, a.history()
sh.dir(output=False)

print t.line
