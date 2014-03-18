#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex

from vortex.syntax.stdattrs import models
models.append('mocage')

from sandbox.data.resources import SimpleTest

t = vortex.ticket()
t.warning()

print t.prompt, 'Playing an extra model'

print t.prompt, 'Load the test resource'

print t.line

print t.prompt, 'SimpleTest footprint', SimpleTest.retrieve_footprint().as_dict()

print t.line

gr = vortex.toolbox.rh(remote='databox', kind='simple', extra=2, cutoff='p', foo='treize', bigmodel='mocage', virtual=True)

print t.line, gr.idcard()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line
