"""
System Addons to support ECMWF' EcTrans data transfert tool.
"""

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
    """Extend current shell with the ECtrans interface defined by optional arguments."""
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
            if actual_setting_key is not None:
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
        return self._get_ectrans_setting(option='gateway',
                                         guess=gateway,
                                         inifile=inifile)

    def ectrans_remote_init(self, remote=None, inifile=None, storage="default"):
        """Initialize the remote attribute used by Ectrans.

        :param remote: remote used if provided
        :param inifile: configuration file in which the remote is read if provided
        :param storage: the store place
        :return: the remote to be used by ECtrans
        """
        try:
            return self._get_ectrans_setting(option='remote_{:s}'.format(storage),
                                             guess=remote,
                                             inifile=inifile)
        except ECtransConfigurationError:
            if storage != 'default':
                return self._get_ectrans_setting(option='remote_default',
                                                 guess=remote,
                                                 inifile=inifile)
            else:
                raise

    @staticmethod
    def ectrans_defaults_init(** kwargs):
        """Initialise the default for ECtrans.

        :return: the different structures used by the ECtrans interface initialised
        """
        sync = kwargs.pop('sync', True)
        list_args = list()
        dict_args = dict()
        list_options = list()
        for k, v in kwargs.items():
            if isinstance(v, bool) and v:
                list_options.append(k)
            else:
                dict_args[k] = v
        if sync:
            dict_args.setdefault("priority", 80)
            dict_args.setdefault("retryCnt", 0)
        else:
            dict_args.setdefault("priority", 30)
            dict_args.setdefault("retryCnt", 72)  # Retry for 12 hours
            dict_args.setdefault("retryFrq", 600)  # 10 minutes between tries
        if 'verbose' not in kwargs:
            list_options.append('verbose')
        if 'overwrite' not in kwargs:
            list_options.append('overwrite')
        return list_args, list_options, dict_args

    def raw_ectransput(self, source, target, gateway=None, remote=None,
                       sync=False, ** kwargs):
        """Put a resource using ECtrans (default class).

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param bool sync: If False, allow asynchronous transfers.
        :return: return code
        """
        ectrans = ECtrans(system=self.sh)
        list_args, list_options, dict_args = self.ectrans_defaults_init(sync=sync,
                                                                        ** kwargs)
        if sync:
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
        return rc

    @fmtshcmd
    def ectransput(self, source, target, gateway=None, remote=None,
                   cpipeline=None, sync=False):
        """Put a resource using ECtrans.

        This class is not used if a particular method format_ectransput exists.

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline used if provided
        :param bool sync: If False, allow asynchronous transfers.
        :return: return code
        """
        if self.sh.is_iofile(source):
            if cpipeline is None:
                rc = self.raw_ectransput(source=source,
                                         target=target,
                                         gateway=gateway,
                                         remote=remote,
                                         sync=sync)
            else:
                csource = source + self.sh.safe_filesuffix()
                try:
                    cpipeline.compress2file(source=source,
                                            destination=csource)
                    rc = self.raw_ectransput(source=csource,
                                             target=target,
                                             gateway=gateway,
                                             remote=remote,
                                             sync=sync)
                finally:
                    self.sh.rm(csource)
        else:
            raise OSError('No such file or directory: {!r}'.format(source))
        return rc

    def raw_ectransget(self, source, target, gateway, remote):
        """Get a resource using ECtrans (default class).

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :return: return code
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
        return rc

    @fmtshcmd
    def ectransget(self, source, target, gateway=None, remote=None, cpipeline=None):
        """Get a resource using ECtrans.

        This class is not used if a particular method format_ectransput exists.

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline to be used if provided
        :return: return code
        """
        if isinstance(target, str):
            self.sh.rm(target)
        if cpipeline is None:
            rc = self.raw_ectransget(source=source,
                                     target=target,
                                     gateway=gateway,
                                     remote=remote)
        else:
            ctarget = target + self.sh.safe_filesuffix()
            try:
                rc = self.raw_ectransget(source=source,
                                         target=ctarget,
                                         gateway=gateway,
                                         remote=remote)
                rc = rc and cpipeline.file2uncompress(source=ctarget,
                                                      destination=target)
            finally:
                self.sh.rm(ctarget)
        return rc
