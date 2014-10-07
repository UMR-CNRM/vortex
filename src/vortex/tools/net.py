#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Net tools.
"""


import types
import urlparse
import io, ftplib
from netrc import netrc
from datetime import datetime

from vortex.autolog import logdefault as logger

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


class StdFtp(object):
    """
    Standard wrapper for the crude FTP object from :mod:`ftplib`.
    First argument of the constructor is the calling OS interface.
    """

    def __init__(self, system, hostname):
        logger.debug('FTP init host %s', hostname)
        self._system  = system
        self._closed  = True
        self._ftplib  = ftplib.FTP(hostname)
        self._logname = None
        self._created = datetime.now()
        self._opened  = None
        self._deleted = None

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
        self.system.stderr('ftp:'+cmd, *args)

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
        try:
            topnow = datetime.now() if self._deleted is None else self._deleted
            timelength = ( topnow - self._opened ).total_seconds()
        except TypeError:
            timelength = 0
        finally:
            return timelength

    def close(self):
        """Proxy to ftplib :meth:`ftplib.FTP.close`."""
        self.stderr('close')
        self._closed = True
        self._deleted = datetime.now()
        return self._ftplib.close()

    def login(self, *args):
        """Proxy to ftplib :meth:`ftplib.FTP.login`."""
        self.stderr('login', args[0])
        logger.debug('FTP login %s', str(args))
        rc = self._ftplib.login(*args)
        if rc:
            self._closed = False
            self._opened = datetime.now()
        else:
            logger.warning('FTP could not login with args %s', str(args))
        return rc

    def fastlogin(self, logname, password=None):
        """Simple heuristic using actual attributes and/or netrc information to log in."""
        self.stderr('fastlogin', logname)
        rc = False
        if logname and password:
            self._logname = logname
            rc = self.login(logname, password)
        else:
            auth = netrc().authenticators(self.host)
            if auth:
                self._logname = auth[0]
                rc = self.login(self._logname, auth[2])
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

    def dir(self, *args):
        """Proxy to ftplib :meth:`ftplib.FTP.login`."""
        self.stderr('dir', *args)
        return self._ftplib.dir(*args)

    def ls(self, *args):
        """Returns directory listing."""
        self.stderr('ls', *args)
        return self.dir(*args)

    def get(self, source, destination):
        """Retrieve a remote `destination` file to a local `source` file object."""
        self.stderr('get', source, destination)
        if type(destination) is types.StringType:
            self.system.filecocoon(destination)
            target = io.open(destination, 'wb')
            xdestination = True
        else:
            target = destination
            xdestination = False
        logger.info('FTP get %s', source)
        rc = True
        try:
            self.retrbinary('RETR ' + source, target.write)
        except StandardError:
            rc = False
        if xdestination:
            target.close()
        return rc

    def put(self, source, destination):
        """Store a local `source` file object to a remote `destination`."""
        self.stderr('put', source, destination)
        if type(source) is types.StringType:
            inputsrc = io.open(source, 'rb')
            xsource = True
        else:
            inputsrc = source
            try:
                inputsrc.seek(0)
            except AttributeError as seek_error:
                logger.warning('No rewind on source %s' % str(source))
            except IOError as seek_error:
                logger.debug('Seek trouble on source %s' % str(source))
            xsource = False
        self.rmkdir(destination)
        try:
            self.delete(destination)
            logger.warning('File %s will be replaced.', destination)
        except ftplib.error_perm:
            logger.warning('File %s will be created.', destination)
        logger.info('FTP put %s', destination)
        rc = True
        try:
            self.storbinary('STOR ' + destination, inputsrc)
        except StandardError:
            rc = False
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
                self.mkd(current)
                self.cwd(current)
            path = current
        self.cwd(origin)

    def cd(self, destination):
        """Change to a directory."""
        return self.cwd(destination)

    def rm(self, source):
        """Proxy to ftp delete command."""
        return self.delete(source)
