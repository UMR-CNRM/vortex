"""
Net tools.
"""

import abc
import binascii
import collections
from collections import namedtuple
from datetime import datetime
import ftplib
import functools
import io
import itertools
import operator
import random
import re
import shlex
import socket
import stat
import struct
import time
from urllib import request as urlrequest
from urllib import parse as urlparse

from bronx.fancies import loggers
from bronx.net.netrc import netrc
from bronx.syntax.decorators import nicedeco, secure_getattr

from vortex.config import get_from_config_w_default, ConfigurationError

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

DEFAULT_FTP_PORT = ftplib.FTP_PORT


def uriparse(uristring):
    """Parse the specified ``uristring`` as a dictionary including keys:

    * scheme
    * netloc
    * port
    * query
    * username
    * password
    """
    (realscheme, other) = uristring.split(":", 1)
    rp = urlparse.urlparse("http:" + other)
    uridict = rp._asdict()
    netloc = uridict["netloc"].split("@", 1)
    hostport = netloc.pop().split(":")
    uridict["netloc"] = hostport.pop(0)
    if hostport:
        uridict["port"] = hostport.pop()
    else:
        uridict["port"] = None
    if netloc:
        userpass = netloc.pop().split(":")
        uridict["username"] = userpass.pop(0)
        if userpass:
            uridict["password"] = userpass.pop()
        else:
            uridict["password"] = None
    else:
        uridict["username"] = None
        uridict["password"] = None
    uridict["scheme"] = realscheme
    uridict["query"] = urlparse.parse_qs(uridict["query"])
    return uridict


def uriunparse(uridesc):
    """Delegates to :mod:`urlparse` the job to unparse the given description (as a dictionary)."""
    return urlparse.urlunparse(uridesc)


def http_post_data(
    url, data, ok_statuses=(), proxies=None, headers=None, verify=None
):
    """Make a http/https POST request, encoding **data**."""
    if isinstance(proxies, (list, tuple)):
        proxies = {scheme: proxies for scheme in ("http", "https")}
    # Try to use the requests package
    try:
        import requests

        use_requests = True
    except ImportError:
        use_requests = False
    # The modern way
    if use_requests:
        resp = requests.post(
            url=url, data=data, headers=headers, proxies=proxies, verify=verify
        )
        if ok_statuses:
            is_ok = resp.status_code in ok_statuses
        else:
            is_ok = resp.ok
        return is_ok, resp.status_code, resp.headers, resp.text
    else:
        if not isinstance(data, bytes):
            data = urlparse.urlencode(data).encode("utf-8")
        if uriparse(url)["scheme"] == "https":
            raise RuntimeError(
                "HTTPS is not properly supported by urllib.request ({}).".format(
                    url
                )
            )
        handlers = []
        if isinstance(proxies, dict):
            handlers.append(urlrequest.ProxyHandler(proxies))
        opener = urlrequest.build_opener(*handlers)
        req = urlrequest.Request(
            url=url, data=data, headers={} if headers is None else headers
        )
        try:
            req_f = opener.open(req)
        except Exception as e:
            try:  # ignore UnboundLocalError if req_f has not been created yet
                req_f.close()
            finally:
                raise e
        else:
            try:
                req_rc = req_f.getcode()
                req_info = req_f.info()
                req_data = req_f.read().decode("utf-8")
                if ok_statuses:
                    return req_rc in ok_statuses, req_rc, req_info, req_data
                else:
                    return 200 <= req_rc < 400, req_rc, req_info, req_data
            finally:
                req_f.close()


def netrc_lookup(logname, hostname, nrcfile=None):
    """Looks into the .netrc file to find FTP authentication credentials.

    :param str logname: The login to look for
    :param str hostname: The hostname to look for

    For backward compatibility reasons:

        * If *hostname* is a FQDN, an attempt will be made using the hostname
          alone.
        * If credentials are not found for the *logname*/*hostname* pair, an attempt
          is made ignoring the provided *logname*.

    """
    actual_logname = None
    actual_pwd = None
    nrc = netrc(file=nrcfile)
    if nrc:
        auth = nrc.authenticators(hostname, login=logname)
        if not auth:
            # self.host may be a FQDN, try to guess only the hostname
            auth = nrc.authenticators(hostname.split(".")[0], login=logname)
        # for backward compatibility: This might be removed one day
        if not auth:
            auth = nrc.authenticators(hostname)
        if not auth:
            # self.host may be a FQDN, try to guess only the hostname
            auth = nrc.authenticators(hostname.split(".")[0])
        # End of backward compatibility section
        if auth:
            actual_logname = auth[0]
            actual_pwd = auth[2]
        else:
            logger.warning("netrc lookup failed (%s)", str(auth))
    else:
        logger.warning("unable to fetch .netrc file")
    return actual_logname, actual_pwd


class ExtendedFtplib:
    """Simple Vortex's extension to the bare ftplib object.

    It wraps the standard ftplib object to add or overwrite methods.
    """

    def __init__(self, system, ftpobj, hostname="", port=DEFAULT_FTP_PORT):
        """
        :param ~vortex.tools.systems.OSExtended system: The system object to work with
        :param ftplib.FTP ftpobj: The FTP object to work with / to extend
        """
        self._system = system
        self._ftplib = ftpobj
        self._closed = True
        self._logname = "not_logged_in"
        self._created = datetime.now()
        self._opened = None
        self._deleted = None
        if hostname:
            self._ftplib.connect(hostname, port)

    @property
    def host(self):
        """Return the hostname."""
        return self._ftplib.host

    @property
    def port(self):
        """Return the port number."""
        return self._ftplib.port

    def __str__(self):
        """
        Nicely formatted print, built as the concatenation
        of the class full name and `logname` and `length` attributes.
        """
        return "{:s} | host={:s} logname={:s} since={!s}>".format(
            repr(self).rstrip(">"),
            self.host,
            self.logname,
            self.length,
        )

    @secure_getattr
    def __getattr__(self, key):
        """Gateway to undefined method or attributes if present in ``_ftplib``."""
        actualattr = getattr(self._ftplib, key)
        if callable(actualattr):

            def osproxy(*args, **kw):
                cmd = [key]
                cmd.extend(args)
                cmd.extend(["{:s}={!s}".format(x, kw[x]) for x in kw.keys()])
                self.stderr(*cmd)
                return actualattr(*args, **kw)

            osproxy.func_name = str(key)
            osproxy.__name__ = str(key)
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
        self.system.stderr("ftp:" + cmd, *args)

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
            logger.warning(
                "Could not evaluate connexion length %s", repr(self)
            )
        return timelength

    def close(self):
        """Proxy to ftplib :meth:`ftplib.FTP.close`."""
        self.stderr("close")
        rc = True
        if not self.closed:
            rc = self._ftplib.close() or True
            self._closed = True
            self._deleted = datetime.now()
        return rc

    def login(self, *args):
        """Proxy to ftplib :meth:`ftplib.FTP.login`."""
        self.stderr("login", args[0])
        self._logname = args[0]
        # kept for debugging, but this exposes the user's password!
        # logger.debug('FTP login <args:%s>', str(args))
        rc = self._ftplib.login(*args)
        if rc:
            self._closed = False
            self._deleted = None
            self._opened = datetime.now()
        else:
            logger.warning("FTP could not login <args:%s>", str(args))
        return rc

    def list(self, *args):
        """Returns standard directory listing from ftp protocol."""
        self.stderr("list", *args)
        contents = []
        self.retrlines("LIST", callback=contents.append)
        return contents

    def dir(self, *args):
        """Proxy to ftplib :meth:`ftplib.FTP.dir`."""
        self.stderr("dir", *args)
        return self._ftplib.dir(*args)

    def ls(self, *args):
        """Returns directory listing."""
        self.stderr("ls", *args)
        return self.dir(*args)

    ll = ls

    def get(self, source, destination):
        """Retrieve a remote `destination` file to a local `source` file object."""
        self.stderr("get", source, destination)
        if isinstance(destination, str):
            self.system.filecocoon(destination)
            target = open(destination, "wb")
            xdestination = True
        else:
            target = destination
            xdestination = False
        logger.info("FTP <get:{:s}>".format(source))
        rc = False
        try:
            self.retrbinary("RETR " + source, target.write)
            if xdestination:
                target.seek(0, io.SEEK_END)
                if self.size(source) == target.tell():
                    rc = True
                else:
                    logger.error("FTP incomplete get %s", repr(source))
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
        self.stderr("put", source, destination)
        if isinstance(source, str):
            inputsrc = open(source, "rb")
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
            logger.warning("Could not rewind <source:%s>", str(source))
        except OSError:
            logger.debug("Seek trouble <source:%s>", str(source))

        self.rmkdir(destination)
        try:
            self.delete(destination)
            logger.info("Replacing <file:%s>", str(destination))
        except ftplib.error_perm:
            logger.info("Creating <file:%s>", str(destination))
        except (
            ValueError,
            TypeError,
            OSError,
            ftplib.error_proto,
            ftplib.error_reply,
            ftplib.error_temp,
        ) as e:
            logger.error(
                "Serious delete trouble <file:%s> <error:%s>",
                str(destination),
                str(e),
            )

        logger.info("FTP <put:%s>", str(destination))
        rc = False

        if size is not None:
            try:
                self.voidcmd("ALLO {:d}".format(size))
            except ftplib.error_perm:
                pass

        try:
            self.storbinary("STOR " + destination, inputsrc)
            if exact:
                if self.size(destination) == size:
                    rc = True
                else:
                    logger.error(
                        "FTP incomplete put %s (%d / %d bytes)",
                        repr(source),
                        self.size(destination),
                        size,
                    )
            else:
                rc = True
                if self.size(destination) != size:
                    logger.info(
                        "FTP put %s: estimated %s bytes, real %s bytes",
                        repr(source),
                        str(size),
                        self.size(destination),
                    )
        finally:
            if xsource:
                inputsrc.close()
        return rc

    def rmkdir(self, destination):
        """Recursive directory creation (mimics `mkdir -p`)."""
        self.stderr("rmkdir", destination)
        origin = self.pwd()
        if destination.startswith("/"):
            path_pre = "/"
        elif destination.startswith("~"):
            path_pre = ""
        else:
            path_pre = origin + "/"

        for subdir in self.system.path.dirname(destination).split("/"):
            current = path_pre + subdir
            try:
                self.cwd(current)
                path_pre = current + "/"
            except ftplib.error_perm:
                self.stderr("mkdir", current)
                try:
                    self.mkd(current)
                except ftplib.error_perm as errmkd:
                    if "File exists" not in str(errmkd):
                        raise
                self.cwd(current)
            path_pre = current + "/"
        self.cwd(origin)

    def cd(self, destination):
        """Change to a directory."""
        return self.cwd(destination)

    def rm(self, source):
        """Proxy to ftp delete command."""
        return self.delete(source)

    def mtime(self, filename):
        """Retrieve the modification time of a file."""
        resp = self.sendcmd("MDTM " + filename)
        if resp[:3] == "213":
            s = resp[3:].strip().split()[-1]
            return int(s)

    def size(self, filename):
        """Retrieve the size of a file."""
        # The SIZE command is defined in RFC-3659
        resp = self.sendcmd("SIZE " + filename)
        if resp[:3] == "213":
            s = resp[3:].strip().split()[-1]
            return int(s)


class StdFtp:
    """Standard wrapper for the crude FTP object (of class :class:`ExtendedFtplib`).

    It relies heavily on the :class:`ExtendedFtplib` class for FTP commands but
    adds some interesting features such as:

        * a fast login using the .netrc file;
        * the ability to delay the :class:`ftplib.FTP` object creation as much as possible;
        * the VORTEX_FTP_PROXY environment variable is looked for (if not available
          FTP_PROXY is also scrutated). If defined, a FTP proxy will be used.

    Methods that are not explicitly defined in the present class will be looked
    for in the associated :class:`ExtendedFtplib` object (and eventually in the
    wrapped :class:`ftplib.FTP` object). For example, it's possible
    to call `self.get(...)` (exactly as one would do with the native
    :class:`ExtendedFtplib` and :class:`ftplib.FTP` class).
    """

    _PROXY_TYPES = ("no-auth-logname-based",)

    _NO_AUTOLOGIN = (
        "set_debuglevel",
        "connect",
        "login",
        "stderr",
    )

    def __init__(
        self,
        system,
        hostname,
        port=DEFAULT_FTP_PORT,
        nrcfile=None,
        ignoreproxy=False,
    ):
        """
        :param ~vortex.tools.systems.OSExtended system: The system object to work with
        :param str hostname: The remote host's network name
        :param int port: The remote host's FTP port.
        :param str nrcfile: The path to the .netrc file (if `None` the ~/.netrc default is used)
        :param bool ignoreproxy: Forcibly ignore any proxy related environment variables
        """
        logger.debug("FTP init <host:%s>", hostname)
        self._system = system
        if ignoreproxy:
            self._proxy_host, self._proxy_port, self._proxy_type = (
                None,
                None,
                None,
            )
        else:
            self._proxy_host, self._proxy_port, self._proxy_type = (
                self._proxy_init()
            )
        self._hostname = hostname
        self._port = port
        self._nrcfile = nrcfile
        self._internal_ftp = None
        self._logname = None
        self._cached_pwd = None
        self._barelogname = None

    def _proxy_init(self):
        """Return the proxy type, address and port."""
        p_netloc = (None, None)
        p_url = self.system.env.get(
            "VORTEX_FTP_PROXY", self.system.env.get("FTP_PROXY", None)
        )
        if p_url:
            p_netloc = p_url.split(":", 1)
            if len(p_netloc) == 1:
                p_netloc.append(DEFAULT_FTP_PORT)
            else:
                p_netloc[1] = int(p_netloc[1])
        p_type = self.system.env.get(
            "VORTEX_FTP_PROXY_TYPE", self._PROXY_TYPES[0]
        )
        if p_type not in self._PROXY_TYPES:
            raise ValueError(
                "Incorrect value for the VORTEX_FTP_PROXY_TYPE "
                + "environment variable (got: {:s})".format(p_type)
            )
        return p_netloc[0], p_netloc[1], p_type

    def _extended_ftp_host_and_port(self):
        if self._proxy_host:
            if self._proxy_type == self._PROXY_TYPES[0]:
                return self._proxy_host, self._proxy_port
        else:
            return self._hostname, self._port

    @property
    def _extended_ftp(self):
        """This property provides the :class:`ExtendedFtpLib` to work with.

        It is created on-demand.
        """
        if self._internal_ftp is None:
            self._internal_ftp = ExtendedFtplib(
                self._system, ftplib.FTP(), *self._extended_ftp_host_and_port()
            )
        return self._internal_ftp

    _loginlike_extended_ftp = _extended_ftp

    @property
    def system(self):
        """The current local system interface."""
        return self._system

    @property
    def host(self):
        """The FTP server hostname."""
        if self._internal_ftp is None or self._proxy_host:
            return self._hostname
        else:
            return self._extended_ftp.host

    @property
    def port(self):
        """The FTP server port number."""
        if self._internal_ftp is None or self._proxy_host:
            return self._port
        else:
            return self._extended_ftp.port

    @property
    def logname(self):
        """The current logname."""
        return self._barelogname

    @property
    def proxy(self):
        if self._proxy_host:
            return "{0._proxy_host}:{0._proxy_port}".format(self)
        else:
            return None

    @property
    def cached_pwd(self):
        """The current cached password."""
        return self._cached_pwd

    def netpath(self, remote):
        """The complete qualified net path of the remote resource."""
        return "{:s}@{:s}:{:s}".format(
            self.logname if self.logname is not None else "unknown",
            self.host,
            remote,
        )

    def delayedlogin(self):
        """Login to the FTP server (if it was not already done)."""
        if self._loginlike_extended_ftp.closed:
            if self._logname is None or self.cached_pwd is None:
                logger.warning(
                    "FTP logname/password must be set first. Use the fastlogin method."
                )
                raise RuntimeError("logname/password were not provided")
            return self.login(self._logname, self.cached_pwd)
        else:
            return True

    def _process_logname_password(self, logname, password=None):
        """Find the actual *logname* and *password*."""
        if logname and password:
            bare_logname = logname
        else:
            bare_logname, password = netrc_lookup(
                logname, self.host, nrcfile=self._nrcfile
            )
        logname = bare_logname
        if logname and self._proxy_host:
            if self._proxy_type == self._PROXY_TYPES[0]:
                logname = "{0:s}@{1.host:s}:{1.port:d}".format(
                    bare_logname, self
                )
        if logname:
            return logname, password, bare_logname
        else:
            return None, None, None

    def close(self):
        """Terminates the FTP session."""
        rc = True
        if self._internal_ftp is not None:
            rc = self._internal_ftp.close()
        return rc

    def fastlogin(self, logname, password=None, delayed=True):
        """
        Simple heuristic using actual attributes and/or netrc information to find
        login informations.

        If *delayed=True*, the actual login will be performed later (whenever
        necessary).
        """
        rc = False
        p_logname, p_password, p_barelogname = self._process_logname_password(
            logname, password
        )
        if p_logname and p_password:
            self._logname = p_logname
            self._cached_pwd = p_password
            self._barelogname = p_barelogname
            rc = True
        if not delayed and rc:
            # If one really wants to login...
            rc = self.login(self._logname, self._cached_pwd)
        return bool(rc)

    def _extended_ftp_lookup_check(self, key):
        """Are we allowed to look for *key* in the `self._extended_ftp` object ?"""
        return not key.startswith("_")

    def _extended_ftp_lookup(self, key):
        """Look if the `self._extended_ftp` object can provide a given method.

        If so, a possibly wrapped method is returned (in order to perform the
        delayed login).
        """
        actualattr = getattr(self._extended_ftp, key)
        if callable(actualattr):

            def osproxy(*args, **kw):
                # For most of the native commands, we want autologin to be performed
                if key not in self._NO_AUTOLOGIN:
                    self.delayedlogin()
                # This is important because wrapper functions are cached (see __getattr__)
                actualattr = getattr(self._extended_ftp, key)
                return actualattr(*args, **kw)

            osproxy.func_name = str(key)
            osproxy.__name__ = str(key)
            osproxy.__doc__ = actualattr.__doc__
            return osproxy
        else:
            return actualattr

    @secure_getattr
    def __getattr__(self, key):
        """Gateway to undefined method or attributes if present in ``_extended_ftp``."""
        if self._extended_ftp_lookup_check(key):
            attr = self._extended_ftp_lookup(key)
            if callable(attr):
                setattr(self, key, attr)
            return attr
        raise AttributeError(key)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):  # @UnusedVariable
        self.close()


class AutoRetriesFtp(StdFtp):
    """An advanced FTP client with retry-on-failure capabilities.

    It inherits from :class:`StdFtp` class thus providing the same interface (no
    new public methods are added).

    However, most of the :class:`StdFtp` methods are wrapped in order to implement
    the retry-on-failure capability.
    """

    def __init__(
        self,
        system,
        hostname,
        port=DEFAULT_FTP_PORT,
        nrcfile=None,
        ignoreproxy=False,
        retrycount_default=6,
        retrycount_connect=8,
        retrycount_login=3,
        retrydelay_default=15,
        retrydelay_connect=15,
        retrydelay_login=10,
    ):
        """
        :param ~vortex.tools.systems.OSExtended system: The system object to work with.
        :param str hostname: The remote host's network name.
        :param int port: The remote host's FTP port.
        :param str nrcfile: The path to the .netrc file (if `None` the ~/.netrc default is used)
        :param bool ignoreproxy: Forcibly ignore any proxy related environment variables
        :param int retrycount_default: The maximum number of retries for most of the FTP functions.
        :param int retrydelay_default: The delay (in seconds) between two retries for most of the FTP functions.
        :param int retrycount_connect: The maximum number of retries when connecting to the FTP server.
        :param int retrydelay_connect: The delay (in seconds) between two retries when connecting to the FTP server.
        :param int retrycount_login: The maximum number of retries when login in to the FTP server.
        :param int retrydelay_login: The delay (in seconds) between two retries when login in to the FTP server.
        """
        logger.debug("AutoRetries FTP init <host:%s>", hostname)
        # Retry stuff
        self.retrycount_default = retrycount_default
        self.retrycount_connect = retrycount_connect
        self.retrycount_login = retrycount_login
        self.retrydelay_default = retrydelay_default
        self.retrydelay_connect = retrydelay_connect
        self.retrydelay_login = retrydelay_login
        # Reset everything
        self._initialise()
        # Finalise
        super().__init__(
            system,
            hostname,
            port=port,
            nrcfile=nrcfile,
            ignoreproxy=ignoreproxy,
        )

    def _initialise(self):
        self._internal_retries_max = None
        self._cwd = ""
        self._autodestroy()

    def _autodestroy(self):
        """Reset the proxied :class:`ExtendedFtpLib` object."""
        self._internal_ftp = None

    def _get_extended_ftp(self, retrycount, retrydelay, exceptions_extras):
        """Delay the call to 'connect' as much as possible."""
        if self._internal_ftp is None:
            eftplib = self._retry_wrapped_callable(
                ExtendedFtplib,
                retrycount=retrycount,
                retrydelay=retrydelay,
                exceptions_extras=exceptions_extras,
            )
            self._internal_ftp = eftplib(
                self._system, ftplib.FTP(), *self._extended_ftp_host_and_port()
            )
        return self._internal_ftp

    @property
    def _extended_ftp(self):
        """Delay the call to 'connect' as much as possible."""
        return self._get_extended_ftp(
            self.retrycount_connect,
            self.retrydelay_connect,
            [
                socket.timeout,
            ],
        )

    @property
    def _loginlike_extended_ftp(self):
        """Delay the call to 'connect' as much as possible."""
        return self._get_extended_ftp(
            self.retrycount_login,
            self.retrydelay_login,
            [
                ftplib.error_perm,
                socket.error,
            ],
        )

    def _actual_login(self, *args):
        """Actually log in + save logname/password + correct the cwd if needed."""
        rc = self._extended_ftp.login(*args)
        if rc:
            if self._logname is None or self._logname != args[0]:
                self._logname = args[0]
                self._barelogname = args[0]
            self._cached_pwd = args[1]
        if rc and self._cwd:
            cocoondir = self._cwd
            self._cwd = ""
            rc = rc and self.cwd(cocoondir)
        return rc

    def login(self, *args):
        """Proxy to ftplib :meth:`ftplib.FTP.login`."""
        wftplogin = self._retry_wrapped_callable(
            self._actual_login,
            retrycount=self.retrycount_login,
            retrydelay=self.retrydelay_login,
            exceptions_extras=[ftplib.error_perm, socket.error, EOFError],
        )
        return wftplogin(*args)

    def _retry_wrapped_callable(
        self, func, retrycount=None, retrydelay=None, exceptions_extras=None
    ):
        """
        Wraps the *func* function in order to implement a retry on failure
        mechanism.

        :param callable func: Any callable that should be wrapped (usually a function)
        :param int retrycount: The wanted retry count (`self.retrycount_default` if omitted)
        :param int retrydelay: The delay between retries (`self.retrydelay_default` if omitted)
        :param list exceptions_extras: Extra exceptions to be catch during the retry
            phase (in addtion of `ftplib.error_temp`, `ftplib.error_proto`,
            `ftplib.error_reply`).

        Upon failure, :meth:`_autodestroy` is called in order to reset this object
        and start with a clean slate.
        """
        actual_rcount = retrycount or self.retrycount_default
        actual_rdelay = retrydelay or self.retrydelay_default
        actual_exc = [
            ftplib.error_temp,
            ftplib.error_proto,
            ftplib.error_reply,
        ]
        if exceptions_extras:
            actual_exc.extend(exceptions_extras)
        actual_exc = tuple(actual_exc)

        def retries_wrapper(*args, **kw):
            globalcounter_driver = self._internal_retries_max is None
            if globalcounter_driver:
                self._internal_retries_max = actual_rcount
            retriesleft = max(
                min(self._internal_retries_max, actual_rcount), 1
            )
            try:
                while retriesleft:
                    try:
                        return func(*args, **kw)
                    except actual_exc as e:
                        logger.warning(
                            'An error occurred (in "%s"): %s', func.__name__, e
                        )
                        retriesleft -= 1
                        self._internal_retries_max -= 1
                        if not retriesleft:
                            logger.warning(
                                "The maximum number of retries (%d) was reached.",
                                actual_rcount,
                            )
                            raise
                        logger.warning(
                            "Sleeping %d sec. before the next attempt.",
                            actual_rdelay,
                        )
                        self._autodestroy()
                        self.system.sleep(actual_rdelay)
            finally:
                if globalcounter_driver:
                    self._internal_retries_max = None

        retries_wrapper.func_name = func.__name__
        retries_wrapper.__name__ = func.__name__
        retries_wrapper.__doc__ = func.__doc__
        return retries_wrapper

    @secure_getattr
    def __getattr__(self, key):
        """Gateway to undefined method or attributes if present in ``_extended_ftp``."""
        if self._extended_ftp_lookup_check(key):
            attr = self._extended_ftp_lookup(key)
            if callable(attr):
                if key not in self._NO_AUTOLOGIN:
                    attr = self._retry_wrapped_callable(
                        attr,
                        exceptions_extras=[
                            socket.error,
                        ],
                    )
                setattr(self, key, attr)
            return attr
        raise AttributeError(key)

    def cwd(self, pathname):
        """Change the current directory to the *pathname* directory."""
        todo = self._retry_wrapped_callable(self._extended_ftp_lookup("cwd"))
        rc = todo(pathname)
        if rc:
            if self.system.path.isabs(pathname):
                self._cwd = pathname
            else:
                self._cwd = self.system.path.join(self._cwd, pathname)
                self._cwd = self.system.path.normpath(self._cwd)
        return rc

    def cd(self, destination):
        """Change the current directory to the *pathname* directory."""
        return self.cwd(destination)

    def quit(self):
        """Quit the current ftp session politely."""
        try:
            rc = self._retry_wrapped_callable(
                self._extended_ftp_lookup("quit")
            )()
        finally:
            self._initialise()
        return rc

    def close(self):
        """Quit the current ftp session abruptly."""
        rc = super().close()
        self._initialise()
        return rc


class ResetableAutoRetriesFtp(AutoRetriesFtp):
    """
    An advanced FTP client with retry-on-failure capabilities and an additional
    method :meth:`reset` to reset the current working directory to its initial
    value (i.e. The working directory just after login).
    """

    def _initialise(self):
        super()._initialise()
        self._initialpath = None

    def _actual_login(self, *args):
        if self._initialpath is not None and self._cwd:
            rc = super()._actual_login(*args)
        else:
            rc = super()._actual_login(*args)
            if rc:
                self._initialpath = self.pwd()
        return rc

    def reset(self):
        """Reset the current working directory to its initial value."""
        if self._initialpath is not None and self._cwd:
            self._cwd = ""
            return self.cwd(self._initialpath)


class PooledResetableAutoRetriesFtp(ResetableAutoRetriesFtp):
    """
    An advanced FTP client derived from :class:`ResetableAutoRetriesFtp` that can
    be used in conjunction with an :class:`FtpConnectionPool` object.
    """

    def __init__(self, pool, *kargs, **kwargs):
        """
        :param FtpConnectionPool pool: The FTP connection pool to work with.

        *kargs* and *kwargs* are passed directly to the :class:`ResetableAutoRetriesFtp`
        class constructor (refers to its documentation).
        """
        self._pool = pool
        super().__init__(*kargs, **kwargs)
        logger.debug(
            "Pooled FTP init <host:%s> <pool:%s>", self.host, repr(pool)
        )

    def forceclose(self):
        """Really quit the ftp session."""
        if self._internal_ftp is not None:
            return super().close()
        else:
            return True

    def close(self):
        """
        The ftp session is not really closed... instead, the current object is
        given back to the FTP connection pool that will be able to reuse it.
        """
        # If no underlying library is available, do not bother...
        if self._internal_ftp is not None:
            self._pool.relinquishing(self)
        return True


class FtpConnectionPool:
    """A class that dispense FTP client objects for a given *hostname*/*logname* pair.

    Dispensed objects can either be new object or re-used pre-existing ones: this
    makes no differences for the caller since re-used object are properly "reseted"
    before being dispensed.

    The great advantage of this class is to keep FTP connections open for a given
    number of clients which avoids multiple connect/login sequences (that are
    time consuming). On the other hand, the user must be cautious when using this
    class since having numerous long standing opened connections can harm the
    remote FTP hosts.
    """

    #: The FTP client class that will be used
    _FTPCLIENT_CLASS = PooledResetableAutoRetriesFtp
    #: The maximum number of spare FTP client (when this threshold is hit,
    #: warning are issued)
    _REUSABLE_THRESHOLD = 10

    def __init__(self, system, nrcfile=None, ignoreproxy=False):
        """
        :param ~vortex.tools.systems.OSExtended system: The system object to work with.
        :param str nrcfile: The path to the .netrc file (if `None` the ~/.netrc default is used)
        :param bool ignoreproxy: Forcibly ignore any proxy related environment variables
        """
        self._system = system
        self._nrcfile = nrcfile
        self._ignoreproxy = ignoreproxy
        self._reusable = collections.defaultdict(collections.deque)
        self._created = 0
        self._reused = 0
        self._givenback = 0

    @property
    def poolsize(self):
        """The number of spare FTP clients."""
        return sum([len(hpool) for hpool in self._reusable.values()])

    def __str__(self):
        """Print a summary of the connection pool activity."""
        out = "Current connection pool size: {:d}\n".format(self.poolsize)
        out += "  # of created objects: {:d}\n".format(self._created)
        out += "  # of re-used objects: {:d}\n".format(self._reused)
        out += "  # of given back objects: {:d}\n".format(self._givenback)
        if self.poolsize:
            out += "\nDetailed list of current spare clients:\n"
            for ident, hpool in self._reusable.items():
                for client in hpool:
                    out += "  - {id[1]:s}@{id[0]:s}: {cl!r}\n".format(
                        id=ident, cl=client
                    )
        return out

    def deal(
        self,
        hostname,
        logname,
        port=DEFAULT_FTP_PORT,
        delayed=True,
        ignoreproxy=False,
    ):
        """Retrieve an FTP client for the *hostname*/*logname* pair."""
        p_logname, _ = netrc_lookup(logname, hostname, nrcfile=self._nrcfile)
        if self._reusable[(hostname, port, p_logname)]:
            ftpc = self._reusable[(hostname, port, p_logname)].pop()
            ftpc.reset()
            logger.debug("Re-using a client: %s", repr(ftpc))
            if not delayed:
                # If requested, ensure that we are logged in
                ftpc.delayedlogin()
            self._reused += 1
            return ftpc
        else:
            ftpc = self._FTPCLIENT_CLASS(
                self,
                self._system,
                hostname,
                port=port,
                nrcfile=self._nrcfile,
                ignoreproxy=self._ignoreproxy,
            )
            rc = ftpc.fastlogin(p_logname, delayed=delayed)
            if rc:
                logger.debug("Creating a new client: %s", repr(ftpc))
                self._created += 1
                return ftpc
            else:
                logger.warning(
                    "Could not login on %s:%d as %s [%s]",
                    hostname,
                    port,
                    p_logname,
                    str(rc),
                )
                return None

    def relinquishing(self, client):
        """
        When the user is done with a reusable *client*, this method should be
        called in order for the FTP connection pool to reuse it.

        It is usually dealt with properly by the FTP client object itself when
        its `close` method is called.
        """
        assert isinstance(client, self._FTPCLIENT_CLASS)
        self._reusable[(client.host, client.port, client.logname)].append(
            client
        )
        self._givenback += 1
        logger.debug(
            "Spare client for %s@%s:%d has been stored (poolsize=%d).",
            client.logname,
            client.host,
            client.port,
            self.poolsize,
        )
        if self.poolsize >= self._REUSABLE_THRESHOLD:
            logger.warning(
                "The FTP pool is too big ! (%d  >= %d). Here are the details:\n%s",
                self.poolsize,
                self._REUSABLE_THRESHOLD,
                str(self),
            )

    def clear(self):
        """Destroy all the spare FTP clients."""
        for hpool in self._reusable.values():
            for client in hpool:
                logger.debug(
                    "Destroying client for %s@%s", client.logname, client.host
                )
                client.forceclose()
            hpool.clear()


class Ssh:
    """Remote command execution via ssh.

    Also handles remote copy via scp or ssh, which is intimately linked
    """

    def __init__(self, sh, hostname, logname=None, sshopts=None, scpopts=None):
        """
        :param System sh: The :class:`System` object that is to be used.
        :param str hostname: The target hostname(s).
        :param logname: The logname for the Ssh commands.
        :param str sshopts: Extra SSH options (in addition to the configuration file ones).
        :param str scpopts: Extra SCP options (in addition to the configuration file ones).
        """
        self._sh = sh

        self._logname = logname
        self._remote = hostname

        def _get_ssh_config(key, default):
            config = get_from_config_w_default(
                section="ssh", key=key, default=default
            )
            try:
                val = config.pop("default")
            except AttributeError:
                assert isinstance(config, str)
                return config
            except KeyError:
                msg = (
                    "A default value must be specified for configuration option"
                    f" {key}. See vortex-nwp.readthedocs.io/en/latest/user-guide/configuration.html#ssh"
                )
                raise ConfigurationError(msg)

            for k, v in config.items():
                if re.match(k, socket.gethostname()):
                    val = v
            return val

        self._sshcmd = _get_ssh_config(key="sshcmd", default="ssh")
        self._scpcmd = _get_ssh_config(key="scpcmd", default="scp")
        self._sshopts = (
            _get_ssh_config(key="sshopts", default="").split()
            + (sshopts or "").split()
        )
        self._scpopts = (
            _get_ssh_config(key="scpopts", default="").split()
            + (scpopts or "").split()
        )

    @property
    def sh(self):
        return self._sh

    @property
    def remote(self):
        return (
            "" if self._logname is None else self._logname + "@"
        ) + self._remote

    def check_ok(self):
        """Is the connexion ok ?"""
        return self.execute("true") is not False

    def execute(self, remote_command, sshopts=""):
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
        cmd = (
            [
                self._sshcmd,
            ]
            + self._sshopts
            + sshopts.split()
            + [
                myremote,
            ]
            + [
                remote_command,
            ]
        )
        return self.sh.spawn(cmd, output=True, fatal=False)

    def background_execute(
        self, remote_command, sshopts="", stdout=None, stderr=None
    ):
        """Execute the command remotely and return the object representing the ssh process.

        Return a Popen object representing the ssh process. The user is reponsible
        for calling pclose on this object and check the return code.
        """
        myremote = self.remote
        if myremote is None:
            return False
        cmd = (
            [
                self._sshcmd,
            ]
            + self._sshopts
            + sshopts.split()
            + [
                myremote,
            ]
            + [
                remote_command,
            ]
        )
        return self.sh.popen(cmd, stdout=stdout, stderr=stderr)

    def cocoon(self, destination):
        """Create the remote directory to contain ``destination``.

        Return ``False`` on failure.
        """
        remote_dir = self.sh.path.dirname(destination)
        if remote_dir == "":
            return True
        logger.debug('Cocooning remote directory "%s"', remote_dir)
        cmd = 'mkdir -p "{}"'.format(remote_dir)
        rc = self.execute(cmd)
        if not rc:
            logger.error(
                "Cannot cocoon on %s (user: %s) for %s",
                str(self._remote),
                str(self._logname),
                destination,
            )
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
            logger.error(
                'Cannot remove from %s (user: %s) item "%s"',
                str(self._remote),
                str(self._logname),
                target,
            )
        return rc

    def _scp_putget_commons(self, source, destination):
        """Common checks on source and destination."""
        if not isinstance(source, str):
            msg = "Source is not a plain file path: {!r}".format(source)
            raise TypeError(msg)
        if not isinstance(destination, str):
            msg = "Destination is not a plain file path: {!r}".format(
                destination
            )
            raise TypeError(msg)

        # avoid special cases
        if destination == "" or destination == ".":
            destination = "./"
        else:
            if destination.endswith(".."):
                destination += "/"
            if "../" in destination:
                raise ValueError(
                    '"../" is not allowed in the destination path'
                )
        if destination.endswith("/"):
            destination = self.sh.path.join(
                destination, self.sh.path.basename(source)
            )

        return source, destination

    def scpput(self, source, destination, scpopts=""):
        r"""Send ``source`` to ``destination``.

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
            logger.error("No such file or directory: %s", source)
            return False

        source = self.sh.path.realpath(source)

        myremote = self.remote
        if myremote is None:
            return False

        if not self.cocoon(destination):
            return False

        if not self.remove(destination):
            return False

        if self.sh.path.isdir(source):
            scpopts += " -r"

        if not self.remove(destination + ".tmp"):
            return False

        # transfer to a temporary place.
        # when ``destination`` contains spaces, 1 round of quoting
        # is necessary, to avoid an 'scp: ambiguous target' error.
        cmd = (
            [
                self._scpcmd,
            ]
            + self._scpopts
            + scpopts.split()
            + [source, myremote + ":" + shlex.quote(destination + ".tmp")]
        )
        rc = self.sh.spawn(cmd, output=False, fatal=False)
        if rc:
            # success, rename the tmp
            rc = self.execute('mv "{0}.tmp" "{0}"'.format(destination))
        return rc

    def scpget(self, source, destination, scpopts="", isadir=False):
        r"""Send ``source`` to ``destination``.

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
            scpopts += " -r"

        # transfer to a temporary place.
        # when ``source`` contains spaces, 1 round of quoting
        # is necessary, to avoid an 'scp: ambiguous target' error.
        cmd = (
            [
                self._scpcmd,
            ]
            + self._scpopts
            + scpopts.split()
            + [myremote + ":" + shlex.quote(source), destination + ".tmp"]
        )
        rc = self.sh.spawn(cmd, output=False, fatal=False)
        if rc:
            # success, rename the tmp
            rc = self.sh.move(destination + ".tmp", destination)
        return rc

    def get_permissions(self, source):
        """
        Convenience method to retrieve the permissions of a file/dir (in a form
        suitable for chmod).
        """
        mode = self.sh.stat(source).st_mode
        return stat.S_IMODE(mode)

    def scpput_stream(self, stream, destination, permissions=None, sshopts=""):
        """Send the ``stream`` to the ``destination``.

        - ``stream`` is a ``file`` (typically returned by open(),
          or the piped output of a spawned process).
        - ``destination`` is the remote file name.

        Return True for ok, False on error.
        """
        if not isinstance(stream, io.IOBase):
            msg = "stream is a {}, should be a <type 'file'>".format(
                type(stream)
            )
            raise TypeError(msg)

        if not isinstance(destination, str):
            msg = "Destination is not a plain file path: {!r}".format(
                destination
            )
            raise TypeError(msg)

        myremote = self.remote
        if myremote is None:
            return False

        if not self.cocoon(destination):
            return False

        # transfer to a tmp, rename and set permissions in one go
        remote_cmd = "cat > {0}.tmp && mv {0}.tmp {0}".format(
            shlex.quote(destination)
        )
        if permissions:
            remote_cmd += " && chmod -v {:o} {}".format(
                permissions, shlex.quote(destination)
            )

        cmd = (
            [
                self._sshcmd,
            ]
            + self._sshopts
            + sshopts.split()
            + [myremote, remote_cmd]
        )
        return self.sh.spawn(cmd, stdin=stream, output=False, fatal=False)

    def scpget_stream(self, source, stream, sshopts=""):
        """Send the ``source`` to the ``stream``.

        - ``source`` is the remote file name.
        - ``stream`` is a ``file`` (typically returned by open(),
          or the piped output of a spawned process).

        Return True for ok, False on error.
        """
        if not isinstance(stream, io.IOBase):
            msg = "stream is a {}, should be a <type 'file'>".format(
                type(stream)
            )
            raise TypeError(msg)

        if not isinstance(source, str):
            msg = "Source is not a plain file path: {!r}".format(source)
            raise TypeError(msg)

        myremote = self.remote
        if myremote is None:
            return False

        # transfer to a tmp, rename and set permissions in one go
        remote_cmd = "cat {}".format(shlex.quote(source))
        cmd = (
            [
                self._sshcmd,
            ]
            + self._sshopts
            + sshopts.split()
            + [myremote, remote_cmd]
        )
        return self.sh.spawn(cmd, output=stream, fatal=False)

    def tunnel(
        self,
        finaldestination,
        finalport=0,
        entranceport=None,
        maxwait=3.0,
        checkdelay=0.25,
    ):
        """Create an SSH tunnel and check that it actually starts.

        :param str finaldestination: The destination hostname (i.e the machine
                                     at the far end of the tunnel). If the
                                     "socks" special value is provided, the SSH
                                     tunnel will behave as a SOCKS4/SOCKS5 proxy.
        :param int finalport: The destination port
        :param int entranceport: The port number of the tunnel entrance (if None,
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
                logger.error(
                    "The SSH tunnel creation failed "
                    + "(entrance: %d, dest: %s:%d, via %s).",
                    entranceport,
                    finaldestination,
                    finalport,
                    myremote,
                )
                logger.error("The entrance port is already in use.")
                return False
        if finaldestination == "socks":
            p = self.sh.popen(
                [
                    self._sshcmd,
                ]
                + self._sshopts
                + ["-N", "-D", "{:d}".format(entranceport), myremote],
                stdin=False,
                output=False,
            )
        else:
            if finalport <= 0:
                raise ValueError(
                    "Erroneous finalport value: {!s}".format(finalport)
                )
            p = self.sh.popen(
                [
                    self._sshcmd,
                ]
                + self._sshopts
                + [
                    "-N",
                    "-L",
                    "{:d}:{:s}:{:d}".format(
                        entranceport, finaldestination, finalport
                    ),
                    myremote,
                ],
                stdin=False,
                output=False,
            )
        tunnel = ActiveSshTunnel(
            self.sh, p, entranceport, finaldestination, finalport
        )
        elapsed = 0.0
        while (
            not self.sh.check_localport(entranceport)
        ) and elapsed < maxwait:
            self.sh.sleep(checkdelay)
            elapsed += checkdelay
        if not self.sh.check_localport(entranceport):
            logger.error(
                "The SSH tunnel creation failed "
                + "(entrance: %d, dest: %s:%d, via %s).",
                entranceport,
                finaldestination,
                finalport,
                myremote,
            )
            tunnel.close()
            tunnel = False
        logger.info(
            "SSH tunnel opened, enjoy the ride ! "
            + "(entrance: %d, dest: %s:%d, via %s).",
            entranceport,
            finaldestination,
            finalport,
            myremote,
        )
        return tunnel


class ActiveSshTunnel:
    """Hold an opened SSH tunnel."""

    def __init__(
        self, sh, activeprocess, entranceport, finaldestination, finalport
    ):
        """
        :param Popen activeprocess: The active tunnel process.
        :param int entranceport: Tunnel's entrance port.
        :param str finaldestination: Tunnel's final destination.
        :param int finalport: Tunnel's destination port.

        Objects of this class can be used as context managers (the tunnel will
        be closed when the context is exited).
        """
        self._sh = sh
        self.activeprocess = activeprocess
        self.entranceport = entranceport
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
            logger.debug(
                "Tunnel termination took: %f seconds", time.time() - t0
            )
            if self.opened:
                logger.debug("Tunnel termination failed: issuing SIGKILL")
                self.activeprocess.kill()
            logger.info(
                "SSH tunnel closed (entrance: %d, dest: %s:%d).",
                self.entranceport,
                self.finaldestination,
                self.finalport,
            )

    @property
    def opened(self):
        """Is the tunnel opened ?"""
        return self.activeprocess.poll() is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):  # @UnusedVariable
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
                    logger.error(
                        "The maximum number of retries (%s) was reached...",
                        self._maxtries,
                    )
                    if self._fatal:
                        raise RuntimeError(
                            "Could not execute the SSH command."
                        )
            finally:
                self._fatal_in_progress = False
            return rc

    return wrapped


@nicedeco
def _tryagain(func):
    """decorator: whenever the return code != True, several attempts are made according to self._maxtries.

    This decorator is very specialised and should be used solely with the AssistedSsh
    class since it relies on several attributes (_retry_in_progress, _retries, _maxtries).
    """

    def wrapped(*args, **kwargs):
        self = args[0]
        if self._retry_in_progress:
            return func(self, *args[1:], **kwargs)
        else:
            # This trick ensures that only one retry loop is attempted
            self._retry_in_progress = True
            trycount = 1
            try:
                rc = func(self, *args[1:], **kwargs)
                while not rc and trycount < self._maxtries:
                    trycount += 1
                    logger.info(
                        "Trying again (retries=%d/%d)...",
                        trycount,
                        self._maxtries,
                    )
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
        for tagain in [x for x in d["_auto_retries"] if x not in bare_methods]:
            inherited = [base for base in b if hasattr(base, tagain)]
            d[tagain] = _tryagain(getattr(inherited[0], tagain))
        # Add the check_fatal decorator...
        for cfatal in [
            x for x in d["_auto_checkfatal"] if x not in bare_methods
        ]:
            inherited = [base for base in b if hasattr(base, cfatal)]
            d[cfatal] = _check_fatal(
                d.get(cfatal, getattr(inherited[0], cfatal))
            )
        return super().__new__(cls, n, b, d)


class AssistedSsh(Ssh, metaclass=_AssistedSshMeta):
    """Remote command execution via ssh.

    Also handles remote copy via scp or ssh, which is intimately linked.
    Compared to the :class:`Ssh` class it adds:

    - retries capabilities
    - support for multiple hostnames (a hostname is picked up in the hostnames
      list, it is tested and if the test succeeds it is chosen. If not, the next
      hostname is tested, ... and so on).
    - virtual nodes support (i.e. the real hostnames associated with a virtual
      node name are read in the configuration file).

    Examples (`sh` being an :class:`~vortex.tools.systems.OSExtended` object):

    - Basic use::

        >>> ssh1 = AssistedSsh(sh, 'localhost')
        >>> print(ssh1, ssh1.remote)
        <vortex.tools.net.AssistedSsh object at 0x7fac3bb19810> localhost
        >> ssh1.execute("echo -n 'My name is: '; hostname")
        ['My name is: belenoslogin3']

    - Using virtual nodes names (let's consider here that "network" nodes are
      defined in the current target-?.ini configuration file)::

        >>> ssh2 = AssistedSsh(sh, 'network', virtualnode=True)
        >>> print(ssh2, ssh2.targets)  # The list of possible network nodes
        ['belenoslogin0', 'belenoslogin1', 'belenoslogin2', 'belenoslogin3', ]
        >>> print(ssh2, ssh2.remote)  # Pick one randomly
        'belenoslogin2'

    - The multiple retries concept::

        >>> ssh3 = AssistedSsh(sh, 'network', virtualnode=True, maxtries=3)
        >>> print(ssh3, ssh3.remote)  # Pick one randomly
        'belenoslogin0'
        >>> ssh3.execute("false")
        # [2018/02/19-11:29:00][vortex.tools.systems][spawn:0878][WARNING]:
            Bad return code [1] for ['ssh', '-x', 'belenoslogin0', 'false']
        # [2018/02/19-11:29:00][vortex.tools.systems][spawn:0885][WARNING]: Carry on because fatal is off
        # [2018/02/19-11:29:00][vortex.tools.net][wrapped:1296][INFO]: Trying again (retries=2/3)...
        # [2018/02/19-11:29:01][vortex.tools.systems][spawn:0878][WARNING]:
            Bad return code [1] for ['ssh', '-x', 'belenoslogin0', 'false']
        # [2018/02/19-11:29:01][vortex.tools.systems][spawn:0885][WARNING]: Carry on because fatal is off
        # [2018/02/19-11:29:01][vortex.tools.net][wrapped:1296][INFO]: Trying again (retries=3/3)...
        # [2018/02/19-11:29:02][vortex.tools.systems][spawn:0878][WARNING]:
            Bad return code [1] for ['ssh', '-x', 'belenoslogin0', 'false']
        # [2018/02/19-11:29:02][vortex.tools.systems][spawn:0885][WARNING]: Carry on because fatal is off
        # [2018/02/19-11:29:02][vortex.tools.net][wrapped:1268][ERROR]: The maximum number of retries (3) was reached...
        False

    - Raise an exception on failure::

        >>> ssh4 = AssistedSsh(sh, 'network', virtualnode=True,  fatal=True)
        >>> ssh4.execute("false")
        # [2018/02/19-11:29:00][vortex.tools.systems][spawn:0878][WARNING]:
            Bad return code [1] for ['ssh', '-x', 'belenoslogin0', 'false']
        # [2018/02/19-11:29:00][vortex.tools.systems][spawn:0885][WARNING]: Carry on because fatal is off
        # [2018/02/19-11:29:02][vortex.tools.net][wrapped:1268][ERROR]: The maximum number of retries (1) was reached...
        RuntimeError: Could not execute the SSH command.

    """

    _auto_checkfatal = [
        "check_ok",
        "execute",
        "cocoon",
        "remove",
        "scpput",
        "scpget",
        "scpput_stream",
        "scpget_stream",
        "tunnel",
    ]
    # No retries on scpput_stream since it's not guaranteed that the stream is seekable.
    _auto_retries = [
        "check_ok",
        "execute",
        "cocoon",
        "remove",
        "scpput",
        "scpget",
        "tunnel",
    ]

    def __init__(
        self,
        sh,
        hostname,
        logname=None,
        sshopts=None,
        scpopts=None,
        maxtries=1,
        triesdelay=1,
        virtualnode=False,
        permut=True,
        fatal=False,
        mandatory_hostcheck=True,
    ):
        """
        :param System sh: The :class:`System` object that is to be used.
        :param hostname: The target hostname(s).
        :type hostname: str or list
        :param logname: The logname for the Ssh commands.
        :param str sshopts: Extra SSH options (in addition to the configuration file ones).
        :param str scpopts: Extra SCP options (in addition to the configuration file ones).
        :param int maxtries: The maximum number of retries.
        :param int triesdelay: The delay in seconds between retries.
        :param bool virtualnode: If True, the *hostname* is considered to be a
                                 virtual node name. It is therefore looked up in
                                 the configuration file.
        :param bool permut: If True, the hostnames list is shuffled prior to
                            being used.
        :param bool fatal: If True, a RuntimeError exception is raised whenever
                           something fails.
        :param mandatory_hostcheck: If True and several host names are provided,
                                    the hostname is always checked prior to being
                                    used for the real Ssh command. When a single
                                    host name is provided, such a check is never
                                    performed.
        """
        super().__init__(sh, hostname, logname, sshopts, scpopts)
        self._triesdelay = triesdelay
        self._virtualnode = virtualnode
        self._permut = permut
        self._fatal = fatal
        self._mandatory_hostcheck = mandatory_hostcheck
        if self._virtualnode and isinstance(self._remote, (list, tuple)):
            raise ValueError(
                "When virtual nodes are used, the hostname must be a string"
            )

        self._retry_in_progress = False
        self._fatal_in_progress = False
        self._retries = 0
        self._targets = self._setup_targets()
        self._targets_iter = itertools.cycle(self._targets)
        if not self._mandatory_hostcheck and len(self._targets) > 1:
            # Try at least one time with each of the possible targets
            self._maxtries = maxtries + len(self._targets) - 1
        else:
            self._maxtries = maxtries
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
            targets = [self._logname + "@" + x for x in targets]
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
        """Hostname to use for this kind of remote execution."""
        if len(self.targets) == 1:
            # This is simple enough, do not bother testing...
            self._chosen_target = self.targets[0]
        # Ok, let's take self._mandatory_hostcheck into account
        if self._mandatory_hostcheck:
            if self._chosen_target is None:
                for guess in self.targets:
                    cmd = (
                        [
                            self._sshcmd,
                        ]
                        + self._sshopts
                        + [
                            guess,
                            "true",
                        ]
                    )
                    try:
                        self.sh.spawn(cmd, output=False, silent=True)
                    except Exception:
                        pass
                    else:
                        self._chosen_target = guess
                        break
            return self._chosen_target
        else:
            return next(self._targets_iter)


_ConnectionStatusAttrs = (
    "Family",
    "LocalAddr",
    "LocalPort",
    "DestAddr",
    "DestPort",
    "Status",
)
TcpConnectionStatus = namedtuple("TcpConnectionStatus", _ConnectionStatusAttrs)
UdpConnectionStatus = namedtuple("UdpConnectionStatus", _ConnectionStatusAttrs)


class AbstractNetstats(metaclass=abc.ABCMeta):
    """AbstractNetstats classes provide all kind of informations on network connections."""

    @property
    @abc.abstractmethod
    def unprivileged_ports(self):
        """The list of unprivileged port that may be opened by any user."""
        pass

    @abc.abstractmethod
    def tcp_netstats(self):
        """Informations on active TCP connections.

        Returns a list of :class:`TcpConnectionStatus` objects.
        """
        pass

    @abc.abstractmethod
    def udp_netstats(self):
        """Informations on active UDP connections.

        Returns a list of :class:`UdpConnectionStatus` objects.
        """
        pass

    def available_localport(self):
        """Returns the number of an unused unprivileged port."""
        netstats = self.tcp_netstats() + self.udp_netstats()
        busyports = {x.LocalPort for x in netstats}
        busy = True
        while busy:
            guess_port = random.choice(self.unprivileged_ports)
            busy = guess_port in busyports
        return guess_port

    def check_localport(self, port):
        """Check if ``port`` is currently in use."""
        netstats = self.tcp_netstats() + self.udp_netstats()
        busyports = {x.LocalPort for x in netstats}
        return port in busyports


class LinuxNetstats(AbstractNetstats):
    """A Netstats implementation for Linux (based on the /proc/net data)."""

    _LINUX_LPORT = "/proc/sys/net/ipv4/ip_local_port_range"
    _LINUX_PORTS_V4 = {"tcp": "/proc/net/tcp", "udp": "/proc/net/udp"}
    _LINUX_PORTS_V6 = {"tcp": "/proc/net/tcp6", "udp": "/proc/net/udp6"}
    _LINUX_AF_INET4 = socket.AF_INET
    _LINUX_AF_INET6 = socket.AF_INET6

    def __init__(self):
        self.__unprivileged_ports = None

    @property
    def unprivileged_ports(self):
        if self.__unprivileged_ports is None:
            with open(self._LINUX_LPORT) as tmprange:
                tmpports = [int(x) for x in tmprange.readline().split()]
            unports = set(range(5001, 65536))
            self.__unprivileged_ports = sorted(
                unports - set(range(tmpports[0], tmpports[1] + 1))
            )
        return self.__unprivileged_ports

    @classmethod
    def _ip_from_hex(cls, hexip, family=_LINUX_AF_INET4):
        if family == cls._LINUX_AF_INET4:
            packed = struct.pack(b"<I", int(hexip, 16))
        elif family == cls._LINUX_AF_INET6:
            packed = struct.unpack(b">IIII", binascii.a2b_hex(hexip))
            packed = struct.pack(b"@IIII", *packed)
        else:
            raise ValueError("Unknown address family.")
        return socket.inet_ntop(family, packed)

    def _generic_netstats(self, proto, rclass):
        tmpports = dict()
        with open(self._LINUX_PORTS_V4[proto]) as netstats:
            netstats.readline()  # Skip the header line
            tmpports[self._LINUX_AF_INET4] = [
                re.split(r":\b|\s+", x.strip())[1:6]
                for x in netstats.readlines()
            ]
        try:
            with open(self._LINUX_PORTS_V6[proto]) as netstats:
                netstats.readline()  # Skip the header line
                tmpports[self._LINUX_AF_INET6] = [
                    re.split(r":\b|\s+", x.strip())[1:6]
                    for x in netstats.readlines()
                ]
        except OSError:
            # Apparently, no IPv6 support on this machine
            tmpports[self._LINUX_AF_INET6] = []
        tmpports = [
            [
                rclass(
                    family,
                    self._ip_from_hex(l[0], family),
                    int(l[1], 16),
                    self._ip_from_hex(l[2], family),
                    int(l[3], 16),
                    int(l[4], 16),
                )
                for l in tmpports[family]
            ]
            for family in (self._LINUX_AF_INET4, self._LINUX_AF_INET6)
        ]
        return functools.reduce(operator.add, tmpports)

    def tcp_netstats(self):
        return self._generic_netstats("tcp", TcpConnectionStatus)

    def udp_netstats(self):
        return self._generic_netstats("udp", UdpConnectionStatus)
