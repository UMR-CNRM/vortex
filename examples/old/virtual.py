# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import vortex
import sandbox.data

t = vortex.ticket()
t.warning()

print(t.line)

print(t.prompt, 'Load the test resource')

print(t.line)

test = vortex.toolbox.rh(
    tube='ftp',
    hostname='cougar.meteo.fr',
    remote='tmp/titi',
    kind='simple',
    extra=2,
    cutoff='p',
    foo='treize',
    bigmodel='arpege',
    incore=True
)

print(test.idcard())
print(test.get())

print(t.line)

print(test.container.localpath(), '- filled ?', test.container.filled, test.container._tmpfile)

print(t.line)

print(test.history())

print(t.line)

test.container.cat()

print(t.line)

c = test.contents

print(c)

for x in c:
    print('CONTENTS:', x)

print('LEN:', len(c))
print('RAW:', c())

print(t.line)

print(t.prompt, 'Duration time =', t.duration())

print(t.line)
