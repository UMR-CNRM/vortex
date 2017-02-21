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
    logger.loglevel = 'debug'
    logger.info('External', todo=ask.todo, pnum=pnum, opts=kw)
    try:
        duration = 0.1
        try:
            duration = float(ask.data['duration'])
        except ValueError:
            logger.error('Bad duration from', data=ask.data)
        logger.warning('Sleep', duration=duration)
        time.sleep(duration)
    except StandardError as trouble:
        rc, value = False, str(trouble)
    return pnum, rc, value


def test_bar(pnum, ask, config, logger, **kw):
    """Jeeves debugging access point.

    Adding an entry in jeeves config is heavier than having a simple selector
    here:

        - slow_write: slowly writes to a file in jeeves directory.
          To test the retry scheme, use "value = dict(rpool='retry')"
        - stamp : write a timestamp to a file

    """
    import os
    logger.loglevel = 'info'
    logger.info('test_bar', todo=ask.todo, pnum=pnum, opts=kw)
    selector = ask.data.get('selector', None)
    logger.info('\t', data=ask.data, pwd=os.getcwd())
    rc, value = True, None

    if selector is None:
        logger.warn('no selector given')
        rc, value = -1, "no selector"

    elif selector == 'slow_write':
        finalpath = ask.data.get('filepath', None)
        temporary = finalpath + '.tmp'
        with open(temporary, 'a+') as fp:
            for step in range(11):
                fp.write('step {:02d}\n'.format(step))
                fp.flush()
                time.sleep(3)
        os.rename(temporary, finalpath)

    elif selector == 'timestamp':
        filepath = ask.data.get('filepath', 'test_bar.txt')
        ask_time = ask.data.get('ask_time', 'not specified')
        message = ask.data.get('message', 'no message')
        now_time = time.strftime('%Y%m%d %H:%M:%S', time.localtime())
        with open(filepath, 'a+') as fp:
            fp.write('test_bar stamp - ask time {} - run time {} - {}\n'.format(ask_time, now_time, message))

    else:
        logger.warn('selector unknown: ', selector=selector)
        rc, value = -1, "bad selector"

    return pnum, rc, value


def test_vortex(pnum, ask, config, logger, **kw):
    """Jeeves debugging access point.

    Activation of a vortex context.
    """
    from vortex.util.worker import VortexWorker
    rc, value = True, 'Yo'
    logger.loglevel = 'info'
    logger.info('External', todo=ask.todo, pnum=pnum, opts=kw)
    with VortexWorker(logger=logger, modules=('common', 'olive')) as vwork:
        sh = vwork.vortex.sh()
        sh.trace = True
        data = vwork.get_dataset(ask)
        duration = 1
        try:
            duration = float(data.duration)
        except StandardError:
            logger.error('Bad duration type', duration=data.duration)
        logger.warning('Sleep', duration=duration)
        time.sleep(duration)
        logger.info('TestVortex', todo=ask.todo, pnum=pnum, ticket=vwork.vortex.ticket().tag,
                    logname=data.logname)
    return pnum, vwork.rc, value


def test_direct_call_to_a_jeeves_callback():
    import os
    from jeeves import pools
    from jeeves import butlers

    # common part
    logger = butlers.GentleTalk()
    jname = 'async'
    jpath = os.path.expanduser('~/jeeves/' + jname + '/depot')
    jfile = 'vortex'
    jtag = jpath + '/' + jfile
    fulltalk = dict(user='user', jtag=jtag, mail=None, apps='play', conf='sandbox', task='interactif', )

    # specifics
    now = time.strftime('%Y%m%d %H:%M:%S', time.localtime())
    data = dict(selector='timestamp', ask_time=now, message='test callback', filepath='test_bar.txt', )
    fulltalk.update(todo='test_bar', data=data)
    request = pools.Request(**fulltalk)
    test_bar(1, request, None, logger)


if __name__ == '__main__':
    test_direct_call_to_a_jeeves_callback()
