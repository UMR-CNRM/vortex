#!/usr/bin/env python2.7
# encoding: utf-8
"""
Run the BasicInputMonitor.
"""

import multiprocessing as mp
import time

import footprints as fp

from utils import promises_generator as pgen
from vortex.layout import monitor

# vlogger = fp.loggers.getLogger('vortex')
# vlogger.setLevel('INFO')
mlogger = fp.loggers.getLogger('vortex.layout.monitor')
mlogger.setLevel('INFO')


class Spy(fp.observers.ParrotObserver):
    """Just look into the observerboard."""

    def updobsitem(self, item, info):
        self._debuglogging('upd item %s info %s -> %s',
                           item.section.rh.container.filename,
                           info['previous_state'], info['state'])


def look_for_promises(args):
    t, wkdir, tbex = pgen.ini_expected(args)
    t.sh.header("Ok: All the expected resources are set. Now I start looking.")
    try:
        with monitor.BasicInputMonitor(t.context, role=pgen.R_ROLE,
                                       caching_freq=2, crawling_threshold=1) as bm:
            james = Spy()
            # Register the observer to the various classes
            for entry in bm.memberslist:
                entry.observerboard.register(james)
            while not bm.all_done:
                # print 'Unactive since: ', bm.inactive_time
                time.sleep(1)
    finally:
        t.sh.cd(t.env.HOME)
        t.sh.rm(wkdir)


if __name__ == "__main__":
    args = pgen.promises_argparse()
    ready_evt = mp.Event()
    pmaker = mp.Process(target=pgen.auto_promises, args=(args, ready_evt))
    pmaker.start()
    ready_evt.wait()
    look_for_promises(args)
    pmaker.join()
