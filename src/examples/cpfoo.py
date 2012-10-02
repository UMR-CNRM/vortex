#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox
import sandbox.data
import olive.data

t = sessions.ticket()
t.warning()

ra = dict( model='arpege', kind='analysis', date='2011112800', cutoff='long' )

print t.line

c = t.system()

thefile = 'titi'
if c.path.exists(thefile):
    print 'Remove', thefile
    c.unlink(thefile)

lh = toolbox.rload(ra, remote='/tmp/toto', file=thefile)
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.get()
a.clear()
a.get()
print a.historic

print t.line

lh = toolbox.rload(ra, remote='/tmp/toto', file='tmp/' + thefile)
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.get()
print a.historic

print t.line

c.ftp('cougar.meteo.fr', 'mrpm631').put(thefile, 'tmp/titi')

lh = toolbox.rload(ra, tube='ftp', hostname='cougar.meteo.fr', remote='tmp/titi', file='bidon/' + thefile)
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.get()
print a.historic

print t.line

thefile = 'signum'
if c.path.exists(thefile):
    print 'Remove', thefile
    c.unlink(thefile)

lh = toolbox.rload(ra, remote='tmp/signum', file=thefile, hostname='cougar.meteo.fr', tube='ftp')
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.get()

print t.line

lh = toolbox.rload(ra, experiment='A001', block='canari', file='titi')
a = lh.pop()

print a
print 'Complete ?', a.complete
print 'URI =', a.location()
a.put()

print t.line
print t.prompt, 'Duration time =', t.duration()
print t.line

