#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time


def foo(pnum, ask, config, logger, **kw):
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
    return (pnum, rc, value)

def vortex_namespaces():
    print  "\n", '-' * 80, "\n"
    vortex.toolbox.print_namespaces()
    print  "\n", '-' * 80, "\n"

def test_vortex(pnum, ask, config, logger, **kw):
    value = 'Yip'
    from vortex.util.worker import VortexWorker
    with VortexWorker(logger=logger, modules=('common',)) as vwork:
        logger.info('Vortex', todo=ask.todo, pnum=pnum, ticket=vwork.vortex.ticket().tag)
        logger.loglevel = 'debug'
        logger.debug('Ah que coucou')
    return (pnum, vwork.rc, value)
