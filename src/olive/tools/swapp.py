#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re, socket

from vortex.autolog import logdefault as logger


def xplabel(sh, env, tag=None, target=None):
    """Return a nice label string for sms monitoring."""

    label = env.PBS_JOBID or env.SLURM_JOB_ID

    if ( env.MTOOL_STEP and env.MTOOL_STEP_ID ):
        depot = env.MTOOL_STEP_DEPOT or env.MTOOL_STEP_STORE
        renum = re.search('\/mstep_(\d+)', depot)
        num = renum.group(1)
        if ( target == None ):
            label = re.sub('-batch', '', label)
            label = re.sub('^\d+:', '', label)
        else:
            label = re.sub('\D+', '', label)
            label = label + '.' + target
        label = ':'.join(reversed(label.split('.')))
        label = '_'.join((label, 'mtool:' + num, env.MTOOL_STEP_ID))
        if tag:
            label = label + ':' + tag

    return label

def guesslocout(sh, env, output):
    """Keep compatibility with previous versions whithout local filename."""

    login = env.SWAPP_USER or sh.getlogin()

    return re.sub('^.*?/' + login + '/', 'xpout/', output)

def xplocout(sh, env, output, localout=None):
    """Return the local path to OLIVE execution output."""

    if localout == None:
        localout = guesslocout(sh, env, output)

    return sh.path.join(env.HOME, localout)

def xpjobout(sh, env, output, localout=None):
    """Connect to OLIVE daemon in charge of SMS outputs."""

    if localout == None:
        localout = guesslocout(sh, env, output)

    mstep = 'off'

    if ( env.MTOOL_STEP and env.MTOOL_STEP_ID ):
        mstep = 'on'
        depot = env.MTOOL_STEP_DEPOT or env.MTOOL_STEP_STORE
        localout = ':'.join(
            [ x for x in sh.ls(depot + '/step.[0-9][0-9]') if (
                sh.path.exists(x+'.done') and
                int(re.search('\.(\d+)$', x).group(1)) < int(env.MTOOL_STEP)
            ) ]
        )

    localhost = env.SWAPP_TARGET or env.SWAPP_TARGET_HOST or env.TARGET_HOST or sh.hostname
    swapp_user, swapp_host, swapp_port = env.SWAPP_OUTPUT_ID.split(':')
    u_swapp_email = swapp_user + '@' + swapp_host
    user = env.SWAPP_TARGET_LOGNAME or env.TARGET_LOGNAME or env.SWAPP_USER or sh.getlogin();

    timeout = int(env.SWAPP_SOCKET_TIMEOUT) or 10

    try:
        client_socket = socket.create_connection((swapp_host, swapp_port), timeout)
    except socket.timeout:
        logger.critical('Got timeout after %s seconds.', timeout)
        client_socket = None

    if client_socket:
        rc = client_socket.send(
            "user:{0:s}\nhost:{0:s}\nname:{0:s}\nfile:{0:s}\nlout:{0:s}\nstep:{0:s}\n".format(
                user, localhost, env.SMSNAME, output, localout, mstep
            )
        )
        client_socket.close()
    else:
        rc = 0
        logger.warning('Could not connect to remote jobout server %s', (swapp_host, swapp_port))

    return rc
