#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import toolbox, sessions

from vortex.syntax.stdattrs import models
models.append('mocage')

from sandbox.data.resources import SimpleTest

t = sessions.ticket()
t.warning()

print t.prompt, 'Playing an extra model'

print t.prompt, 'Load the test resource'

print t.line

print t.prompt, 'SimpleTest footprint', SimpleTest.footprint().as_dict()

print t.line

gr = toolbox.rload(remote='databox', kind='simple', extra=2, cutoff='p', foo='treize', bigmodel='mocage', virtual=True).pop()

print t.line, gr.idcard(), t.line

print t.prompt, 'Duration time =', t.duration()
