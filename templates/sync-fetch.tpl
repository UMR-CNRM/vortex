#!$python $pyopts
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import os, sys, io, glob, json, time, datetime

exit_value = 0

sync_name = sys.argv[0].lstrip('./')

with io.open(sync_name + '.log', mode='a', buffering=1) as flog:

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

    promise_file = '$promise'
    logging('Sync file:', promise_file)

    promise_info = None

    if os.stat(promise_file).st_size < 4096:
        with io.open(promise_file, 'r') as fd:
            promise_info = json.load(fd)
    else:
        logging('Sync size:', 'promise file is far too big')

    if promise_info:
        source = promise_info.get('locate').split(';')[0]
        logging('Sync from:', source)

        if source is not None:

            itself = promise_info.get('itself', None)
            logging('Sync self:', itself)

            time_sleep = int(os.environ.get('VORTEX_TIME_SLEEP', 10))
            logging('Sync time:', time_sleep)

            time_retry = int(os.environ.get('VORTEX_TIME_RETRY', 12))
            logging('Sync redo:', time_retry)

            nb = 0
            while os.path.exists(itself):
                time.sleep(time_sleep)
                logging('Sync ----:', datetime.datetime.now().isoformat())
                nb += 1
                if nb > time_retry:
                    logging('Sync stop:', 'too many tries', nb)
                    exit_value = 2
                    break
            else:
                if os.path.exists(source):
                    os.unlink(promise_file)
                    os.symlink(source, promise_file)
                    logging('Sync link:', (source, promise_file))
                else:
                    logging('Sync fake:', source)
                    exit_value = 2

    sync_next = [ x for x in glob.glob(sync_name + '.*') if not x.endswith('.log') ]

    if sync_base in sync_next:
        sync_next.sort()
        pos = sync_next.index(sync_base)
        sync_next = sync_next[pos+1:]
        logging('Sync next:', sync_next)

        if sync_next:
            os.symlink(sync_next[0], sync_name)
            logging('Sync link:', (sync_next[0], sync_name))

    logging('Sync exit:', exit_value)

exit(exit_value)
