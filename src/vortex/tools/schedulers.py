"""
Interface to SMS commands.
"""

import contextlib
import functools

from bronx.fancies import loggers
import footprints

from vortex import config
from .services import Service

__all__ = []

logger = loggers.getLogger(__name__)


class Scheduler(Service):
    """Abstract class for scheduling systems."""

    _abstract = True
    _footprint = dict(
        info="Scheduling service class",
        attr=dict(
            muteset=dict(
                optional=True,
                default=footprints.FPSet(),
                type=footprints.FPSet,
            )
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug("Scheduler init %s", self.__class__)
        super().__init__(*args, **kw)

    @property
    def env(self):
        """Return the current active environment."""
        return self.sh.env

    def cmd_rename(self, cmd):
        """Remap command name. Default is lowercase command name."""
        return cmd.lower()

    def mute(self, cmd):
        """Switch off the given command."""
        self.muteset.add(self.cmd_rename(cmd))

    def play(self, cmd):
        """Switch on the given command."""
        self.muteset.discard(self.cmd_rename(cmd))

    def clear(self):
        """Clear set of mute commands."""
        self.muteset.clear()


class EcmwfLikeScheduler(Scheduler):
    """Abstract class for any ECMWF scheduling systems (SMS, Ecflow)."""

    _abstract = True
    _footprint = dict(
        attr=dict(
            env_pattern=dict(
                info="Scheduler configuration variables start with...",
            ),
            non_critical_timeout=dict(
                info="Timeout in seconds for non-critical commands",
                type=int,
                default=5,
                optional=True,
            ),
        )
    )

    _KNOWN_CMD = ()

    def __init__(self, *args, **kw):
        logger.debug("Scheduler init %s", self.__class__)
        super(Scheduler, self).__init__(*args, **kw)
        self._inside_child_session = False

    def conf(self, kwenv):
        """Possibly export the provided variables and return a dictionary of positioned variables."""
        if kwenv:
            for schedvar in [
                x.upper()
                for x in kwenv.keys()
                if x.upper().startswith(self.env_pattern)
            ]:
                self.env[schedvar] = str(kwenv[schedvar])
        subenv = dict()
        for schedvar in [
            x for x in self.env.keys() if x.startswith(self.env_pattern)
        ]:
            subenv[schedvar] = self.env.get(schedvar)
        return subenv

    def info(self):
        """Dump current defined variables."""
        for schedvar, schedvalue in self.conf(dict()).items():
            print('{:s}="{!s}"'.format(schedvar, schedvalue))

    def __call__(self, *args):
        """By default call the :meth:`info` method."""
        return self.info()

    @contextlib.contextmanager
    def child_session_setup(self):
        """This may be customised in order to setup session related stuff."""
        yield True

    @contextlib.contextmanager
    def child_session(self):
        """Prepare the environment and possibly setup the session.

        It will only clone the environment and call child_session_setup
        once (even if child is called again from within the first child call).
        """
        if not self._inside_child_session:
            self._inside_child_session = True
            try:
                with self.env.clone():
                    with self.child_session_setup() as setup_rc:
                        yield setup_rc
            finally:
                self._inside_child_session = False
        else:
            yield True

    def setup_default(self, *args):
        """Fake method for any missing callback, ie: setup_init, setup_abort, etc."""
        return True

    def close_default(self, *args):
        """Fake method for any missing callback, ie: close_init, close_abort, etc."""
        return True

    @contextlib.contextmanager
    def wrap_actual_child_command(self, kwoptions):
        """Last minute wrap before binary child command."""
        yield True

    def child(self, cmd, *options, **kwoptions):
        """Miscellaneous sms/ecflow child sub-command."""
        rc = None
        cmd = self.cmd_rename(cmd)
        if cmd in self.muteset:
            logger.warning("%s mute command [%s]", self.kind, cmd)
        else:
            with self.child_session() as session_rc:
                if session_rc:
                    if getattr(self, "setup_" + cmd, self.setup_default)(
                        *options
                    ):
                        wrapp_rc = False
                        try:
                            with self.wrap_actual_child_command(
                                kwoptions
                            ) as wrapp_rc:
                                if wrapp_rc:
                                    rc = self._actual_child(
                                        cmd, options, **kwoptions
                                    )
                                else:
                                    logger.warning(
                                        "Actual [%s %s] command wrap failed",
                                        self.kind,
                                        cmd,
                                    )
                        finally:
                            if wrapp_rc:
                                getattr(
                                    self, "close_" + cmd, self.close_default
                                )(*options)
                    else:
                        logger.warning(
                            "Actual [%s %s] command skipped due to setup action",
                            self.kind,
                            cmd,
                        )
                else:
                    logger.warning(
                        "Actual [%s %s] command skipped session setup failure",
                        self.kind,
                        cmd,
                    )
        return rc

    def _actual_child(self, cmd, options, critical=True):
        """The actual child command implementation."""
        raise NotImplementedError("This an abstract method.")

    def __getattr__(self, name):
        """Deal with any known commands."""
        if name in self._KNOWN_CMD:
            return functools.partial(self.child, name)
        else:
            raise AttributeError(name)


class SMS(EcmwfLikeScheduler):
    """
    Client interface to SMS scheduling and monitoring system.
    """

    _footprint = dict(
        info="SMS client service",
        attr=dict(
            kind=dict(
                values=["sms"],
            ),
            rootdir=dict(
                optional=True,
                default=None,
                alias=("install",),
            ),
            env_pattern=dict(
                default="SMS",
                optional=True,
            ),
        ),
    )

    _KNOWN_CMD = (
        "abort",
        "complete",
        "event",
        "init",
        "label",
        "meter",
        "msg",
        "variable",
        "fix",
    )

    def __init__(self, *args, **kw):
        logger.debug("SMS scheduler client init %s", self)
        super().__init__(*args, **kw)
        self._actual_rootdir = self.rootdir
        if self._actual_rootdir is None:
            self._actual_rootdir = (
                self.env.SMS_INSTALL_ROOT
                or config.from_config(section="sms", key="rootdir")
            )
        if self.sh.path.exists(self.cmdpath("init")):
            self.env.setbinpath(self._actual_rootdir)
        else:
            logger.warning(
                "No SMS client found at init time [rootdir:%s]>",
                self._actual_rootdir,
            )

    def cmd_rename(self, cmd):
        """Remap command name. Strip any sms prefix."""
        cmd = super().cmd_rename(cmd)
        while cmd.startswith("sms"):
            cmd = cmd[3:]
        return cmd

    def cmdpath(self, cmd):
        """Return a complete binary path to cmd."""
        cmd = "sms" + self.cmd_rename(cmd)
        if self._actual_rootdir:
            return self.sh.path.join(self._actual_rootdir, cmd)
        else:
            return cmd

    def path(self):
        """Return actual binary path to SMS commands."""
        return self._actual_rootdir

    @contextlib.contextmanager
    def child_session_setup(self):
        """Setup the path to the SMS client."""
        with super().child_session_setup() as setup_rc:
            self.env.SMSACTUALPATH = self._actual_rootdir
            yield setup_rc

    @contextlib.contextmanager
    def wrap_actual_child_command(self, kwoptions):
        """Last minute wrap before binary child command."""
        with super().wrap_actual_child_command(kwoptions) as wrapp_rc:
            upd_env = dict()
            if not kwoptions.get("critical", True):
                upd_env["SMSDENIED"] = 1
                if self.non_critical_timeout:
                    upd_env["SMSTIMEOUT"] = self.non_critical_timeout
            if upd_env:
                with self.env.delta_context(**upd_env):
                    yield wrapp_rc
            else:
                yield wrapp_rc

    def _actual_child(self, cmd, options, critical=True):
        """Miscellaneous smschild subcommand."""
        args = [self.cmdpath(cmd)]
        args.extend(options)
        return self.sh.spawn(args, output=False, fatal=critical)


class SMSColor(SMS):
    """
    Default SMS service with some extra colorful features.
    """

    _footprint = dict(
        info="SMS color client service",
        attr=dict(
            kind=dict(
                values=["smscolor"],
            ),
        ),
    )

    @contextlib.contextmanager
    def wrap_actual_child_command(self, kwoptions):
        """Last minute wrap before binary child command."""
        with super().wrap_actual_child_command(kwoptions) as wrapp_rc:
            print("SMS COLOR")
            yield wrapp_rc


class EcFlow(EcmwfLikeScheduler):
    """
    Client interface to the ecFlow scheduling and monitoring system.
    """

    _footprint = dict(
        info="SMS client service",
        attr=dict(
            kind=dict(
                values=["ecflow"],
            ),
            clientpath=dict(
                info=(
                    "Path to the ecFlow client binary (if omitted, "
                    + "it's read in the configuration file)"
                ),
                optional=True,
                default=None,
            ),
            env_pattern=dict(
                default="ECF_",
                optional=True,
            ),
        ),
    )

    _KNOWN_CMD = (
        "abort",
        "complete",
        "event",
        "init",
        "label",
        "meter",
        "msg",
        "alter",
    )

    def __init__(self, *args, **kw):
        logger.debug("EcFlow scheduler client init %s", self)
        super().__init__(*args, **kw)
        self._actual_clientpath = self.clientpath

    def path(self):
        """Return the actual binary path to the EcFlow client."""
        if self._actual_clientpath is None:
            thistarget = self.sh.default_target
            guesspath = self.env.ECF_CLIENT_PATH or thistarget.get(
                "ecflow:clientpath"
            )
            ecfversion = self.env.get("ECF_VERSION", "default")
            guesspath = guesspath.format(version=ecfversion)
            if guesspath is None:
                logger.warning(
                    "ecFlow service could not guess the install location [%s]",
                    str(guesspath),
                )
            else:
                self._actual_clientpath = guesspath
        if not self.sh.path.exists(self._actual_clientpath):
            logger.warning(
                "No ecFlow client found at init time [path:%s]>",
                self._actual_clientpath,
            )
        return self._actual_clientpath

    @contextlib.contextmanager
    def child_session_setup(self):
        """Setup a SSH tunnel if necessary."""
        with super().child_session_setup() as setup_rc:
            if setup_rc and not self.sh.default_target.isnetworknode:
                tunnel = None
                # wait and retries from config
                thistarget = self.sh.default_target
                sshwait = float(thistarget.get("ecflow:sshproxy_wait", 6))
                sshretries = float(
                    thistarget.get("ecflow:sshproxy_retries", 2)
                )
                sshretrydelay = float(
                    thistarget.get("ecflow:sshproxy_retrydelay", 1)
                )
                # Build up an SSH tunnel to convey the EcFlow command
                ecconf = self.conf(dict())
                echost = ecconf.get("{:s}HOST".format(self.env_pattern), None)
                ecport = ecconf.get("{:s}PORT".format(self.env_pattern), None)
                if not (echost and ecport):
                    setup_rc = False
                else:
                    sshobj = self.sh.ssh(
                        "network",
                        virtualnode=True,
                        mandatory_hostcheck=False,
                        maxtries=sshretries,
                        triesdelay=sshretrydelay,
                    )
                    tunnel = sshobj.tunnel(
                        echost, int(ecport), maxwait=sshwait
                    )
                    if not tunnel:
                        setup_rc = False
                    else:
                        newvars = {
                            "{:s}HOST".format(self.env_pattern): "localhost",
                            "{:s}PORT".format(
                                self.env_pattern
                            ): tunnel.entranceport,
                        }
                        self.env.update(**newvars)
                try:
                    yield setup_rc
                finally:
                    # Close the SSH tunnel regardless of the exit status
                    if tunnel:
                        tunnel.close()
            else:
                yield setup_rc

    @contextlib.contextmanager
    def wrap_actual_child_command(self, kwoptions):
        """Last minute wrap before binary child command."""
        with super().wrap_actual_child_command(kwoptions) as wrapp_rc:
            upd_env = dict()
            if not kwoptions.get("critical", True):
                upd_env["{:s}DENIED".format(self.env_pattern)] = 1
                if self.non_critical_timeout:
                    upd_env["{:s}TIMEOUT".format(self.env_pattern)] = (
                        self.non_critical_timeout
                    )
            if upd_env:
                with self.env.delta_context(**upd_env):
                    yield wrapp_rc
            else:
                yield wrapp_rc

    def _actual_child(self, cmd, options, critical=True):
        """Miscellaneous ecFlow sub-command."""
        args = [
            self.path(),
        ]
        if options:
            args.append("--{:s}={!s}".format(cmd, options[0]))
            if len(options) > 1:
                args.extend(options[1:])
        else:
            args.append("--{:s}".format(cmd))
        args = [str(a) for a in args]
        logger.info("Issuing the ecFlow command: %s", " ".join(args[1:]))
        return self.sh.spawn(args, output=False, fatal=critical)

    def abort(self, *opts):
        """Gateway to :meth:`child` abort method."""
        actual_opts = list(opts)
        if not actual_opts:
            # For backward compatibility with SMS
            actual_opts.append("No abort reason provided")
        return self.child("abort", *actual_opts)
