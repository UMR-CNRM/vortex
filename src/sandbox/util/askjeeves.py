# -*- coding: utf-8 -*-

"""
A place to test callback functions for Jeeves.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import io
import json
import os
import time
from ast import literal_eval
from configparser import ConfigParser

from bronx.fancies import loggers as b_loggers
from jeeves import butlers, pools, talking

#: No automatic export
__all__ = []


def test_foo(pnum, ask, config, logger, **kw):
    """Jeeves debugging access point.

    Simple sleep.
    """
    profile = config['driver'].get('profile', None)
    logger.info('External', todo=ask.todo, pnum=pnum, profile=profile, opts=kw)
    rc, value = True, None
    try:
        duration = 0.1
        try:
            duration = float(ask.data['duration'])
        except ValueError:
            logger.error('Bad duration from', data=ask.data)
        logger.warning('Sleep', duration=duration)
        time.sleep(duration)
    except Exception as trouble:
        logger.error('An exception occurred during execution:' + str(trouble))
        rc, value = False, dict(rpool='error')

    return pnum, rc, value


def test_bar(pnum, ask, config, logger, **kw):
    """Jeeves debugging access point.

    Adding an entry in jeeves config is heavier than having a simple selector
    here:

        - slow_write: slowly writes to a file in jeeves directory.
          To test the retry scheme, use "value = dict(rpool='retry')"
        - stamp : write a timestamp to a file

    """
    try:
        profile = config['driver'].get('profile', None)
    except (AttributeError, TypeError):
        profile = None
    logger.info('test_bar', todo=ask.todo, pnum=pnum, profile=profile, opts=kw)
    selector = ask.data.get('selector', None)
    logger.info('\t', data=ask.data, pwd=os.getcwd())

    if selector is None:
        logger.error('no selector given')
        rc, value = False, dict(rpool='error')

    elif selector == 'slow_write':
        finalpath = ask.data.get('filepath', None)
        temporary = finalpath + '.tmp'
        with io.open(temporary, 'a+') as fp:
            for step in range(11):
                fp.write('step {:02d}\n'.format(step))
                fp.flush()
                time.sleep(3)
        os.rename(temporary, finalpath)
        rc, value = True, None

    elif selector == 'timestamp':
        filepath = ask.data.get('filepath', 'test_bar.txt')
        ask_time = ask.data.get('ask_time', 'not specified')
        message = ask.data.get('message', 'no message')
        now_time = time.strftime('%Y%m%d %H:%M:%S', time.localtime())
        with io.open(filepath, 'a+') as fp:
            fp.write('test_bar stamp - ask time {} - run time {} - {}\n'.format(ask_time, now_time, message))
        rc, value = True, None

    else:
        logger.warning('selector unknown: ', selector=selector)
        rc, value = False, dict(rpool='error')

    return pnum, rc, value


def test_vortex(pnum, ask, config, logger, **kw):
    """Jeeves debugging access point.

    Activation of a vortex context.
    """
    from vortex.util.worker import VortexWorker

    logger.debug('External', todo=ask.todo, pnum=pnum, opts=kw)
    logger.info('External', todo=ask.todo, pnum=pnum, opts=kw)
    logger.warning('External', todo=ask.todo, pnum=pnum, opts=kw)
    logger.error('External', todo=ask.todo, pnum=pnum, opts=kw)
    logger.critical('External', todo=ask.todo, pnum=pnum, opts=kw)

    profile = config['driver'].get('profile', None)
    with VortexWorker(logger=logger, modules=('common', 'olive'), profile=profile) as vwork:
        sh = vwork.session.sh
        sh.trace = 'log'
        logger.debug('Test Level DEBUG', vwork=vwork)
        logger.info('Test Level INFO', vwork=vwork)
        logger.warning('Test Level WARNING', vwork=vwork)
        logger.error('Test Level ERROR', vwork=vwork)
        logger.critical('Test Level CRITICAL', vwork=vwork)

        data = vwork.get_dataset(ask)
        duration = 1
        try:
            duration = float(data.duration)
        except (ValueError, AttributeError):
            logger.error('Bad or no duration in data:', data=data)
        logger.info('Sleep', duration=duration)
        sh.sleep(duration)
        logger.info('TestVortex', todo=ask.todo, pnum=pnum, session=vwork.session.tag)
    return pnum, vwork.rc, None


def directly_call_jeeves_callback(cb_function):
    """Run a jeeves async callback as if it was called by jeeves, but from the main process.

    This may be run interactively in a debugger.
    """

    # common part
    logger = talking.FancyArgsLoggerAdapter(b_loggers.getLogger(__name__), dict())
    jname = 'test'
    jpath = os.path.expanduser('~/jeeves/' + jname + '/depot')
    jfile = 'vortex'
    jtag = jpath + '/' + jfile
    fulltalk = dict(user='user', jtag=jtag, mail=None, apps='play', conf='sandbox', task='interactif', )

    # specifics
    cb_function_name = cb_function.__name__
    now = time.strftime('%Y%m%d %H:%M:%S', time.localtime())
    data = dict(selector='timestamp', ask_time=now, message='test callback ' + cb_function_name,
                duration=1, filepath=cb_function_name + '.txt', )
    fulltalk.update(todo=cb_function_name, data=data)

    # generate a json for reference
    request = pools.Request(**fulltalk)
    request.dump()
    print('request dumped to', request.last)

    # and directly call the fonction
    config = dict(driver=dict(profile='research'))
    cb_function(1, request, config, logger)


def execute_a_json_askfile(jsonfile):
    """Execute a json file like jeeves would, but in a debuggable direct call."""

    # read the json request (jeeves.butlers.Jeeves.json_load())
    with io.open(os.path.expanduser(jsonfile), 'rb') as fd:
        obj = json.load(fd)
    ask = pools.Request(**obj)

    # read jeeves config (jeeves.butlers.Jeeves.read_config())
    cfg = ConfigParser()
    cfg.read(os.path.expanduser('../../../conf/jeeves-test.ini'))
    config = dict(driver=dict(pools=[]))
    for section in cfg.sections():
        if section not in config:
            config[section] = dict()
        for k, v in cfg.items(section):
            try:
                v = literal_eval(v)
            except (SyntaxError, ValueError):
                if k.startswith('options') or ',' in v:
                    v = v.replace('\n', '').replace(' ', '').split(',')
            config[section][k.lower()] = v

    # what do we have to do (jeeves.butlers.Jeeves.process_request())
    action = 'action_' + ask.todo
    if action in cfg:
        acfg = cfg[action]
    else:
        raise ValueError('Cannot find action ' + action)
    thismod = acfg.get('module', 'internal')
    thisname = acfg.get('entry', ask.todo)

    # options from the config, overridden by the json 'opts' if any
    # (variant of jeeves.butlers.Jeeves.dispatch())
    opts = ask.opts.copy()
    options = acfg.get('options', '').split(',')
    print(type(options), options)
    for extra in [x for x in options
                  if x not in opts]:
        opts[extra] = acfg.get(extra, None)
        print('opts["{}"]={}'.format(extra, opts[extra]))

    # build the arguments (ibidem)
    logfacility = talking.LoggingBasedLogFacility()
    args = (
        logfacility.worker_logger_cb,
        logfacility.worker_logger_setid_manager,
        'info', thismod, thisname, '001', ask, config.copy()
    )

    # and this is what the subprocess calls !
    rc = butlers._dispatch_func_wrapper(*args, **opts)
    print('rc =', rc)


if __name__ == '__main__':
    print('current working directory:', os.getcwd())

    # directly_call_jeeves_callback(cb_function=test_vortex)

    json_concat = "ask.20210827192526.221655.P006488.pascal.vortex.json"
    json_synopsis = "ask.20210827192526.248749.P006488.pascal.vortex.json"
    execute_a_json_askfile('~/jeeves/keep/' + json_concat)
