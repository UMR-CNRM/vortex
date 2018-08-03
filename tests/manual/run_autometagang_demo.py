#!/usr/bin/env python2.7
# encoding: utf-8
"""
Run the test of AutoMetaGang class.
"""

from __future__ import print_function
# from __future__ import absolute_import, unicode_literals, division

import multiprocessing as mp
import time

import footprints as fp

from utils import promises_generator as pgen
from vortex.layout import monitor

# vlogger = fp.loggers.getLogger('vortex')
# vlogger.setLevel('INFO')
# mlogger = fp.loggers.getLogger('vortex.layout.monitor')
# mlogger.setLevel('INFO')


class Spy(fp.observers.ParrotObserver):
    """Just look into the observerboard."""

    def updobsitem(self, item, info):
        self._debuglogging('upd item %s info %s -> %s',
                           item.nickname,
                           info['previous_state'], info['state'])


def test_autogang(args, allowmissing=0, waitlimit=0):
    t, wkdir, tbex = pgen.ini_expected(args)
    t.sh.header("Ok: All the expected resources are set. Now I start looking.")
    try:
        with monitor.BasicInputMonitor(t.context, role=pgen.R_ROLE,
                                       caching_freq=2) as bm:
            autometa = monitor.AutoMetaGang()
            autometa.autofill(bm, ('term', 'geometry'),
                              allowmissing=allowmissing, waitlimit=waitlimit)
            # Spy on the individual Gangs
            james = Spy()
            for gang in autometa.memberslist:
                gang.observerboard.register(james)
            # Let's roll !
            while not bm.all_done:
                autometa.state  # Just to keep the states up-to-date
                time.sleep(0.5)
            print('Last meta:', autometa.state)

    finally:
        t.sh.cd(t.env.HOME)
        t.sh.rm(wkdir)


if __name__ == "__main__":
    args = pgen.promises_argparse()

#     allowmissing, waitlimit = (0, 0)
    allowmissing, waitlimit = (1, 6)

    ready_evt = mp.Event()
    pmaker = mp.Process(target=pgen.auto_promises, args=(args, ready_evt))
    pmaker.start()
    ready_evt.wait()
    test_autogang(args, allowmissing, waitlimit)
    pmaker.join()
