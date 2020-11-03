#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Various tools to interact with the SWAPP system.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import contextlib
import six
import io
import re
import socket
import string
import uuid
import tempfile

from bronx.datagrip import namelist as fortran
from bronx.fancies import loggers

from vortex import sessions
from vortex.util import config
from vortex.data import geometries
from common.data.namelists import KNOWN_NAMELIST_MACROS

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

STEPFILE_MAX_SIZE = 2097152  # 2Mb


def olive_label(sh, env, target=None):
    """Return a nice label string for sms monitoring."""

    label = env.PBS_JOBID or env.SLURM_JOB_ID or 'localpid'

    if label == 'localpid':
        label = six.text_type(sh.getpid())

    if env.MTOOL_STEP:
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
        label = '--'.join((label, 'mtool:' + num))

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


def _olive_jobout_sizecontrol(sh, stepfile, directory=None, extrasuffix=''):
    fullstepfile = sh.path.join(directory, stepfile) if directory else stepfile
    fullstepfile = sh.path.expanduser(fullstepfile)
    mysize = sh.size(fullstepfile + extrasuffix)
    if mysize > STEPFILE_MAX_SIZE:
        tpl = config.load_template(sessions.current(),
                                   '@olive-swapp-file2big.tpl')
        with io.open(fullstepfile + '.oversized' + extrasuffix, 'w') as fd:
            fd.write(tpl.substitute(
                filename=fullstepfile + extrasuffix,
                mysize='{:.1f}'.format(mysize / 1024. / 1024.),
                sizelimit='{:.1f}'.format(STEPFILE_MAX_SIZE / 1024. / 1024.))
            )
        return stepfile + '.oversized'
    else:
        return stepfile


def olive_jobout(sh, env, output, localout=None, mode='socket'):
    """Connect to OLIVE daemon in charge of SMS outputs."""

    logger.info('Prepare output <%s> at localout <%s>', output, str(localout))

    if localout is None:
        localout = guesslocout(sh, env, output)

    mstep = 'off'

    if 'MTOOL_STEP' in env and env.MTOOL_STEP_ID:
        mstep = 'on'
        depot = env.MTOOL_STEP_DEPOT or env.MTOOL_STEP_STORE
        localout = ':'.join(
            [_olive_jobout_sizecontrol(sh, x, extrasuffix='.out')
             for x in sh.ls(depot + '/step.[0-9][0-9]')
             if (sh.path.exists(x + '.done') and
                 int(re.search(r'\.(\d+)$', x).group(1)) < int(env.MTOOL_STEP))]
        )
    else:
        localout = _olive_jobout_sizecontrol(sh, localout, directory='~')

    if mode == 'socket':
        return olive_jobout_socketsend(sh, env, output, mstep, localout)
    elif mode == 'fullsocket':
        return olive_jobout_fullsocketsend(sh, env, output, mstep, localout)
    elif mode == 'ectrans':
        return olive_jobout_ectranssend(sh, env, output, mstep, localout)
    else:
        raise NotImplementedError('mode "{:s}" is not implemented'.format(mode))


def _olive_jobout_getsocket(sh, env):
    """Send the request to joboutd using a socket."""
    localhost = sh.default_target.inetname
    _, swapp_host, swapp_port = env.VORTEX_OUTPUT_ID.split(':')
    user = env.VORTEX_TARGET_LOGNAME or env.TARGET_LOGNAME or env.SWAPP_USER or sh.getlogin()

    if 'VORTEX_SOCKET_TIMEOUT' in env:
        timeout = int(env.VORTEX_SOCKET_TIMEOUT)
    else:
        timeout = 10

    try:
        client_socket = socket.create_connection((str(swapp_host), str(swapp_port)), timeout)
    except socket.timeout:
        logger.critical('Got timeout after %s seconds.', timeout)
        logger.warning('Could not connect to remote jobout server %s', (swapp_host, swapp_port))
        client_socket = None

    return client_socket, user, localhost


def olive_jobout_socketsend(sh, env, output, mstep, localout):
    """Send the request to joboutd using a socket."""
    client_socket, user, localhost = _olive_jobout_getsocket(sh, env)
    rc = 0
    if client_socket:
        message = "user:{0:s}\nhost:{1:s}\nname:{2:s}\nfile:{3:s}\nlout:{4:s}\nstep:{5:s}\n".format(
            user, localhost, env.SMSNAME, output, localout, mstep
        ).encode('ascii', 'replace')
        sh.stderr(['client_socket', 'send', str(message)])
        client_socket.sendall(message)
        rc = 1
        client_socket.close()
    return rc


def olive_jobout_fullsocketsend(sh, env, output, mstep, localout):
    """Send the request to joboutd using a socket."""
    # What are the output files ?
    stepfiles = localout.split(':')
    if mstep == 'on':
        stepfiles = [s + '.out' for s in stepfiles]
    stepfiles_fh = list()
    stepfiles_size = 0
    try:
        # Open all file in read mode and accumulate their sizes
        for stepfile in stepfiles:
            stepfile_fh = io.open(stepfile, 'rb')
            stepfiles_fh.append(stepfile_fh)
            stepfiles_size += stepfile_fh.seek(0, io.SEEK_END)
            stepfile_fh.seek(0, io.SEEK_SET)
        # Create the socket
        client_socket, user, localhost = _olive_jobout_getsocket(sh, env)
        rc = 0
        if client_socket:
            # Send the header
            message = "user:{0:s}\nhost:{1:s}\nname:{2:s}\nfile:{3:s}\nlout:{4:s}\nstep:{5:d}\n".format(
                user, localhost, env.SMSNAME, output, 'socket', stepfiles_size
            ).encode('ascii', 'replace')
            sh.stderr(['client_socket', 'send', str(message)])
            client_socket.sendall(message)
            # Send data to the socket
            chunksize = 64 * 1024  # 64Ko
            for stepfile_fh in stepfiles_fh:
                sdata = stepfile_fh.read(chunksize)
                while sdata:
                    client_socket.sendall(sdata)
                    sdata = stepfile_fh.read(chunksize)
            rc = 1
            client_socket.close()
    finally:
        for stepfile_fh in stepfiles_fh:
            stepfile_fh.close()
    return rc


def olive_jobout_ectranssend(sh, env, output, mstep, localout):
    """Send the request to updsmsd using ectrans."""
    if 'ectrans' not in sh.loaded_addons():
        raise RuntimeError('The ectrans addon needs to be loaded !')
    if 'VORTEX_UPDSERVER_HOST' not in env:
        raise RuntimeError('The VORTEX_UPDSERVER_HOST variable needs to be defined')
    if 'VORTEX_UPDSERVER_PATH' not in env:
        raise RuntimeError('The VORTEX_UPDSERVER_PATH variable needs to be defined')
    if 'VORTEX_OUTPUT_ID' not in env:
        raise RuntimeError('The VORTEX_OUTPUT_ID variable needs to be defined')
    _, swapp_host, swapp_port = env.VORTEX_OUTPUT_ID.split(':')

    stepfiles = localout.split(':')
    if mstep == 'on':
        stepfiles = [s + '.out' for s in stepfiles]
    with tempfile.NamedTemporaryFile('wb', prefix='jobout_send.') as fhdir:
        # Create the directive file...
        fhdir.write((output + "\n").encode())
        fhdir.write(("{:s}:{:s}\n".format(swapp_host, swapp_port)).encode())
        fhdir.write("void_password\n".encode())
        for stepfile in stepfiles:
            with io.open(stepfile, 'rb') as fhstep:
                fhdir.write(fhstep.read() + b"\n")
        fhdir.flush()

        remote = sh.ectrans_remote_init(storage=env.VORTEX_UPDSERVER_HOST)
        gateway = sh.ectrans_gateway_init()
        return sh.raw_ectransput(source=fhdir.name,
                                 target=sh.path.join(env.VORTEX_UPDSERVER_PATH,
                                                     'jobout.' + uuid.uuid4().hex),
                                 gateway=gateway, remote=remote,
                                 priority=90, retryCnt=5, retryFrq=180, sync=False)


def olive_enforce_oneshot(identifier):
    """Return True only once. This is rather crude..."""
    t = sessions.current()
    flag = 'olive_oneshot_flag_{!s}'.format(identifier)
    go = not t.sh.path.exists(flag)
    t.sh.touch(flag)
    return go


@contextlib.contextmanager
def _olive_readonly_gnam_context(sh, container):
    """If the container is readonly, move the file first."""
    is_readonly = (isinstance(container.iotarget(), six.string_types) and
                   not sh.wperm(container.localpath()))
    if is_readonly:
        tmp_ro_file = container.localpath() + sh.safe_filesuffix()
        sh.move(container.localpath(), tmp_ro_file)
        try:
            yield
            sh.readonly(container.localpath())
        except Exception:
            sh.move(tmp_ro_file, container.localpath())
            raise
        else:
            sh.rm(tmp_ro_file)
    else:
        yield


def olive_gnam_hook_factory(nickname, nam_delta, env=None):
    """Hook functions factory to apply namelist delta on a given ressource."""
    if env is not None:
        # If an Environment object is given: try to substitute variable
        nam_delta = string.Template(nam_delta).substitute(env)

    try:
        namdelta_l = fortran.namparse(nam_delta, macros=KNOWN_NAMELIST_MACROS)
    except ValueError:
        logger.critical("Error while parsing the following namelist delta:\n%s",
                        nam_delta)
        raise

    def olive_gnam_hook(t, namrh):
        t.sh.subtitle('Applying the following namelist patch {} '
                      'to namelist {}'.format(nickname, namrh.container.localpath()))
        print(namdelta_l.dumps())
        namrh.contents.merge(namdelta_l)
        with _olive_readonly_gnam_context(t.sh, namrh.container):
            namrh.save()

    return olive_gnam_hook


def olive_generic_hook_factory(body):
    """User-defined hook functions factory."""
    lines = body.split("\n")
    # Remove a possibly blank first line
    if re.match(r'^\s*$', lines[0]):
        del lines[0]
    # If the first line is indented, that's wrong => dedent
    imatch = re.match(r'^(\s+)', lines[0])
    ilen = len(imatch.group(1)) if imatch else 0
    body = "\n".join([line[ilen:] for line in lines])
    bytecode = compile(body, '<string>', 'exec')

    def olive_generic_hook(t, rh):
        # Create a jail for the environment...
        localenv = t.env.clone()
        localenv.verbose(True, t.sh)
        with localenv:
            jail = dict(t=t, rh=rh, sh=t.sh, env=localenv, )
            six.exec_(bytecode, jail)

    return olive_generic_hook


def olive_new_geometry(tag, kind, **kw):
    """Add on-the-fly new geometries."""
    g_constructor = getattr(geometries, kind[0].upper() + kind[1:] + 'Geometry')
    g = g_constructor(tag=tag, new=True, **kw)
    print('!!! New geometry to be added to geometries.ini:')
    print(g.to_inifile())
