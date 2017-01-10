#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Net tools.
"""

import urlparse
import io, ftplib
from netrc import netrc
from datetime import datetime
import socket

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.util.decorators import nicedeco


#: No automatic export
__all__ = []


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

    def __init__(self, system, hostname, loginretries=3):
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
        self._loginretries_sleep = 5

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
                    retry -= 1
                    if not retry:
                        raise
                    self.system.sleep(self._loginretries_sleep)
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
                except (ftplib.error_temp, ftplib.error_proto) as e:
                    logger.warning('An FTP error occurred: %s', str(e))
                    retry -= 1
                    if not retry:
                        raise
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
                cmd.extend([ '{0:s}={1:s}'.format(x, str(kw[x])) for x in kw.keys() ])
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
            timelength = ( topnow - self._opened ).total_seconds()
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
        logger.debug('FTP login <args:%s>', str(args))
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
                auth = nrc.authenticators(self.host)
                if not auth:
                    # self.host may be a FQDN, try to guess only the hostname
                    auth = nrc.authenticators(self.host.split('.')[0])
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
            raise IOError('FTP could not get %s: %s', repr(source), str(e))
        else:
            if xdestination:
                target.seek(0, 2)
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

    def put(self, source, destination):
        """Store a local `source` file object to a remote `destination`."""
        self.stderr('put', source, destination)
        if isinstance(source, basestring):
            inputsrc = io.open(source, 'rb')
            xsource = True
        else:
            inputsrc = source
            try:
                inputsrc.seek(0)
            except AttributeError:
                logger.warning('Could not rewind <source:%s>', str(source))
            except IOError:
                logger.debug('Seek trouble <source:%s>', str(source))
            xsource = False
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
        try:
            self.storbinary('STOR ' + destination, inputsrc)
        except (ValueError, IOError, TypeError, ftplib.all_errors) as e:
            logger.error('FTP could not put %s: %s', repr(source), str(e))
        else:
            if xsource:
                inputsrc.seek(0, 2)
                if self.size(destination) == inputsrc.tell():
                    rc = True
                else:
                    logger.error('FTP incomplete put %s', repr(source))
            else:
                rc = True
        finally:
            if xsource:
                inputsrc.close()
        return rc

    def rmkdir(self, destination):
        """Recursive directory creation."""
        self.stderr('rmkdir', destination)
        origin = self.pwd()
        if destination.startswith('/'):
            path = ''
        else:
            path = origin

        for subdir in self.system.path.dirname(destination).split('/'):
            current = path + '/' + subdir
            try:
                self.cwd(current)
                path = current
            except ftplib.error_perm:
                self.stderr('mkdir', current)
                try:
                    self.mkd(current)
                except ftplib.error_perm as errmkd:
                    if 'File exists' not in str(errmkd):
                        raise
                self.cwd(current)
            path = current
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
