#!/usr/bin/env python
# -*- coding: utf-8 -*-

import vortex
from vortex import toolbox, tools

t = vortex.ticket()
e = t.env
sh = t.sh

sh.trace = True
e.verbose(True, sh)


from vortex.tools.actions import actiond as ad
from iga.tools import actions
from iga.tools import services

ad.alarm_on()
ad.agt_on()

#### Listes des services et actions
tell_me = False
if tell_me:
    import pprint
    print 'available actions:', ad.actions()
    print 'existing handlers:\n', pprint.pformat(ad.items())
    print 'action/handlers:'
    for act in ad.actions():
        handlers = ad.candidates(act)
        status   = ad.__getattr__(act + '_status')()
        print act,':', pprint.pformat(zip(status, handlers))


dtime = tools.date.now().compact()
stime = dtime[:8] + '_' + dtime[8:]

# ce serait mieux de pouvoir s'en passer...
toolbox.defaults(
    hostname = sh.hostname
)

ad.alarm(
    message ='an AlarmLogService at ' + stime,
    level   = 'debug',
)

ad.alarm(
    message = 'an AlarmRemoteService (with syshost) at ' + stime,
    level   = 'debug',
    syshost = 'localhost',
)
