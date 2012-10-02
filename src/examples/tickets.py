#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions

p = sessions.prompt()

print p, 'Playing with sessions'

print p, 'Sessions opened ?', sessions.opened()

t1 = sessions.ticket()
print p, 'Current', t1, t1.tag, t1.started, "\n", t1.glove, "\n", t1.env, "\n", t1.context

g = t1.glove

print t1.prompt, 'Glove =', g
print t1.prompt, 'dict =', g.puredict()

t2 = sessions.ticket(tag='zozo')
print p, 'Yet an other ticket', t2, t2.tag, t2.started, "\n", t2.glove, "\n", t2.env, "\n", t2.context

t3 = sessions.ticket(tag='root')
print p, 'Check singleton', t3, t3.tag, t3.started, "\n", t3.glove, "\n", t3.env, "\n", t3.context

t = sessions.ticket(tag='current')
print t.prompt, 'Back to current', t, t.tag, t.started, "\n", t.glove, "\n", t.env, "\n", t.context

print t.prompt, 'Sessions opened ?', sessions.opened()

sb = sessions.Desk()
print t.prompt, 'Tickets desk as a callable list', sb()
print t.prompt, 'Iterate on tickets desk'
for tt in sb:
    print t.prompt, '  ', tt

print t.prompt, 'Switch to the second session', sessions.switch('zozo')
t = sessions.ticket(tag='current')
print t.prompt, 'Last check', t, t.glove, t.env, t.context

print t.line

print t1.prompt, 'Duration time =', t1.duration()

