#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import tempfile

import footprints
from vortex.tools import addons
from vortex.tools.systems import fmtshcmd
from vortex.tools.grib import GRIB_Tool
from vortex.tools.folder import FolderShell
from vortex.tools.lfi import LFI_Tool_Raw, LFI_Status
from .interfaces import ECfs

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


def use_in_shell(sh, **kw):
    """Extend current shell with the LFI interface defined by optional arguments."""
    kw['shell'] = sh
    return footprints.proxy.addon(**kw)


class ECfsError(Exception):
    """Generic ECfs error"""
    pass


class ECfsConfigurationError(ECfsError):
    """Generic ECfs configuration error"""
    pass


class ECfsTools(addons.FtrawEnableAddon):
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
        """
        Test a state of the file provided using ECfs.
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
        """
        List the files at a location using ECfs.
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

    def ecfscp(self, source, target, options=None):
        """
        Copy the source file to the target using Ecfs.
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
        """
        Get a resource using ECfs (default class).
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
            ctarget = target + "tmp"
            rc, dict_args = self.ecfscp(source=source,
                                        target=ctarget,
                                        options=options)
            rc = rc and cpipeline.file2uncompress(source=ctarget,
                                                  destination=target)
            return rc, dict_args

    @fmtshcmd
    def ecfsput(self, source, target, cpipeline=None, options=None):
        """
        Put a resource using ECfs (default class).
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
            csource = source + "tmp"
            rc1 = cpipeline.compress2file(source=source,
                                          target=csource)
            rc, dict_args = self.ecfscp(source=csource,
                                        target=target,
                                        options=options)
            rc = rc and rc1
            return rc, dict_args

    @fmtshcmd
    def ecfsrm(self, item, options):
        """
        Delete a file or directory using ECfs.
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


class ECfsGRIB_Tool(GRIB_Tool):
    """
    Handle Grib files transfers via ECfs at ECMWF
    """
    _footprint = dict(
        info = 'ECfs grib system interface',
        attr = dict(
            kind = dict(
                values   = ['grib_ecfs'],
            )
        ),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX
        )
    )

    def grib_ecfsput(self, source, target, cpipeline=None, options=None):
        """
        Put a grib resource using ECfs.
        :param source: source file
        :param target: target file
        :param cpipeline: compression pipeline used, if provided
        :param options: list of options to be used
        :return: return code and additional attributes used
        """
        if self.is_xgrib(source):
            if cpipeline is not None:
                raise IOError("It's not allowed to compress xgrib files.")
            psource = source + ".tmp"
            rc1 = self.xgrib_pack(source=source,
                                  destination=psource)
            rc, dict_args = self.sh.ecfsput(source=psource,
                                            target=target,
                                            options=options)
            rc = rc and rc1 and self.sh.rm(psource)
            return rc, dict_args
        else:
            return self.sh.ecfsput(source=source,
                                   target=target,
                                   options=options,
                                   cpipeline=cpipeline)


class ECfsFolderShell(FolderShell):
    """
    Abstract class to handle ECfs transfers of Folders objects
    """
    _footprint = dict(
        info = 'Tools to manipulate folders via ECfs',
        attr = dict(
            kind = dict(
                values   = ['folder_ecfs'],
            )
        ),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX
        )
    )

    def _folder_ecfsget(self, source, target, cpipeline=None, options=None):
        """
        Get a folder resource using ECfs.
        :param source: source file
        :param target: target file
        :param cpipeline: compression pipeline to be used, if provided
        :param options: list of options to be used
        :return: return code and additional attributes used
        """
        # The folder must not be compressed
        if cpipeline is not None:
            raise IOError("It's not allowed to compress folder like data.")
        ctarget = target + ".tgz"
        source, target = self._folder_preftget(source, target)
        # Create a local directory, get the source file and untar it
        loccwd = self.sh.getcwd()
        loctmp = tempfile.mkdtemp(prefix="folder_", dir=loccwd)
        with self.sh.cdcontext(loctmp, create=True):
            rc, dict_args = self.sh.ecfsget(source=source,
                                            target=ctarget,
                                            options=options)
            rc = rc and self.sh.untar(ctarget)
            rc = rc and self.sh.rm(ctarget)
            self._folder_postftget(target, loccwd, loctmp)
        return rc, dict_args

    def _folder_ecfsput(self, source, target, cpipeline=None, options=None):
        """
        Put a folder resource using ECfs.
        :param source: source file
        :param target: target file
        :param cpipeline: compression pipeline to be used, if provided
        :param options: list of options to be used
        :return: return code and additional attributes used
        """
        if cpipeline is not None:
            raise IOError("It's not allowed to compress folder like data.")
        if not target.endswith('.tgz'):
            target += ".tgz"
        source = self.sh.path.abspath(source)
        csource = source + ".tgz"
        rc1 = self.sh.tar(source)
        rc, dict_args = self.sh.ecfsput(source=csource,
                                        target=target,
                                        options=options)
        rc = rc and rc1 and self.sh.rm(csource)
        return rc, dict_args


class ECfs_LFI_Tool_Raw(LFI_Tool_Raw):
    """
    Abstract class to handle ECfs transfers of LFI objects.
    """
    _footprint = dict(
        info = 'ECfs LFI system interface',
        attr = dict(
            kind = dict(
                values   = ['lfi_ecfs'],
            )
        ),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX
        )
    )

    def _std_ecfsput(self, source, target, cpipeline=None, options=None):
        """
        TODO: define xlfi_pack in the parent class
        :param source: source file
        :param target: target file
        :param cpipeline: compression pipeline to be used, if provided
        :param options: list of options to be used
        :return: return code and additional attributes used
        """
        if self.is_xlfi(source):
            if cpipeline is not None:
                raise IOError("It's not allowed to compress xlfi files.")
            psource = source + ".tmp"
            rc1 = LFI_Status()
            rc1 = rc1 and self.xlfi_pack(source=source,
                                         destination=psource)
            rc, dict_args = self.sh.ecfsput(source=psource,
                                            target=target,
                                            options=options)
            rc = rc and rc1 and self.sh.rm(psource)
            return rc, dict_args
        else:
            return self.sh.ecfsput(source=source,
                                      target=target,
                                      options=options,
                                      cpipeline=cpipeline)

    fa_ecfsput = lfi_ecfsput = _std_ecfsput
