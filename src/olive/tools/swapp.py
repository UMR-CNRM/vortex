#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re, socket

from vortex.autolog import logdefault as logger


def olive_label(sh, env, tag=None, target=None):
    """Return a nice label string for sms monitoring."""

    label = env.PBS_JOBID or env.SLURM_JOB_ID

    if env.MTOOL_STEP and env.MTOOL_STEP_ID:
        depot = env.MTOOL_STEP_DEPOT or env.MTOOL_STEP_STORE
        renum = re.search(r'\/mstep_(\d+)', depot)
        num = renum.group(1)
        if target is None:
            label = re.sub(r'-batch', '', label)
            label = re.sub(r'^\d+:', '', label)
        else:
            label = re.sub(r'\D+', '', label)
            label = label + '.' + target
        label = ':'.join(reversed(label.split('.')))
        label = '_'.join((label, 'mtool:' + num, env.MTOOL_STEP_ID))
        if tag:
            label = label + ':' + tag

    return label


def guesslocout(sh, env, output):
    """Keep compatibility with previous versions whithout local filename."""

    login = env.SWAPP_USER or sh.getlogin()

    return re.sub(r'^.*?/' + login + '/', 'xpout/', output)


def olive_logname(sh, env, output, localout=None):
    """Return the local path to OLIVE execution output."""

    if localout is None:
        localout = guesslocout(sh, env, output)

    return sh.path.join(env.HOME, localout)


def olive_jobout(sh, env, output, localout=None):
    """Connect to OLIVE daemon in charge of SMS outputs."""

    sh.stderr(['olive_jobout', output, localout])

    if localout is None:
        localout = guesslocout(sh, env, output)

    mstep = 'off'

    if 'MTOOL_STEP' in env and env.MTOOL_STEP_ID:
        mstep = 'on'
        depot = env.MTOOL_STEP_DEPOT or env.MTOOL_STEP_STORE
        localout = ':'.join(
            [ x for x in sh.ls(depot + '/step.[0-9][0-9]') if (
                sh.path.exists(x+'.done') and
                int(re.search(r'\.(\d+)$', x).group(1)) < int(env.MTOOL_STEP)
            ) ]
        )

    localhost = env.VORTEX_TARGET or env.VORTEX_TARGET_HOST or env.TARGET_HOST or sh.hostname
    swapp_user, swapp_host, swapp_port = env.VORTEX_OUTPUT_ID.split(':')
    user = env.VORTEX_TARGET_LOGNAME or env.TARGET_LOGNAME or env.SWAPP_USER or sh.getlogin()

    if 'VORTEX_SOCKET_TIMEOUT' in env:
        timeout = int(env.VORTEX_SOCKET_TIMEOUT)
    else:
        timeout = 10

    try:
        client_socket = socket.create_connection((swapp_host, swapp_port), timeout)
    except socket.timeout:
        logger.critical('Got timeout after %s seconds.', timeout)
        client_socket = None

    if client_socket:
        message = "user:{0:s}\nhost:{1:s}\nname:{2:s}\nfile:{3:s}\nlout:{4:s}\nstep:{5:s}\n".format(
            user, localhost, env.SMSNAME, output, localout, mstep
        )
        sh.stderr(['client_socket', 'send', message])
        rc = client_socket.send(message)
        client_socket.close()
    else:
        rc = 0
        logger.warning('Could not connect to remote jobout server %s', (swapp_host, swapp_port))

    return rc


def olive_rescue(sh, env, *files):
    """Action to be undertaken when things really went bad."""

    sh.stderr(['olive_rescue', files])

    if 'VORTEX_RESCUE' in env and env.false('VORTEX_RESCUE'):
        logger.warning('Skip olive rescue (VORTEX_RESCUE=%s)', env.VORTEX_RESCUE)
        return False

    if files:
        items = list(files)
    else:
        items = sh.glob('*')

    if 'VORTEX_RESCUE_FILTER' in env:
        select = '|'.join(re.split(r'[,;:]+', env.VORTEX_RESCUE_FILTER))
        items = [ x for x in items if re.search(select, x, re.IGNORECASE) ]
        logger.info('Rescue filter (%s)', select)

    if 'VORTEX_RESCUE_DISCARD' in env:
        select = '|'.join(re.split(r'[,;:]+', env.VORTEX_RESCUE_DISCARD))
        items = [ x for x in items if not re.search(select, x, re.IGNORECASE) ]
        logger.info('Rescue discard (%s)', select)

    if items:

        bkupdir = None

        if env.VORTEX_RESCUE_DIR is not None:
            bkupdir = env.VORTEX_RESCUE_DIR
            logger.info('Rescue user defined backup directory is %s', bkupdir)
        elif env.MTOOL_STEP_ABORT is not None:
            bkupdir = sh.path.join(env.MTOOL_STEP_ABORT, env.MTOOL_STEP_ID)
            logger.info('Rescue mtool defined backup directory is %s', bkupdir)

        if bkupdir is None:
            logger.error('No rescue directory defined.')
        else:
            sh.mkdir(bkupdir)
            mkmove = False

            if env.MTOOL_STEP_SPOOL is not None:
                st1 = sh.stat(env.MTOOL_STEP_SPOOL)
                st2 = sh.stat(bkupdir)
                if st1 and st2 and st1.st_dev == st2.st_dev:
                    mkmove = True
            if mkmove:
                for ritem in items:
                    sh.mv(ritem, sh.path.join(bkupdir, ritem))
            else:
                for ritem in items:
                    sh.rawcp(ritem, sh.path.join(bkupdir, ritem))

    else:
        logger.warning('No item to rescue.')

    return bool(items)
