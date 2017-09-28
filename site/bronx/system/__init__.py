#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
*system* sub-module:

System related tools.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from six import StringIO
import netrc
import ftplib
import re
import uuid
import os
import sys
from contextlib import contextmanager

import footprints.loggers

logger = footprints.loggers.getLogger(__name__)

#: No automatic export
__all__ = []

from . import cpus_tool
from . import interrupt


def mf_prestage(resource_paths, mail=None,
                archive_machine='hendrix',
                stagedir='/DemandeMig/ChargeEnEspaceRapide'):
    """
    Puts a pre-staging request on **archive_machine** for the given list of
    resources **resource_paths**, and return the path to the submitted request
    file.

    :param resource_paths: list of paths to requested resources
    :param mail: if given, used for informing about the request progress.
    :param archive_machine: name of the archive machine. Will probably not work
                            for other than *hendrix* for now...
    :param stagedir: directory in which prestaging request are to be put
                     on **archive_machine**

    .. note::
        Uses *~/.netrc* to connect to **archive_machine**.
    """
    # build request
    if mail is not None:
        if re.match('([a-zA-Z\-]+)\.([a-zA-Z\-]+)\@meteo.fr', mail):
            request = ["#MAIL=" + mail + '\n', ]
        else:
            logger.warning('invalid **mail** format: ' + mail)
            request = []
    else:
        request = []
    request += [r + '\n' for r in resource_paths]
    # connect to archive
    try:
        (_login, _, _passwd) = netrc.netrc().authenticators(archive_machine)
    except TypeError:
        if netrc.netrc().authenticators(archive_machine) is None:
            raise IOError("host " + archive_machine + " is unknown in .netrc")
        else:
            raise
    ftp = ftplib.FTP(archive_machine)
    ftp.login(_login, _passwd)
    # send request
    request_filename = '.'.join([_login,
                                 'staging_request',
                                 uuid.uuid4().hex[:8],  # [:8] safe enough ?
                                 'MIG'])
    f = StringIO()
    f.writelines(request)
    f.seek(0)
    ftp.cwd(stagedir)
    ftp.storbinary('STOR ' + request_filename, f)
    f.close()
    ftp.quit()
    # send back request identifier
    return '/'.join([stagedir, request_filename])


@contextmanager
def stdout_redirected(to=os.devnull):
    """
    Redirect *sys.stdout* to **to**.

    Usage::

        with stdout_redirected(to=filename):
            print("from Python")
            import os
            os.system("echo non-Python applications are also supported")
    """
    return redirected_stdio(module=sys, stdio='stdout', to=to)


@contextmanager
def stderr_redirected(to=os.devnull):
    """
    Redirect *sys.stderr* to **to**.

    Cf. :func:`stdout_redirected()` for usage.
    """
    return redirected_stdio(module=sys, stdio='stderr', to=to)


def redirected_stdio(module=sys, stdio='stdout', to=os.devnull):
    """
    Redirect **module.stdio** to **to**,
    e.g. (default): *sys.stdout* to *os.devnull*

    Usage::

        with _redirected_stdio(sys, out='stdout', to=filename):
            print("from Python")
            import os
            os.system("echo non-Python applications are also supported")

    Inspired from:
    `<http://stackoverflow.com/questions/5081657/how-do-i-prevent-a-c-shared-library-to-print-on-stdout-in-python>`
    """
    fd = getattr(module, stdio).fileno()

    def _redirect_stdout(to):
        getattr(module, stdio).close()  # + implicit flush()
        os.dup2(to.fileno(), fd)  # fd writes to 'to' file
        setattr(module, stdio, os.fdopen(fd, 'w'))  # Python writes to fd
    with os.fdopen(os.dup(fd), 'w') as old_stdio:
        with open(to, 'w') as f:
            _redirect_stdout(f)
        try:
            yield  # allow code to be run with the redirected stdio
        finally:
            _redirect_stdout(to=old_stdio)  # restore stdio.
