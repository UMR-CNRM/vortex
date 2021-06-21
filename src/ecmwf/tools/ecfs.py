# -*- coding: utf-8 -*-

"""
System Addons to support ECMWF' ECFS archiving system.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
import footprints

from vortex.tools import addons
from vortex.tools.systems import fmtshcmd
from .interfaces import ECfs

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def use_in_shell(sh, **kw):
    """Extend current shell with the ECfs interface defined by optional arguments."""
    kw['shell'] = sh
    return footprints.proxy.addon(**kw)


class ECfsError(Exception):
    """Generic ECfs error"""
    pass


class ECfsConfigurationError(ECfsError):
    """Generic ECfs configuration error"""
    pass


class ECfsTools(addons.Addon):
    """
    Handle ECfs use properly within Vortex.
    """
    _footprint = dict(
        info = 'Default ECfs system interface',
        attr = dict(
            kind = dict(
                values   = ['ecfs'],
            ),
        )
    )

    def ecfstest(self, item, options=None):
        """Test a state of the file provided using ECfs.

        :param item: file to be tested
        :param options: list of options to be used by the test (default "r": test existence)
        :return: return code and additional attributes used
        """
        ecfs = ECfs(system=self.sh)
        command = "etest"
        list_args = [item, ]
        if options is None:
            list_options = ["r", ]
        else:
            list_options = options
        rc = ecfs(command=command,
                  list_args=list_args,
                  dict_args=dict(),
                  list_options=list_options)
        return rc, dict()

    def ecfsls(self, location, options):
        """List the files at a location using ECfs.

        :param location: location the contents of which should be listed
        :param options: list of options to be used (default: "l").
        :return: return code and additional attributes used
        """
        ecfs = ECfs(system=self.sh)
        command = "els"
        list_args = [location, ]
        if options is None:
            list_options = ["l", ]
        else:
            list_options = options
        rc = ecfs(command=command,
                  list_args=list_args,
                  dict_args=dict(),
                  list_options=list_options)
        return rc, dict()

    @fmtshcmd
    def ecfscp(self, source, target, options=None):
        """Copy the source file to the target using Ecfs.

        :param source: source file to be copied
        :param target: target file
        :param options: list of options to be used (default none)
        :return: return code and additional attributes used
        """
        ecfs = ECfs(system=self.sh)
        command = "ecp"
        list_args = [source, target]
        if options is None:
            list_options = list()
        else:
            list_options = options
        rc = ecfs(command=command,
                  list_args=list_args,
                  dict_args=dict(),
                  list_options=list_options)
        return rc, dict()

    @fmtshcmd
    def ecfsget(self, source, target, cpipeline=None, options=None):
        """Get a resource using ECfs (default class).

        :param source: file to be copied
        :param target: target file
        :param cpipeline: compression pipeline used, if provided
        :param options: options to be used
        :return: return code and additional attributes used
        """
        if cpipeline is None:
            return self.ecfscp(source=source,
                               target=target,
                               options=options)
        else:
            ctarget = target + self.sh.safe_filesuffix()
            try:
                rc, dict_args = self.ecfscp(source=source,
                                            target=ctarget,
                                            options=options)
                rc = rc and cpipeline.file2uncompress(source=ctarget,
                                                      destination=target)
            finally:
                self.sh.rm(ctarget)
            return rc, dict_args

    @fmtshcmd
    def ecfsput(self, source, target, cpipeline=None, options=None):
        """Put a resource using ECfs (default class).

        :param source: file to be copied
        :param target: target file
        :param cpipeline: compression pipeline used, if provided
        :param options: options to be used
        :return: return code and additional attributes used
        """
        if cpipeline is None:
            return self.ecfscp(source=source,
                               target=target,
                               options=options)
        else:
            csource = source + self.sh.safe_filesuffix()
            try:
                rc1 = cpipeline.compress2file(source=source,
                                              target=csource)
                rc, dict_args = self.ecfscp(source=csource,
                                            target=target,
                                            options=options)
            finally:
                self.sh.rm(csource)
            rc = rc and rc1
            return rc, dict_args

    @fmtshcmd
    def ecfsrm(self, item, options):
        """Delete a file or directory using ECfs.

        :param item: file or directory to be deleted
        :param options: list of options to be used (default none)
        :return: return code and additional attributes used
        """
        ecfs = ECfs(system=self.sh)
        command = "erm"
        list_args = [item, ]
        if options is None:
            list_options = list()
        else:
            list_options = options
        if ecfs:
            rc = ecfs(command=command,
                      list_args=list_args,
                      dict_args=dict(),
                      list_options=list_options)
        return rc, dict()
