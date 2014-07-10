#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import vortex

t0 = vortex.sessions.ticket()

p = vortex.sessions.prompt()

print p, 'Playing with sessions', t0.line

print p, 'Sessions opened ?', vortex.sessions.sessionstags()

print t0.line

t1 = vortex.sessions.ticket()
print p, 'Current', t1, t1.tag, "\n", t1.started
print t1.glove, "\n", t1.topenv, "\n", t1.env, "\n", t1.context
print p, 'Env current', vortex.tools.env.current()

print t0.line

t2 = vortex.sessions.ticket(tag='zozo', topenv=t0.topenv)
print p, 'Yet an other ticket', t2, t2.tag, "\n", t2.started
print t2.glove, "\n", t2.topenv, "\n", t2.env, "\n", t2.context
print p, 'Env current', vortex.tools.env.current()

print t0.line

print p, 'Sessions opened ?', vortex.sessions.sessionstags()

print t0.line

t3 = vortex.sessions.ticket(tag='root')
print p, 'Check singleton', t3, t3.tag, "\n", t3.started
print t3.glove, "\n", t3.topenv, "\n", t3.env, "\n", t3.context
print p, 'Env current', vortex.tools.env.current()

print t0.line

print p, 'Sessions opened ?', vortex.sessions.sessionstags()

print t0.line

t = vortex.sessions.ticket(tag='current')
print t.prompt, 'Back to current', t, t.tag, "\n", t.started
print t.glove, "\n", t.env, "\n", t.context
print t.prompt, 'Env current', vortex.tools.env.current()

print t0.line

print t.prompt, 'Sessions opened ?', vortex.sessions.sessionstags()
print t.prompt, 'Env current', vortex.tools.env.current()

print t0.line

sb = vortex.sessions.Desk()
print t.prompt, 'Tickets desk as a callable list', sb()
print t.prompt, 'Iterate on tickets desk'
for tt in sb:
    print t.prompt, '  ', tt

print t0.line

print t.prompt, 'Switch to the SECOND session', vortex.sessions.switch('zozo')
t = vortex.sessions.ticket(tag='current')
print t.prompt, 'Last check', t, t.tag, t.glove, t.topenv, t.env, t.context
print t.prompt, 'Env current', vortex.tools.env.current()

print t0.line

print t.prompt, 'Switch to the FIRST session', vortex.sessions.switch('root')
t = vortex.sessions.ticket(tag='current')
print t.prompt, 'Last check', t, t.tag, t.glove, t.topenv, t.env, t.context
print t.prompt, 'Env current', vortex.tools.env.current()

print t0.line

print t0.line, vortex.tools.env.Environment._os

print t1.prompt, 'Duration time =', t1.duration()

print t0.line
