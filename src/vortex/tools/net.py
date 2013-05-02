#!/bin/env python
# -*- coding: utf-8 -*-

"""
Net tools.
"""

from os.path import dirname
from vortex.autolog import logdefault as logger
import urlparse
import io, ftplib
from ftplib import FTP
from netrc import netrc

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

    (realscheme, other) = uristring.split(':',1)
    rp = urlparse.urlparse('http:' + other)
    uridict = rp._asdict()
    netloc = uridict['netloc'].split('@',1)
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


class StdFtp(FTP):
    """
    Standard wrapper for the crude FTP object from :mod:`ftplib`.
    First argument of the constructor is the calling OS interface.
    """

    def __init__(self, system, hostname):
        self._local_system = system
        FTP.__init__(self, hostname)
        self.logname = None

    def identify(self):
        print self

    def fastlogin(self, login, password=None):
        if login and password:
            self.logname = login
            return self.login(login, password)
        else:
            auth = netrc().authenticators(self.host)
            if auth:
                self.logname = auth[0]
                return self.login(self.logname, auth[2])
            else:
                return None

    def fullpath(self, remote):
        return self.logname + '@' + self.host + ':' + remote

    def list(self, *args):
        contents = []
        self.retrlines('LIST', callback=contents.append)
        return contents

    def ls(self, *args):
        """Returns directory listing."""
        return self.dir(*args)

    def get(self, source, destination):
        """Retrieve a remote `destination` file to a local `source` file object."""
        if type(destination) == str:
            self._local_system.filecocoon(destination)
            target = io.open(destination, 'wb')
            xdestination = True
        else:
            target = destination
            xdestination = False
        logger.info('FTP get %s', source)
        rc = True
        try:
            self.retrbinary('RETR ' + source, target.write)
        except:
            rc = False
        if xdestination:
            target.close()
        return rc

    def put(self, source, destination):
        """Store a local `source` file object to a remote `destination`."""
        inputsrc = open(source, 'rb')
        if type(source) == str:
            inputsrc = io.open(source, 'rb')
            xsource = True
        else:
            inputsrc = source
            inputsrc.seek(0)
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
        except:
            rc = False
        if xsource:
            inputsrc.close()
        return rc

    def rmkdir(self, destination):
        """Recursive directory creation."""
        origin = self.pwd()
        if destination.startswith('/'):
            path = ''
        else:
            path = self.pwd()

        for subdir in filter(lambda x: x, dirname(destination).split('/')):
            current = path + '/' + subdir
            try:
                self.cwd(current)
                path = current
            except ftplib.error_perm:
                self.mkd(current)
                self.cwd(current)
            path = current
        self.cwd(origin)
