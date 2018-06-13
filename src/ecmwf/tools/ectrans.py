#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import six
import tempfile

import footprints
from vortex.tools import addons
from vortex.tools.systems import fmtshcmd
from vortex.tools.grib import GRIB_Tool
from vortex.tools.folder import FolderShell
from vortex.tools.lfi import LFI_Tool_Raw, LFI_Status
from .interfaces import ECtrans
from vortex import proxy
from vortex.util.config import GenericConfigParser

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


def use_in_shell(sh, **kw):
    """Extend current shell with the LFI interface defined by optional arguments."""
    kw['shell'] = sh
    return footprints.proxy.addon(**kw)


class ECtransError(Exception):
    """Generic ECtrans error"""
    pass


class ECtransConfigurationError(ECtransError):
    """Generic ECtrans configuration error"""
    pass


class ECtransTools(addons.FtrawEnableAddon):
    """
    Handle ECtrans use properly within Vortex.
    """
    _footprint = dict(
        info = 'Default ECtrans system interface',
        attr = dict(
            kind = dict(
                values   = ['ectrans'],
            ),
        )
    )

    def ectrans_gateway_init(self, gateway=None, inifile=None):
        """
        Initialize the gateway attribute used by ECtrans.
        :param gateway: gateway used if provided
        :param inifile: configuration file in which the gateway is read if provided
        :return: the gateway to be used by ECtrans
        """
        actual_gateway = gateway
        if actual_gateway is None:
            actual_inifile = inifile
            actual_gateway_key = None
            if actual_inifile is not None:
                actual_config = GenericConfigParser(inifile=actual_inifile)
                actual_gateway_key = actual_config.get("ectrans", "gateway")
            if actual_gateway_key is not None:
                actual_gateway = self.sh.env[actual_gateway_key]
            if actual_gateway is None:
                actual_inifile = proxy.target().inifile
                if actual_inifile is None:
                    raise ECtransConfigurationError("Could not find a proper configuration file.")
                else:
                    actual_config = GenericConfigParser(inifile=actual_inifile)
                    actual_gateway_key = actual_config.get("ectrans", "gateway")
                    if actual_gateway_key is not None:
                        actual_gateway = self.sh.env[actual_gateway_key]
                    if actual_gateway is None:
                        raise ECtransConfigurationError("Could not find a proper value for ECtrans gateway.")
        return actual_gateway

    def ectrans_remote_init(self, remote=None, inifile=None, storage="default"):
        """
        Initialize the remote attribute used by Ectrans.
        :param remote: remote used if provided
        :param inifile: configuration file in which the remote is read if provided
        :param storage: the store place
        :return: the remote to be used by ECtrans
        """
        actual_remote = remote
        if actual_remote is None:
            actual_inifile = inifile
            actual_remote_key = None
            if actual_inifile is not None:
                actual_config = GenericConfigParser(inifile=actual_inifile)
                actual_remote_key = actual_config.get("ectrans", "remote_{}".format(storage))
            if actual_remote_key is not None:
                actual_remote = self.sh.env[actual_remote_key]
            elif storage != "default" and actual_inifile is not None:
                actual_remote_key = actual_config.get("ectrans", "remote_default")
            if actual_remote_key is not None:
                actual_remote = self.sh.env[actual_remote_key]
            if actual_remote is None:
                actual_inifile = proxy.target().inifile
                if actual_inifile is None:
                    raise ECtransConfigurationError("Could not find a proper configuration file.")
                else:
                    actual_config = GenericConfigParser(inifile=actual_inifile)
                    actual_remote_key = actual_config.get("ectrans", "remote_{}".format(storage))
                    if actual_remote_key is not None:
                        actual_remote = self.sh.env[actual_remote_key]
                    elif storage != "default":
                        actual_remote_key = actual_config.get("ectrans", "remote_default")
                    if actual_remote_key is not None:
                        actual_remote = self.sh.env[actual_remote_key]
                    if actual_remote is None:
                        raise ECtransConfigurationError("Could not find a proper value for ECtrans remote.")
        return actual_remote

    @staticmethod
    def ectrans_defaults_init():
        """
        Initialise the default for ECtrans.
        :return: the different structures used by the ECtrans interface initialised
        """
        list_args = list()
        dict_args = dict()
        dict_args["delay"] = '120'
        dict_args["priority"] = 60
        dict_args["retryCnt"] = 0
        list_options = ["verbose", "overwrite"]
        return list_args, list_options, dict_args

    def raw_ectransput(self, source, target, gateway=None, remote=None):
        """
        Put a resource using ECtrans (default class).
        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :return: return code and additional attributes used
        """
        ectrans = ECtrans(system=self.sh)
        list_args, list_options, dict_args = self.ectrans_defaults_init()
        list_options.append("put")
        dict_args["gateway"] = gateway
        dict_args["remote"] = remote
        dict_args["source"] = source
        dict_args["target"] = target
        rc = ectrans(
            list_args=list_args,
            list_options=list_options,
            dict_args=dict_args
        )
        del dict_args["source"]
        del dict_args["target"]
        return rc, dict_args

    @fmtshcmd
    def ectransput(self, source, target, gateway=None, remote=None, cpipeline=None):
        """
        Put a resource using ECtrans.
        This class is not used if a particular method format_ectransput exists.
        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline used if provided
        :return: return code and additional attributes used
        """
        if self.is_iofile(source):
            if cpipeline is None:
                rc, dict_args = self.raw_ectransput(source=source,
                                                    target=target,
                                                    gateway=gateway,
                                                    remote=remote)
            else:
                csource = source + ".tmp"
                cpipeline.compress2file(source=source,
                                        destination=csource)
                rc, dict_args = self.raw_ectransput(source=csource,
                                                    target=target,
                                                    gateway=gateway,
                                                    remote=remote)
        else:
            raise IOError('No such file or directory: {!r}'.format(source))
        return rc, dict_args

    def raw_ectransget(self, source, target, gateway, remote):
        """
        Get a resource using ECtrans (default class).
        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :return: return code and additional attributes used
        """
        ectrans = ECtrans(system=self.sh)
        list_args, list_options, dict_args = self.ectrans_defaults_init()
        list_options.append("get")
        dict_args["gateway"] = gateway
        dict_args["remote"] = remote
        dict_args["source"] = source
        dict_args["target"] = target
        rc = ectrans(
            list_args=list_args,
            list_options=list_options,
            dict_args=dict_args
        )
        del dict_args["source"]
        del dict_args["target"]
        return rc

    @fmtshcmd
    def ectransget(self, source, target, gateway=None, remote=None, cpipeline=None):
        """
        Get a resource using ECtrans.
        This class is not used if a particular method format_ectransput exists.
        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline to be used if provided
        :return: return code and additional attributes used
        """
        if isinstance(target, six.string_types):
            self.rm(target)
        if cpipeline is None:
            rc, dict_args = self.raw_ectransget(source=source,
                                                target=target,
                                                gateway=gateway,
                                                remote=remote)
        else:
            ctarget = target + ".tmp"
            rc, dict_args = self.raw_ectransget(source=source,
                                                target=ctarget,
                                                gateway=gateway,
                                                remote=remote)
            rc = rc and cpipeline.file2uncompress(source=ctarget,
                                                  destination=target)
        return rc, dict_args


class ECtransGRIB_Tool(GRIB_Tool):
    """
    Handle Grib files transfers via ECtrans at ECMWF
    """
    _footprint = dict(
        info = 'ECtrans grib system interface',
        attr = dict(
            kind = dict(
                values   = ['grib_ectrans'],
            )
        ),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX
        )
    )

    def grib_ectransput(self, source, target, gateway=None, remote=None, cpipeline=None):
        """
        Put a grib resource using ECtrans.
        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline used, if provided
        :return: return code and additional attributes used
        """
        if self.is_xgrib(source):
            if cpipeline is not None:
                raise IOError("It's not allowed to compress xgrib files.")
            psource = source + ".tmp"
            rc1 = self.xgrib_pack(source=source,
                                  destination=psource)
            rc, dict_args = self.sh.raw_ectransput(source=psource,
                                                   target=target,
                                                   gateway=gateway,
                                                   remote=remote)
            rc = rc and rc1 and self.sh.rm(psource)
            return rc, dict_args
        else:
            return self.sh.ectransput(source=source,
                                      target=target,
                                      gateway=gateway,
                                      remote=remote,
                                      cpipeline=cpipeline)


class ECtransFolderShell(FolderShell):
    """
    Class to handle ECtrans transfers of Folder objects.
    """
    _footprint = dict(
        info = 'Tools to manipulate folders via ECtrans',
        attr = dict(
            kind = dict(
                values   = ['folder_ectrans'],
            )
        ),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX
        )
    )

    def _folder_ectransget(self, source, target, gateway=None, remote=None, cpipeline=None):
        """
        Get a folder resource using ECtrans.
        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline to be used, if provided
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
            rc, dict_args = self.sh.raw_ectransget(source=source,
                                                   target=ctarget,
                                                   gateway=gateway,
                                                   remote=remote)
            rc = rc and self.sh.untar(ctarget)
            rc = rc and self.sh.rm(ctarget)
            self._folder_postftget(target, loccwd, loctmp)
        return rc, dict_args

    def _folder_ectransput(self, source, target, gateway=None, remote=None, cpipeline=None):
        """
        Put a folder resource using ECtrans.
        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline to be used, if provided
        :return: return code and additional attributes used
        """
        if cpipeline is not None:
            raise IOError("It's not allowed to compress folder like data.")
        if not target.endswith('.tgz'):
            target += ".tgz"
        source = self.sh.path.abspath(source)
        csource = source + ".tgz"
        rc1 = self.sh.tar(source)
        rc, dict_args = self.sh.raw_ectransput(source=csource,
                                               target=target,
                                               gateway=gateway,
                                               remote=remote)
        rc = rc and rc1 and self.sh.rm(csource)
        return rc, dict_args


class ECtrans_LFI_Tool_Raw(LFI_Tool_Raw):
    """
    Abstract class to handle ECtrans transfers of LFI objects.
    """
    _footprint = dict(
        info = 'ECtrans LFI system interface',
        attr = dict(
            kind = dict(
                values   = ['lfi_ectrans'],
            )
        ),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX
        )
    )

    def _std_ectransput(self, source, target, gateway=None, remote=None, cpipeline=None):
        """
        TODO: define xlfi_pack in the parent class
        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline to be used, if provided
        :return: return code and additional attributes used
        """
        if self.is_xlfi(source):
            if cpipeline is not None:
                raise IOError("It's not allowed to compress xlfi files.")
            psource = source + ".tmp"
            rc1 = LFI_Status()
            rc1 = rc1 and self.xlfi_pack(source=source,
                                         destination=psource)
            rc, dict_args = self.sh.raw_ectransput(source=psource,
                                                   target=target,
                                                   gateway=gateway,
                                                   remote=remote)
            rc = rc and rc1 and self.sh.rm(psource)
            return rc, dict_args
        else:
            return self.sh.ectransput(source=source,
                                      target=target,
                                      gateway=gateway,
                                      remote=remote,
                                      cpipeline=cpipeline)

    fa_ectransput = lfi_ectransput = _std_ectransput
