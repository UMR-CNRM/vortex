#!/bin/env python
# -*- coding:Utf-8 -*-

# Status : Looks OK (v0.6.21)

import vortex
import sandbox.data
import olive.data

t = vortex.ticket()
t.warning()

ra = dict( model='arpege', kind='analysis', date='2011112800', cutoff='long' )

print t.line

sh = t.system()

thefile = 'titi'
if sh.path.exists(thefile):
    print 'Remove', thefile
    sh.unlink(thefile)

rl = vortex.toolbox.rload
    
lh = rl(ra, remote='/tmp/toto', file=thefile)
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.get()
a.clear()
a.get()
print a.historic

print t.line

lh = rl(ra, remote='/tmp/toto', file='tmp/' + thefile)
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.get()
print a.historic

print t.line

sh.ftp('cougar.meteo.fr', 'mrpm631').put(thefile, 'tmp/titi')

lh = rl(ra, tube='ftp', hostname='cougar.meteo.fr', remote='tmp/titi', file='bidon/' + thefile)
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.get()
print a.historic

print t.line

thefile = 'signum'
if sh.path.exists(thefile):
    print 'Remove', thefile
    sh.unlink(thefile)

lh = rl(ra, remote='tmp/signum', file=thefile, hostname='cougar.meteo.fr', tube='ftp')
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.get()

print t.line

lh = rl(ra, experiment='A001', block='canari', file='titi')
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.put()

print t.line
print t.prompt, 'Duration time =', t.duration()
print t.line

vortex.exit()
