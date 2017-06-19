#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Net tools.
"""

import abc
import ftplib
import functools
import io
import operator
import re
import random
import socket
import stat
import struct
import time
import urlparse
from datetime import datetime

import footprints
from vortex.util.decorators import nicedeco
from vortex.util.netrc import netrc
from collections import namedtuple

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


def uriparse(uristring):
    """Parse the specified ``uristring`` as a dictionary including keys:

     * scheme
     * netloc
     * port
     * query
     * username
     * password
    """

    (realscheme, other) = uristring.split(':', 1)
    rp = urlparse.urlparse('http:' + other)
    uridict = rp._asdict()
    netloc = uridict['netloc'].split('@', 1)
    hostport = netloc.pop().split(':')
    uridict['netloc'] = hostport.pop(0)
    if hostport:
        uridict['port'] = hostport.pop()
    else:
        uridict['port'] = None
    if netloc:
        userpass = netloc.pop().split(':')
        uridict['username'] = userpass.pop(0)
        if userpass:
            uridict['password'] = userpass.pop()
        else:
            uridict['password'] = None
    else:
        uridict['username'] = None
        uridict['password'] = None
    uridict['scheme'] = realscheme
    uridict['query'] = urlparse.parse_qs(uridict['query'])
    return uridict


def uriunparse(uridesc):
    """Delegates to :mod:`urlparse` the job to unparse the given description (as a dictionary)."""
    return urlparse.urlunparse(uridesc)


@nicedeco
def _ensure_delayedlogin(method):
    """Login if necessary."""

    def opened_method(self, *kargs, **kwargs):
        rc = self._delayedlogin()
        if rc:
            return method(self, *kargs, **kwargs)
        else:
            return rc

    return opened_method


class StdFtp(object):
    """
    Standard wrapper for the crude FTP object from :mod:`ftplib`.
    First argument of the constructor is the calling OS interface.
    """

    def __init__(self, system, hostname, loginretries=5):
        logger.debug('FTP init <host:%s>', hostname)
        self._system = system
        self._closed = True
        self._hostname = hostname
        self._internal_ftplib = None
        self._logname = None
        self._cached_pwd = None
        self._created = datetime.now()
        self._opened = None
        self._deleted = None
        self._loginretries = loginretries
        self._loginretries_sleep = 20

    @property
    def _ftplib(self):
        """Delay the call to 'connect' as much as possible."""
        if self._internal_ftplib is None:
            retry = self._loginretries
            while self._internal_ftplib is None and retry:
                try:
                    self._internal_ftplib = ftplib.FTP(self._hostname)
                except socket.timeout:
                    logger.warning('Timeout error occurred when connecting to the FTP server')
                    self._internal_ftplib = None
                    retry -= 1
                    if not retry:
                        logger.warning('The maximum number of retries (%d) was reached.', self._loginretries)
                        raise
                    logger.warning('Sleeping %d sec. before the next attempt.', self._loginretries_sleep)
                    self.system.sleep(self._loginretries_sleep)
            # self._internal_ftplib.set_debuglevel(2)
        return self._internal_ftplib

    @property
    def host(self):
        """Return the hostname."""
        if self._internal_ftplib is None:
            return self._hostname
        else:
            return self._ftplib.host

    def _delayedlogin(self):
        """Login if it was not already done."""
        if self._closed:
            if self._logname is None or self._cached_pwd is None:
                logger.warning('FTP logname/password must be set first. Use the fastlogin method.')
                return False
            retry = self._loginretries
            rc = False
            while not rc and retry:
                try:
                    rc = self.login(self._logname, self._cached_pwd)
                except ftplib.all_errors as e:
                    logger.warning('An FTP error occurred: %s', str(e))
                    rc = False
                    retry -= 1
                    if not retry:
                        logger.warning('The maximum number of retries (%d) was reached.', self._loginretries)
                        raise
                    logger.warning('Sleeping %d sec. before the next attempt.', self._loginretries_sleep)
                    self.system.sleep(self._loginretries_sleep)
            return rc
        else:
            return True

    def __str__(self):
        """
        Nicely formatted print, built as the concatenation
        of the class full name and `logname` and `length` attributes.
        """
        return '{0:s} | host={1:s} logname={2:s} since={3:s}>'.format(
            repr(self).rstrip('>'),
            self.host,
            self.logname,
            str(self.length)
        )

    def __getattr__(self, key):
        """Gateway to undefined method or attributes if present in ``_ftplib``."""
        actualattr = getattr(self._ftplib, key)
        if callable(actualattr):
            def osproxy(*args, **kw):
                # For most of the native commands, we want autologin to be performed
                if key not in ('set_debuglevel', 'connect'):
                    self._delayedlogin()
                cmd = [key]
                cmd.extend(args)
                cmd.extend(['{0:s}={1:s}'.format(x, str(kw[x])) for x in kw.keys()])
                self.stderr(*cmd)
                return actualattr(*args, **kw)

            osproxy.func_name = key
            osproxy.func_doc = actualattr.__doc__
            setattr(self, key, osproxy)
            return osproxy
        else:
            return actualattr

    @property
    def system(self):
        """Current local system interface."""
        return self._system

    def stderr(self, cmd, *args):
        """Proxy to local system's standard error."""
        self.system.stderr('ftp:' + cmd, *args)

    @property
    def closed(self):
        """Current status of the ftp connection."""
        return self._closed

    @property
    def logname(self):
        """Current logname of the ftp connection."""
        return self._logname

    @property
    def length(self):
        """Length in seconds of the current opened connection."""
        timelength = 0
        try:
            topnow = datetime.now() if self._deleted is None else self._deleted
            timelength = (topnow - self._opened).total_seconds()
        except TypeError:
            logger.warning('Could not evaluate connexion length %s', repr(self))
        return timelength

    def close(self):
        """Proxy to ftplib :meth:`ftplib.FTP.close`."""
        self.stderr('close')
        rc = self._ftplib.close()
        self._internal_ftplib = None
        self._closed = True
        self._deleted = datetime.now()
        return rc

    def login(self, *args):
        """Proxy to ftplib :meth:`ftplib.FTP.login`."""
        self.stderr('login', args[0])
        # kept for debugging, but this exposes the user's password!
        # logger.debug('FTP login <args:%s>', str(args))
        rc = self._ftplib.login(*args)
        if rc:
            self._closed = False
            self._deleted = None
            self._opened = datetime.now()
        else:
            logger.warning('FTP could not login <args:%s>', str(args))
        return rc

    def fastlogin(self, logname, password=None, delayed=True):
        """
        Simple heuristic using actual attributes and/or netrc information to find
        login informations.

        The actual login will be performed later (whenever necessary)
        """
        self.stderr('fastlogin', logname)
        rc = False
        if logname and password:
            self._logname = logname
            self._cached_pwd = password
            rc = True
        else:
            nrc = netrc()
            if nrc:
                auth = nrc.authenticators(self.host, login=logname)
                if not auth:
                    # self.host may be a FQDN, try to guess only the hostname
                    auth = nrc.authenticators(self.host.split('.')[0], login=logname)
                # for backward compatibility: This might be removed one day
                if not auth:
                    auth = nrc.authenticators(self.host)
                if not auth:
                    # self.host may be a FQDN, try to guess only the hostname
                    auth = nrc.authenticators(self.host.split('.')[0])
                # End of backward compatibility section
                if auth:
                    self._logname = auth[0]
                    self._cached_pwd = auth[2]
                    self.stderr('netrc', self._logname)
                    rc = True
                else:
                    logger.warning('netrc lookup failed (%s)', str(auth))
            else:
                logger.warning('unable to fetch .netrc file')
        if not delayed and rc:
            # If one really wants to login...
            rc = self.login(self._logname, self._cached_pwd)
        return bool(rc)

    def netpath(self, remote):
        """The complete qualified net path of the remote resource."""
        return self.logname + '@' + self.host + ':' + remote

    def list(self, *args):
        """Returns standard directory listing from ftp protocol."""
        self.stderr('list', *args)
        contents = []
        self.retrlines('LIST', callback=contents.append)
        return contents

    @_ensure_delayedlogin
    def dir(self, *args):
        """Proxy to ftplib :meth:`ftplib.FTP.login`."""
        self.stderr('dir', *args)
        return self._ftplib.dir(*args)

    def ls(self, *args):
        """Returns directory listing."""
        self.stderr('ls', *args)
        return self.dir(*args)

    ll = ls

    def get(self, source, destination):
        """Retrieve a remote `destination` file to a local `source` file object."""
        self.stderr('get', source, destination)
        if isinstance(destination, basestring):
            self.system.filecocoon(destination)
            target = io.open(destination, 'wb')
            xdestination = True
        else:
            target = destination
            xdestination = False
        logger.info('FTP <get:{:s}>'.format(source))
        rc = False
        try:
            self.retrbinary('RETR ' + source, target.write)
        except (ValueError, TypeError, IOError) as e:
            logger.error('FTP could not get %s: %s', repr(source), str(e))
            raise
        except ftplib.all_errors as e:
            logger.error('FTP internal exception %s: %s', repr(source), str(e))
            raise IOError('FTP could not get %s: %s' % (repr(source), str(e)))
        else:
            if xdestination:
                target.seek(0, io.SEEK_END)
                if self.size(source) == target.tell():
                    rc = True
                else:
                    logger.error('FTP incomplete get %s', repr(source))
            else:
                rc = True
        finally:
            if xdestination:
                target.close()
                # If the ftp GET fails, a zero size file is here: remove it
                if not rc:
                    self.system.remove(destination)
        return rc

    def put(self, source, destination, size=None, exact=False):
        """Store a local `source` file object to a remote `destination`.

           When `size` is known, it is sent to the ftp server with the ALLO
           command. It is mesured in this method for real files, but should
           be given for other (non-seekeable) sources such as pipes.

           When `exact` is True, the size is checked against the size of the
           destination, and a mismatch is considered a failure.
        """
        self.stderr('put', source, destination)
        if isinstance(source, basestring):
            inputsrc = io.open(source, 'rb')
            xsource = True
        else:
            inputsrc = source
            xsource = False
        try:
            inputsrc.seek(0, io.SEEK_END)
            size = inputsrc.tell()
            exact = True
            inputsrc.seek(0)
        except AttributeError:
            logger.warning('Could not rewind <source:%s>', str(source))
        except IOError:
            logger.debug('Seek trouble <source:%s>', str(source))

        self.rmkdir(destination)
        try:
            self.delete(destination)
            logger.warning('Replacing <file:%s>', str(destination))
        except ftplib.error_perm:
            logger.warning('Creating <file:%s>', str(destination))
        except (ValueError, TypeError, IOError,
                ftplib.error_proto, ftplib.error_reply, ftplib.error_temp) as e:
            logger.critical('Serious delete trouble <file:%s> <error:%s>',
                            str(destination), str(e))

        logger.info('FTP <put:%s>', str(destination))
        rc = False

        if size is not None:
            try:
                self.voidcmd('ALLO {:d}'.format(size))
            except ftplib.error_perm:
                pass

        try:
            self.storbinary('STOR ' + destination, inputsrc)
        except (ValueError, IOError, TypeError, ftplib.all_errors) as e:
            logger.error('FTP could not put %s: %s', repr(source), str(e))
        else:
            if exact:
                if self.size(destination) == size:
                    rc = True
                else:
                    logger.error('FTP incomplete put %s (%d / %d bytes)', repr(source),
                                 self.size(destination), size)
            else:
                rc = True
                if self.size(destination) != size:
                    logger.info('FTP put %s: estimated %s bytes, real %s bytes',
                                repr(source), str(size), self.size(destination))
        finally:
            if xsource:
                inputsrc.close()
        return rc

    def rmkdir(self, destination):
        """Recursive directory creation."""
        self.stderr('rmkdir', destination)
        origin = self.pwd()
        if destination.startswith('/'):
            path_pre = '/'
        elif destination.startswith('~'):
            path_pre = ''
        else:
            path_pre = origin + '/'

        for subdir in self.system.path.dirname(destination).split('/'):
            current = path_pre + subdir
            try:
                self.cwd(current)
                path_pre = current + '/'
            except ftplib.error_perm:
                self.stderr('mkdir', current)
                try:
                    self.mkd(current)
                except ftplib.error_perm as errmkd:
                    if 'File exists' not in str(errmkd):
                        raise
                self.cwd(current)
            path_pre = current + '/'
        self.cwd(origin)

    def cd(self, destination):
        """Change to a directory."""
        return self.cwd(destination)

    def rm(self, source):
        """Proxy to ftp delete command."""
        return self.delete(source)

    def size(self, filename):
        """Retrieve the size of a file."""
        # The SIZE command is defined in RFC-3659
        resp = self.sendcmd('SIZE ' + filename)
        if resp[:3] == '213':
            s = resp[3:].strip().split()[-1]
            try:
                return int(s)
            except (OverflowError, ValueError):
                return long(s)


class Ssh(object):
    """Remote command execution via ssh.

    Also handles remote copy via scp or ssh, which is intimately linked
    """
    def __init__(self, sh, hostname, logname=None, sshopts=None, scpopts=None):
        """
        :param System sh: The :class:`System` object that is to be used.
        :param str hostname: The target hostname(s).
        :param logname: The logname for the Ssh commands.
        :param str sshopts: Extra SSH options (in addition of the configuration
                            file ones).
        :param str scpopts: Extra SCP options (in addition of the configuration
                            file ones).
        """
        self._sh = sh

        self._logname = logname
        self._remote = hostname

        target = sh.default_target
        self._sshcmd = target.get(key='services:sshcmd', default='ssh')
        self._scpcmd = target.get(key='services:scpcmd', default='scp')
        self._sshopts = (
            target.get(key='services:sshopts', default='-x').split() +
            target.get(key='services:sshretryopts', default='').split() +
            (sshopts or '').split())
        self._scpopts = (
            target.get(key='services:scpopts', default='-Bp').split() +
            target.get(key='services:scpretryopts', default='').split() +
            (scpopts or '').split())

    @property
    def sh(self):
        return self._sh

    @property
    def remote(self):
        return ('' if self._logname is None else self._logname + '@') + self._remote

    def check_ok(self):
        """Is the connexion ok ?"""
        return self.execute('true') is not False

    @staticmethod
    def quote(s):
        """Quote a string so that it can be used as an argument in a posix shell."""
        try:
            # py3
            from shlex import quote
        except ImportError:
            # py2
            from pipes import quote
        return quote(s)

    def execute(self, remote_command, sshopts=''):
        """Execute the command remotely.

        Return the output of the command (list of lines), or False on error.

        Only the output sent to the log (when silent=False) shows the difference
        between:

        - a bad connection (e.g. wrong user)
        - a remote command retcode != 0 (e.g. cmd='/bin/false')

        """
        myremote = self.remote
        if myremote is None:
            return False
        cmd = ([self._sshcmd, ] +
               self._sshopts + sshopts.split() +
               [myremote, ] + [remote_command, ])
        return self.sh.spawn(cmd, output=True, fatal=False)

    def cocoon(self, destination):
        """Create the remote directory to contain ``destination``.
           Return False on failure.
        """
        remote_dir = self.sh.path.dirname(destination)
        if remote_dir == '':
            return True
        logger.debug('Cocooning remote directory "%s"', remote_dir)
        cmd = 'mkdir -p "{}"'.format(remote_dir)
        rc = self.execute(cmd)
        if not rc:
            logger.error('Cannot cocoon on %s (user: %s) for %s',
                         str(self._remote), str(self._logname), destination)
        return rc

    def remove(self, target):
        """Remove the remote target, if present. Return False on failure.

        Does not fail when the target is missing, but does when it exists
        and cannot be removed, which would make a final move also fail.
        """
        logger.debug('Removing remote target "%s"', target)
        cmd = 'rm -fr "{}"'.format(target)
        rc = self.execute(cmd)
        if not rc:
            logger.error('Cannot remove from %s (user: %s) item "%s"',
                         str(self._remote), str(self._logname), target)
        return rc

    def _scp_putget_commons(self, source, destination):
        """Common checks on source and destination."""
        if not isinstance(source, basestring):
            msg = 'Source is not a plain file path: {!r}'.format(source)
            raise TypeError(msg)
        if not isinstance(destination, basestring):
            msg = 'Destination is not a plain file path: {!r}'.format(destination)
            raise TypeError(msg)

        # avoid special cases
        if destination == '' or destination == '.':
            destination = './'
        else:
            if destination.endswith('..'):
                destination += '/'
            if '../' in destination:
                raise ValueError('"../" is not allowed in the destination path')
        if destination.endswith('/'):
            destination = self.sh.path.join(destination, self.sh.path.basename(source))

        return source, destination

    def scpput(self, source, destination, scpopts=''):
        """Send ``source`` to ``destination``.

        - ``source`` is a single file or a directory, not a pattern (no '\*.grib').
        - ``destination`` is the remote name, unless it ends with '/', in
          which case it is the containing directory, and the remote name is
          the basename of ``source`` (like a real cp or scp):

            - ``scp a/b.gif c/d.gif --> c/d.gif``
            - ``scp a/b.gif c/d/    --> c/d/b.gif``

        Return True for ok, False on error.
        """
        source, destination = self._scp_putget_commons(source, destination)

        if not self.sh.path.exists(source):
            logger.error('No such file or directory: %s', source)
            return False

        source = self.sh.path.realpath(source)

        myremote = self.remote
        if myremote is None:
            return False

        if not self.cocoon(destination):
            return False

        isadir = self.sh.path.isdir(source)
        if isadir:
            if not self.remove(destination):
                return False
            scpopts += ' -r'

        # transfer to a temporary place.
        # when ``destination`` contains spaces, 1 round of quoting
        # is necessary, to avoid an 'scp: ambiguous target' error.
        cmd = ([self._scpcmd, ] +
               self._scpopts + scpopts.split() +
               [source,
                myremote + ':' + self.quote(destination + '.tmp')])
        rc = self.sh.spawn(cmd, output=False, fatal=False)
        if rc:
            # success, rename the tmp
            rc = self.execute('mv "{0}.tmp" "{0}"'.format(destination))
        return rc

    def scpget(self, source, destination, scpopts='', isadir=False):
        """Send ``source`` to ``destination``.

        - ``source`` is the remote name, not a pattern (no '\*.grib').
        - ``destination`` is a single file or a directory, unless it ends with
          '/', in which case it is the containing directory, and the remote name
          is the basename of ``source`` (like a real cp or scp):

            - ``scp a/b.gif c/d.gif --> c/d.gif``
            - ``scp a/b.gif c/d/    --> c/d/b.gif``

        Return True for ok, False on error.
        """
        source, destination = self._scp_putget_commons(source, destination)

        myremote = self.remote
        if myremote is None:
            return False

        if not self.sh.filecocoon(destination):
            return False

        if isadir:
            if not self.sh.remove(destination):
                return False
            scpopts += ' -r'

        # transfer to a temporary place.
        # when ``source`` contains spaces, 1 round of quoting
        # is necessary, to avoid an 'scp: ambiguous target' error.
        cmd = ([self._scpcmd, ] +
               self._scpopts + scpopts.split() +
               [myremote + ':' + self.quote(source),
                destination + '.tmp'])
        rc = self.sh.spawn(cmd, output=False, fatal=False)
        if rc:
            # success, rename the tmp
            rc = self.sh.move(destination + '.tmp', destination)
        return rc

    def get_permissions(self, source):
        """Convenience method to retrieve the permissions
           of a file/dir (in a form suitable for chmod).
        """
        mode = self.sh.stat(source).st_mode
        return stat.S_IMODE(mode)

    def scpput_stream(self, stream, destination, permissions=None, sshopts=''):
        """Send the ``stream`` to the ``destination``.

        - ``stream`` is a ``file`` (typically returned by open(),
          or the piped output of a spawned process).
        - ``destination`` is the remote file name.

        Return True for ok, False on error.
        """
        if not isinstance(stream, file):
            msg = "stream is a {}, should be a <type 'file'>".format(type(stream))
            raise TypeError(msg)

        if not isinstance(destination, basestring):
            msg = 'Destination is not a plain file path: {!r}'.format(destination)
            raise TypeError(msg)

        myremote = self.remote
        if myremote is None:
            return False

        if not self.cocoon(destination):
            return False

        # transfer to a tmp, rename and set permissions in one go
        remote_cmd = 'cat > {0}.tmp && mv {0}.tmp {0}'.format(self.quote(destination))
        if permissions:
            remote_cmd += ' && chmod -v {} {}'.format(oct(permissions), self.quote(destination))

        cmd = ([self._sshcmd, ] +
               self._sshopts + sshopts.split() +
               [myremote, remote_cmd])
        return self.sh.spawn(cmd, stdin=stream, output=False, fatal=False)

    def scpget_stream(self, source, stream, sshopts=''):
        """Send the ``source`` to the ``stream``.

        - ``source`` is the remote file name.
        - ``stream`` is a ``file`` (typically returned by open(),
          or the piped output of a spawned process).

        Return True for ok, False on error.
        """
        if not isinstance(stream, file):
            msg = "stream is a {}, should be a <type 'file'>".format(type(stream))
            raise TypeError(msg)

        if not isinstance(source, basestring):
            msg = 'Source is not a plain file path: {!r}'.format(source)
            raise TypeError(msg)

        myremote = self.remote
        if myremote is None:
            return False

        # transfer to a tmp, rename and set permissions in one go
        remote_cmd = 'cat {0}'.format(self.quote(source))
        cmd = ([self._sshcmd, ] +
               self._sshopts + sshopts.split() +
               [myremote, remote_cmd])
        return self.sh.spawn(cmd, output=stream, fatal=False)

    def tunnel(self, finaldestination, finalport, entranceport=None,
               maxwait=5., checkdelay=0.25):
        """Create an SSH tunnel and check that it actually starts.

        :param str finaldestination: the destination hostname (i.e the machine
                                     at the far end of the tunnel)
        :param int finalport: the destination port
        :param int entranceport: the port number of the tunnel entrace (if None,
                                 which is the default, it is automatically
                                 assigned)
        :param float maxwait: The maximum time to wait for the entrance port to
                              be opened by the SSH client (if the entrance port
                              is not ready by that time, the SSH command is
                              considered to have failed).
        :return: False if the tunnel command failed, otherwise an object that
                 contains all kind of details on the SSH tunnel.
        :rtype: ActiveSshTunnel
        """

        myremote = self.remote
        if myremote is None:
            return False

        if entranceport is None:
            entranceport = self.sh.available_localport()
        else:
            if self.sh.check_localport(entranceport):
                logger.error('The SSH tunnel creation failed ' +
                             '(entrance: %d, dest: %s:%d, via %s).',
                             entranceport, finaldestination, finalport, myremote)
                logger.error('The entrance port is already in use.')
                return False

        p = self.sh.popen([self._sshcmd, ] + self._sshopts +
                          ['-N', '-L',
                           '{:d}:{:s}:{:d}'.format(entranceport,
                                                   finaldestination, finalport),
                           myremote],
                          stdin   = False, output  = False)
        tunnel = ActiveSshTunnel(self.sh, p, entranceport, finaldestination, finalport)
        elapsed = 0.
        while (not self.sh.check_localport(entranceport)) and elapsed < maxwait:
            self.sh.sleep(checkdelay)
            elapsed += checkdelay
        if not self.sh.check_localport(entranceport):
            logger.error('The SSH tunnel creation failed ' +
                         '(entrance: %d, dest: %s:%d, via %s).',
                         entranceport, finaldestination, finalport, myremote)
            tunnel.close()
            tunnel = False
        logger.info('SSH tunnel opened, enjoy the ride ! ' +
                    '(entrance: %d, dest: %s:%d, via %s).',
                    entranceport, finaldestination, finalport, myremote)
        return tunnel


class ActiveSshTunnel(object):
    """Hold an opened SSH tunnel."""

    def __init__(self, sh, activeprocess, entraceport, finaldestination, finalport):
        """
        :param Popen activeprocess: The active tunnel process.
        :param int entraceport: Tunnel's entrance port.
        :param str finaldestination: Tunnel's final destination.
        :param int finalport: Tunnel's destination port.

        Objects of this class can be used as context managers (the tunnel will
        be closed when the context is exited).
        """
        self._sh = sh
        self.activeprocess = activeprocess
        self.entraceport = entraceport
        self.finaldestination = finaldestination
        self.finalport = finalport

    def __del__(self):
        self.close()

    def close(self):
        """Close the tunnel (i.e. kill the SSH process)."""
        if self.opened:
            self.activeprocess.terminate()
            t0 = time.time()
            while self.opened and time.time() - t0 < 5:
                self._sh.sleep(0.1)
            logger.debug("Tunnel termination took: %f seconds", time.time() - t0)
            if self.opened:
                logger.debug("Tunnel termination failed: issuing SIGKILL")
                self.activeprocess.kill()

    @property
    def opened(self):
        """Is the tunnel oppened ?"""
        return self.activeprocess.poll() is None

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


@nicedeco
def _check_fatal(func):
    """decorator: an exception is raised, if fatal=True and the returncode != True.

    This decorator is very specialised and should be used solely with the AssistedSsh
    class since it relies on several attributes (_fatal, _maxtries).
    """
    def wrapped(*args, **kwargs):
        self = args[0]
        if self._fatal_in_progress:
            return func(self, *args[1:], **kwargs)
        else:
            # This trick ensure that only one fatal check is attempted
            self._fatal_in_progress = True
            try:
                rc = func(self, *args[1:], **kwargs)
                if not rc:
                    logger.error("The maximum number of retries (%s) was reached...", self._maxtries)
                    if self._fatal:
                        raise RuntimeError("Could not execute the SSH command.")
            finally:
                self._fatal_in_progress = False
            return rc
    return wrapped


@nicedeco
def _tryagain(func):
    """decorator: whenever the return code != True, several are made according to self._maxtries.

    This decorator is very specialised and should be used solely with the AssistedSsh
    class since it relies on several attributes (_retry_in_progress, _retries, _maxtries).
    """
    def wrapped(*args, **kwargs):
        self = args[0]
        if self._retry_in_progress:
            return func(self, *args[1:], **kwargs)
        else:
            # This trick ensure that only one retry loop is attempted
            self._retry_in_progress = True
            trycount = 1
            try:
                rc = func(self, *args[1:], **kwargs)
                while not rc and trycount < self._maxtries:
                    trycount += 1
                    logger.info("Trying again (retries=%d/%d)...", trycount, self._maxtries)
                    self.sh.sleep(self._triesdelay)
                    rc = func(self, *args[1:], **kwargs)
            finally:
                self._retries = trycount
                self._retry_in_progress = False
            return rc
    return wrapped


class _AssistedSshMeta(type):
    """Specialized metaclass for AssitedSsh."""

    def __new__(cls, n, b, d):
        """Adds _tryagain and _check_fatal decorators on a list of inherited methods.

        This is controled by two class variables:

        - _auto_retries: list of inherited methods that should be decorated
          with _tryagin
        - _auto_checkfatal: list of inherited methods that should be
          decorated with _check_fatal

        Note: it only acts on inherited methods. For overridden methods,
        decorators have to be added manually.
        """
        bare_methods = list(d.keys())
        # Add the tryagain decorator...
        for tagain in [x for x in d['_auto_retries'] if x not in bare_methods]:
            inherited = [base for base in b if hasattr(base, tagain)]
            d[tagain] = _tryagain(getattr(inherited[0], tagain))
        # Add the check_fatal decorator...
        for cfatal in [x for x in d['_auto_checkfatal'] if x not in bare_methods]:
            inherited = [base for base in b if hasattr(base, cfatal)]
            d[cfatal] = _check_fatal(d.get(cfatal, getattr(inherited[0], cfatal)))
        return super(_AssistedSshMeta, cls).__new__(cls, n, b, d)


class AssistedSsh(Ssh):
    """Remote command execution via ssh.

    Also handles remote copy via scp or ssh, which is intimately linked. Compared
    too the :class:`Ssh` class it adds:

    - retries capabilities
    - support for multiple hostnames (a hostname is picked up in the hostnames
      list, it is tested and if the test succeed it is chosen. If not, the next
      hostname is tested, ... and so on).
    - virtual nodes support (i.e. the real hostnames associated with a virtual
      node name are read in the configuration file).
    """

    _auto_checkfatal = ['check_ok', 'execute', 'cocoon', 'remove',
                        'scpput', 'scpget', 'scpput_stream', 'scpget_stream',
                        'tunnel']
    # No retries on scpput_stream since it's not guaranteed that the stream is seekable.
    _auto_retries = ['check_ok', 'execute', 'cocoon', 'remove',
                     'scpput', 'scpget', 'tunnel']

    __metaclass__ = _AssistedSshMeta

    def __init__(self, sh, hostname, logname=None, sshopts=None, scpopts=None,
                 maxtries=1, triesdelay=1, virtualnode=False, permut=True,
                 fatal=False, mandatory_hostcheck=False):
        """
        :param System sh: The :class:`System` object that is to be used.
        :param hostname: The target hostname(s).
        :type hostname: str or list
        :param logname: The logname for the Ssh commands.
        :param str sshopts: Extra SSH options (in addition of the configuration
                            file ones).
        :param str scpopts: Extra SCP options (in addition of the configuration
                            file ones).
        :param int maxtries: The maximum number of retries.
        :param int triesdelay: The delay in seconds between retries.
        :param bool virtualnode: If True, the *hostname* is considered to be a
                                 virtual node name. It is therefore looked up in
                                 the configuration file.
        :param bool permut: If True, the hostnames list is shuffled prior to
                            being used.
        :param bool fatal: If True, a RuntimeError exception is raised whenever
                           something fails.
        :param mandatory_hostcheck: If True, the hostname is always checked
                                    prior to being used for the real Ssh command.
        """
        super(AssistedSsh, self).__init__(sh, hostname, logname, sshopts, scpopts)
        self._maxtries = maxtries
        self._triesdelay = triesdelay
        self._virtualnode = virtualnode
        self._permut = permut
        self._fatal = fatal
        self._mandatory_hostcheck = mandatory_hostcheck
        if self._virtualnode and isinstance(self._remote, (list, tuple)):
            raise ValueError('When virtual nodes are used, the hostname must be a string')

        self._retry_in_progress = False
        self._fatal_in_progress = False
        self._retries = 0
        self._targets = self._setup_targets()
        self._chosen_target = None

    def _setup_targets(self):
        """Build the actual hostnames list."""
        if self._virtualnode:
            targets = self.sh.default_target.specialproxies[self._remote]
        else:
            if isinstance(self._remote, (list, tuple)):
                targets = self._remote
            else:
                targets = [self._remote]
        if self._logname is not None:
            targets = [self._logname + '@' + x for x in targets]
        if self._permut:
            random.shuffle(targets)
        return targets

    @property
    def targets(self):
        """The actual hostnames list."""
        return self._targets

    @property
    def retries(self):
        """The number of tries made for the last Ssh command."""
        return self._retries

    @property
    @_check_fatal
    @_tryagain
    def remote(self):
        """hostname to use for this kind of remote execution."""
        if len(self.targets) == 1 and not self._mandatory_hostcheck:
            # This is simple enough, do not bother testing...
            self._chosen_target = self.targets[0]
        if self._chosen_target is None:
            for guess in self.targets:
                cmd = [self._sshcmd, ] + self._sshopts + [guess, 'true', ]
                try:
                    self.sh.spawn(cmd, output=False, silent=True)
                except StandardError:
                    pass
                else:
                    self._chosen_target = guess
                    break
        return self._chosen_target


_ConnectionStatusAttrs = ('Family', 'LocalAddr', 'LocalPort', 'DestAddr', 'DestPort', 'Status')
TcpConnectionStatus = namedtuple('TcpConnectionStatus', _ConnectionStatusAttrs)
UdpConnectionStatus = namedtuple('UdpConnectionStatus', _ConnectionStatusAttrs)


class AbstractNetstats(object):
    """AbstractNetstats classes provide all kind of informations on network connections."""

    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def unprivileged_ports(self):
        """The list of unprivileged port that may be opened by any user."""
        pass

    @abc.abstractmethod
    def tcp_netstats(self):
        """Informations on active TCP connections (returns a list of
        :class:`TcpConnectionStatus` objects.)"""
        pass

    @abc.abstractmethod
    def udp_netstats(self):
        """Informations on active UDP connections (returns a list of
        :class:`UdpConnectionStatus` objects.)"""
        pass

    def available_localport(self):
        """Returns the number of an unused unprivileged port."""
        netstats = self.tcp_netstats() + self.udp_netstats()
        busyports = set([x.LocalPort for x in netstats])
        busy = True
        while busy:
            guess_port = random.choice(self.unprivileged_ports)
            busy = guess_port in busyports
        return guess_port

    def check_localport(self, port):
        """Check if ``port`` is currently in use."""
        netstats = self.tcp_netstats() + self.udp_netstats()
        busyports = set([x.LocalPort for x in netstats])
        return port in busyports


class LinuxNetstats(AbstractNetstats):
    """A Netstats implemenetation for Linux (based on the /proc/net data)."""

    def __init__(self):
        self.__unprivileged_ports = None

    @property
    def unprivileged_ports(self):
        if self.__unprivileged_ports is None:
            with open('/proc/sys/net/ipv4/ip_local_port_range', 'r') as tmprange:
                tmpports = [int(x) for x in tmprange.readline().split()]
            unports = set(range(5001, 65536))
            self.__unprivileged_ports = sorted(unports - set(range(tmpports[0], tmpports[1] + 1)))
        return self.__unprivileged_ports

    @staticmethod
    def _ip_from_hex(hexip, family=socket.AF_INET):
        if family == socket.AF_INET:
            packed = struct.pack("<I", int(hexip, 16))
        elif family == socket.AF_INET6:
            packed = struct.unpack(">IIII", hexip.decode('hex'))
            packed = struct.pack("@IIII", * packed)
        else:
            raise ValueError("Unknown address family.")
        return socket.inet_ntop(family, packed)

    def _generic_netstats(self, proto, rclass):
        tmpports = dict()
        with open('/proc/net/{:s}'.format(proto), 'r') as netstats:
            netstats.readline()  # Skip the header line
            tmpports[socket.AF_INET] = [re.split(r':\b|\s+', x.strip())[1:6]
                                        for x in netstats.readlines()]
        with open('/proc/net/{:s}6'.format(proto), 'r') as netstats:
            netstats.readline()  # Skip the header line
            tmpports[socket.AF_INET6] = [re.split(r':\b|\s+', x.strip())[1:6]
                                         for x in netstats.readlines()]
        tmpports = [[rclass(family,
                            self._ip_from_hex(l[0], family), int(l[1], 16),
                            self._ip_from_hex(l[2], family), int(l[3], 16),
                            int(l[4], 16)) for l in tmpports[family]]
                    for family in (socket.AF_INET, socket.AF_INET6)]
        return functools.reduce(operator.add, tmpports)

    def tcp_netstats(self):
        return self._generic_netstats('tcp', TcpConnectionStatus)

    def udp_netstats(self):
        return self._generic_netstats('udp', UdpConnectionStatus)
