#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, tools

t0 = sessions.ticket()

p = sessions.prompt()

print p, 'Playing with sessions', t0.line

print p, 'Sessions opened ?', sessions.tagsnames()

print t0.line

t1 = sessions.ticket()
print p, 'Current', t1, t1.tag, "\n", t1.started, "\n", t1.glove, "\n", t1.topenv, "\n", t1.env, "\n", t1.context
print p, 'Env current', tools.env.current()

print t0.line

t2 = sessions.ticket(tag='zozo', topenv=t0.topenv)
print p, 'Yet an other ticket', t2, t2.tag, "\n", t2.started, "\n", t2.glove, "\n", t2.topenv, "\n", t2.env, "\n", t2.context
print p, 'Env current', tools.env.current()

print t0.line

print p, 'Sessions opened ?', sessions.tagsnames()

print t0.line

t3 = sessions.ticket(tag='root')
print p, 'Check singleton', t3, t3.tag, "\n", t3.started, "\n", t3.glove, "\n", t3.topenv, "\n", t3.env, "\n", t3.context
print p, 'Env current', tools.env.current()

print t0.line

print p, 'Sessions opened ?', sessions.tagsnames()

print t0.line

t = sessions.ticket(tag='current')
print t.prompt, 'Back to current', t, t.tag, "\n", t.started, "\n", t.glove, "\n", t.env, "\n", t.context
print t.prompt, 'Env current', tools.env.current()

print t0.line

print t.prompt, 'Sessions opened ?', sessions.tagsnames()
print t.prompt, 'Env current', tools.env.current()

print t0.line

sb = sessions.Desk()
print t.prompt, 'Tickets desk as a callable list', sb()
print t.prompt, 'Iterate on tickets desk'
for tt in sb:
    print t.prompt, '  ', tt

print t0.line

print t.prompt, 'Switch to the SECOND session', sessions.switch('zozo')
t = sessions.ticket(tag='current')
print t.prompt, 'Last check', t, t.tag, t.glove, t.topenv, t.env, t.context
print t.prompt, 'Env current', tools.env.current()

print t0.line

print t.prompt, 'Switch to the FIRST session', sessions.switch('root')
t = sessions.ticket(tag='current')
print t.prompt, 'Last check', t, t.tag, t.glove, t.topenv, t.env, t.context
print t.prompt, 'Env current', tools.env.current()

print t0.line

print t0.line, tools.env.Environment._os

print t1.prompt, 'Duration time =', t1.duration()

