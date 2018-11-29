#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import six

from bronx.fancies import loggers
import footprints

from vortex.tools import addons
from vortex.tools.systems import fmtshcmd
from .interfaces import ECtrans
from vortex.util.config import GenericConfigParser

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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


class ECtransTools(addons.Addon):
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

    def _get_ectrans_setting(self, option, section='ectrans', guess=None, inifile=None):
        """
        Use the configuration data (from the curent target object or from
        **inifile**) to find out the appropriate configuration setting in the
        environment.

        :param option: The configuration key to look for
        :param section: The configuration section that will be used
        :param guess: gateway used if provided
        :param inifile: configuration file in which the gateway is read if provided
        :return: the appropriate configuration setting

        :note: If the method is unable to find an appropriate value, a
               :class:`ECtransConfigurationError` exception is raised.
        """
        actual_setting = guess
        # Use inifile first (if provided)
        if actual_setting is None and inifile is not None:
            actual_config = GenericConfigParser(inifile=inifile)
            actual_setting_key = None
            if (actual_config.has_section(section) and
                    actual_config.has_option(section, option)):
                actual_setting_key = actual_config.get("ectrans", "gateway")
            if actual_setting_key:
                actual_setting = self.sh.env[actual_setting_key]
        # Use the system's configuration file otherwise
        if actual_setting is None:
            actual_setting_key = self.sh.default_target.get('{:s}:{:s}'.format(section, option),
                                                      None)
            if actual_setting_key:
                actual_setting = self.sh.env[actual_setting_key]
        # Check if it worked ?
        if actual_setting is None:
            raise ECtransConfigurationError("Could not find a proper value for an ECtrans setting ({:s})."
                                            .format(option))
        return actual_setting

    def ectrans_gateway_init(self, gateway=None, inifile=None):
        """Initialize the gateway attribute used by ECtrans.

        :param gateway: gateway used if provided
        :param inifile: configuration file in which the gateway is read if provided
        :return: the gateway to be used by ECtrans
        """
        return self._get_ectrans_setting('gateway', gateway, inifile)

    def ectrans_remote_init(self, remote=None, inifile=None, storage="default"):
        """Initialize the remote attribute used by Ectrans.

        :param remote: remote used if provided
        :param inifile: configuration file in which the remote is read if provided
        :param storage: the store place
        :return: the remote to be used by ECtrans
        """
        try:
            return self._get_ectrans_setting('remote_{:s}'.format(storage), remote, inifile)
        except ECtransConfigurationError:
            if storage != 'default':
                return self._get_ectrans_setting('remote_default', remote, inifile)
            else:
                raise

    @staticmethod
    def ectrans_defaults_init():
        """Initialise the default for ECtrans.

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
        """Put a resource using ECtrans (default class).

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
        """Put a resource using ECtrans.

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
                csource = source + self.sh.safe_filesuffix()
                try:
                    cpipeline.compress2file(source=source,
                                            destination=csource)
                    rc, dict_args = self.raw_ectransput(source=csource,
                                                        target=target,
                                                        gateway=gateway,
                                                        remote=remote)
                finally:
                    self.sh.rm(csource)
        else:
            raise IOError('No such file or directory: {!r}'.format(source))
        return rc, dict_args

    def raw_ectransget(self, source, target, gateway, remote):
        """Get a resource using ECtrans (default class).

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
        return rc, dict_args

    @fmtshcmd
    def ectransget(self, source, target, gateway=None, remote=None, cpipeline=None):
        """Get a resource using ECtrans.

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
            ctarget = target + self.sh.safe_filesuffix()
            try:
                rc, dict_args = self.raw_ectransget(source=source,
                                                    target=ctarget,
                                                    gateway=gateway,
                                                    remote=remote)
                rc = rc and cpipeline.file2uncompress(source=ctarget,
                                                      destination=target)
            finally:
                self.sh.rm(ctarget)
        return rc, dict_args
