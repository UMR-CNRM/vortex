#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time

#: No automatic export
__all__ = []


def test_foo(pnum, ask, config, logger, **kw):
    """Jeeves debugging access point.
       Simple sleep.
    """
    rc, value = True, 'Yo'
    logger.info('External', todo=ask.todo, pnum=pnum, opts=kw)
    try:
        duration = 1
        try:
            duration = int(ask.data)
        except StandardError:
            logger.error('Bad duration type', data=ask.data)
        logger.warning('Sleep', duration=duration)
        time.sleep(duration)
    except StandardError as trouble:
        rc, value = False, str(trouble)
    return pnum, rc, value


def test_bar(pnum, ask, config, logger, **kw):
    """Jeeves debugging access point.
       Slowly writes to a file in jeeves directory.
       To test the retry scheme, use "value = dict(rpool='retry')"
    """
    import os
    logger.info('test_bar', todo=ask.todo, pnum=pnum, opts=kw)
    logger.loglevel = 'debug'
    logger.debug('\t', ask=ask, pwd=os.getcwd())

    finalpath  = ask.data.get('filepath', None)
    temporary = finalpath + '.tmp'
    with open(temporary, 'a+') as fp:
        for step in range(11):
            fp.write('step {:02d}\n'.format(step))
            fp.flush()
            time.sleep(3)
    os.rename(temporary,finalpath)
    rc = True
    value = None
    return pnum, rc, value


def test_vortex(pnum, ask, config, logger, **kw):
    """Jeeves debugging access point.
       Activation of a vortex context.
    """
    value = 'Yip'
    from vortex.util.worker import VortexWorker
    with VortexWorker(logger=logger, modules=('common', 'olive')) as vwork:
        logger.info('Vortex', todo=ask.todo, pnum=pnum, ticket=vwork.vortex.ticket().tag)
        logger.loglevel = 'debug'
        logger.debug('Ah que coucou', data=ask.data, kw=kw)
    return pnum, vwork.rc, value
