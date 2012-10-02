#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import toolbox, sessions
import sandbox.data

t = sessions.ticket()
t.warning()

print t.line

print t.prompt, 'Load the test resource'

print t.line

test = toolbox.rload(
    tube='ftp',
    hostname='cougar.meteo.fr',
    #remote='bidon/toto',
    remote='tmp/titi',
    kind='simple',
    extra=2,
    cutoff='p',
    foo='treize',
    bigmodel='arpege',
    #file='bidon/bof'
    #virtual=True
    incore=True
).pop()

print test.idcard()

print t.line

test.get()

print test.container.localpath(), '- filled ?', test.container.filled, test.container._tmpfile

print t.line

print test.historic

print t.line

test.container.cat()

print t.line

c = test.contents

print c

for x in c:
    print 'CONTENTS:', x
    
print 'LEN:', len(c)
print 'RAW:', c()


print t.line

print t.prompt, 'Duration time =', t.duration()
