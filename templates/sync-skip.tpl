#!$python $pyopts
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import os, sys, glob, datetime

exit_value = 0

sync_name = sys.argv[0].lstrip('./')

with open(sync_name + '.log', 'a') as flog:

    def logging(*msg):
        if sys.version_info.major == 2:
            flog.write(unicode(' '.join([str(m) for m in msg]) + '\n'))
        else:
            flog.write(' '.join([str(m) for m in msg]) + '\n')

    logging('-' * 80)
    logging('Sync tool:', sync_name)
    logging('Sync date:', datetime.datetime.now().isoformat())

    sync_real = os.path.realpath(sync_name)
    logging('Sync real:', sync_real)

    sync_base = sync_real.split('/')[-1]
    logging('Sync base:', sync_base)

    if sync_name != sync_base:
        logging('Sync rmln:', (sync_name, sync_base))
        os.unlink(sync_name)

    logging('Sync skip:', 'true')

    sync_next = [ x for x in glob.glob(sync_name + '.*') if not x.endswith('.log') ]

    if sync_base in sync_next:
        sync_next.sort()
        pos = sync_next.index(sync_base)
        sync_next = sync_next[pos+1:]
        logging('Sync next:', str(sync_next))

        if sync_next:
            os.symlink(sync_next[0], sync_name)
            logging('Sync link:', str((sync_next[0], sync_name)))

    logging('Sync exit:', exit_value)

exit(exit_value)
