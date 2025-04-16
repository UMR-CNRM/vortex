# pylint: disable=unused-argument

"""
Abstract class for any AlgoComponent (:class:`AlgoComponent`) or AlgoComponent's
Mixins (:class:`AlgoComponentDecoMixin`).

Some very generic concrete AlgoComponent classes are also provided:

    * :class:`Expresso`: launch a simple script;
    * :class:`BlindRun`: launch a simple executable (no MPI);
    * :class:`Parallel`: launch an MPI application.

Additional abstract classes provide multiprocessing support (through the
:mod:`taylorism` package):

    * :class:`TaylorRun`: launch a piece of Python code on several processes;
    * :class:`ParaExpresso`: launch a script multiple times (in parallel);
    * :class:`ParaBlindRun`: launch an executable multiple times (in parallel).

Such classes are based on the :mod:`taylorism` (the developer should be familiar
with this package) and uses "Worker" classes provided in the
:mod:`vortex.tools.parallelism` package.

A few examples of AlgoComponent classes are shipped with the code
(see :ref:`examples_algo`). In addition to the documentation provided
in :ref:`stepbystep-index`, it might help.

When class inheritance is not applicable or ineffective, The AlgoComponent's
Mixins are a powerful tool to mutualise some pieces of code. See the
:class:`AlgoComponentDecoMixin` class documentation for more details.
"""

import collections.abc
import contextlib
import copy
import functools
import importlib
import locale
import logging
import multiprocessing
import queue
import shlex
import sys
import tempfile
import traceback as py_traceback

from bronx.fancies import loggers
from bronx.stdtypes import date
from bronx.syntax.decorators import nicedeco
import footprints
from taylorism import Boss
import vortex
import vortex.config as config
from vortex.algo import mpitools
from vortex.syntax.stdattrs import DelayedEnvValue
from vortex.tools.parallelism import ParallelResultParser

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class AlgoComponentError(Exception):
    """Generic exception class for Algo Components."""

    pass


class AlgoComponentAssertionError(AlgoComponentError):
    """Assertion exception class for Algo Components."""

    pass


class DelayedAlgoComponentError(AlgoComponentError):
    """Triggered when exceptions occurred during the execution but were delayed."""

    def __init__(self, excs):
        super().__init__("One or several errors occurred during the run.")
        self._excs = excs

    def __iter__(self):
        yield from self._excs

    def __str__(self):
        outstr = "One or several errors occurred during the run. In order of appearance:\n"
        outstr += "\n".join(
            [
                "{:3d}. {!s} (type: {!s})".format(i + 1, exc, type(exc))
                for i, exc in enumerate(self)
            ]
        )
        return outstr


class ParallelInconsistencyAlgoComponentError(Exception):
    """Generic exception class for Algo Components."""

    def __init__(self, target):
        msg = "The len of {:s} is inconsistent with the number or ResourceHandlers."
        super().__init__(msg.format(target))


@nicedeco
def _clsmtd_mixin_locked(f):
    """
    This is a utility decorator (for class methods) : it ensures that the method can only
    be called on a bare :class:`AlgoComponentDecoMixin` class.
    """

    def wrapped_clsmethod(cls, *kargs, **kwargs):
        if issubclass(cls, AlgoComponent):
            raise RuntimeError(
                "This class method should not be called once the mixin is in use."
            )
        return f(cls, *kargs, **kwargs)

    return wrapped_clsmethod


def algo_component_deco_mixin_autodoc(cls):
    """
    Decorator that adds an automatic documentation on any :class:`AlgoComponentDecoMixin`
    class.
    """
    extradoc = ""

    # Document extra footprints
    if cls.MIXIN_AUTO_FPTWEAK and cls._MIXIN_EXTRA_FOOTPRINTS:
        extradoc += "\nThe following footprints will be applied to the target classes:\n\n"
        for fp in cls._MIXIN_EXTRA_FOOTPRINTS:
            if isinstance(fp, footprints.Footprint):
                extradoc += footprints.doc.format_docstring(
                    fp, footprints.setup.docstrings, abstractfpobj=True
                )
                extradoc += "\n"

    # Document decorating classes
    if cls.MIXIN_AUTO_DECO:
        for what, desc in (
            ("PREPARE_PREHOOKS", "before the original ``prepare`` method"),
            ("PREPARE_HOOKS", "after the original ``prepare`` method"),
            ("POSTFIX_PREHOOKS", "before the original ``postfix`` method"),
            ("POSTFIX_HOOKS", "after the original ``postfix`` method"),
            ("SPAWN_HOOKS", "after the original ``spawn_hook`` method"),
            (
                "CLI_OPTS_EXTEND",
                "to alter the result of the ``spawn_command_options`` method",
            ),
            (
                "STDIN_OPTS_EXTEND",
                "to alter the result of the ``spawn_stdin_options`` method",
            ),
            (
                "_MIXIN_EXECUTE_OVERWRITE",
                "instead of the original ``execute`` method",
            ),
            (
                "MPIBINS_HOOKS",
                "to alter the result of the ``_bootstrap_mpibins_hack`` method",
            ),
            (
                "MPIENVELOPE_HOOKS",
                "to alter the result of the ``_bootstrap_mpienvelope_hack`` method",
            ),
        ):
            what = "_MIXIN_{:s}".format(what)
            if getattr(cls, what, ()):
                extradoc += "\nThe following method(s) will be called {:s}:\n\n".format(
                    desc
                )
                extradoc += "\n".join(
                    "    * {!r}".format(cb) for cb in getattr(cls, what)
                )
                extradoc += "\n"

    if extradoc:
        extradoc = (
            "\n    .. note:: The following documentation is automatically generated. "
            + "From a developer point of view, using the present mixin class "
            + "will result in the following actions:\n"
            + " \n".join(
                ["        " + t if t else "" for t in extradoc.split("\n")]
            )
        )

        if isinstance(getattr(cls, "__doc__", None), str):
            cls.__doc__ += "\n" + extradoc
        else:
            cls.__doc__ = extradoc

    return cls


class AlgoComponentDecoMixin:
    """
    This is the base class for any Mixin class targeting :class:`AlgoComponent`
    classes.

    Like any Mixin class, this Mixin class primary use is to define methods that
    will be available to the child class.

    However, this class will also interact with the :class:`AlgoComponentMeta`
    metaclass to alter the behaviour of the :class:`AlgoComponent` class it is
    used with. Several "alterations" will be made to the resulting
    :class:`AlgoComponent` class.

        * A bunch of footprints' attribute can be added to the resulting class.
          This is controlled by the :data:`MIXIN_AUTO_FPTWEAK` and
          :data:`_MIXIN_EXTRA_FOOTPRINTS` class variables.
          If :data:`MIXIN_AUTO_FPTWEAK` is ``True`` (which is the default), the
          :class:`~footrprints.Footprint` objects listed in the
          :data:`_MIXIN_EXTRA_FOOTPRINTS` tuple will be prepended to the resulting
          :class:`AlgoComponent` class footprint definition.

        * The ``execute`` method of the resulting class can be overwritten by
          the method referenced in the :data:`_MIXIN_EXECUTE_OVERWRITE` class
          variable. This is allowed only if no ``execute`` method is defined
          manually and if no other :class:`AlgoComponentDecoMixin` tries to
          overwrite it as well. If these two conditions are not met, a
          :class:`RuntimeError` exception will be thrown by the the
          :class:`AlgoComponentMeta` metaclass.

        * A bunch of the :class:`AlgoComponent`'s methods can be decorated. This
          is controlled by the :data:`MIXIN_AUTO_DECO` class variable (``True``
          by default) and a bunch of other class variables containing tuples.
          They are described below:

              * :data:`_MIXIN_PREPARE_PREHOOKS`: Tuple of methods that will be
                executed before the original prepare method. Such methods receive
                the same arguments list than the original decorated method.

              * :data:`_MIXIN_PREPARE_HOOKS`: Tuple of methods that will be
                executed after the original prepare method. Such methods receive
                the same arguments list than the original decorated method.

              * :data:`_MIXIN_EXECUTE_FINALISE_HOOKS`: Tuple of method that will
                be executed after any execution (even if the execution failed).

              * :data:`_MIXIN_FAIL_EXECUTE_HOOKS`: Tuple of method that will
                be executed if the execution fails (the original exception
                will be re-raised afterwards)

              * :data:`_MIXIN_POSTFIX_PREHOOKS`: Tuple of methods that will be
                executed before the original postfix method. Such methods receive
                the same arguments list than the original decorated method.

              * :data:`_MIXIN_POSTFIX_HOOKS`: Tuple of methods that will be
                executed after the original postfix method. Such methods receive
                the same arguments list than the original decorated method.

              * :data:`_MIXIN_SPAWN_HOOKS`: Tuple of methods that will be
                executed after the original spawn_hook method. Such methods receive
                the same arguments list than the original decorated method.

              * :data:`_MIXIN_CLI_OPTS_EXTEND`: Tuple of methods that will be
                executed after the original ``spawn_command_options`` method. Such
                method will receive one argument (``self`` set aside): the value
                returned by the original ``spawn_command_options`` method.

              * :data:`_MIXIN_STDIN_OPTS_EXTEND`: Tuple of methods that will be
                executed after the original ``spawn_stdin_options`` method. Such
                method will receive one argument (``self`` set aside): the value
                returned by the original ``spawn_stdin_options`` method.

    """

    MIXIN_AUTO_FPTWEAK = True
    MIXIN_AUTO_DECO = True

    _MIXIN_EXTRA_FOOTPRINTS = ()

    _MIXIN_PREPARE_PREHOOKS = ()
    _MIXIN_PREPARE_HOOKS = ()
    _MIXIN_EXECUTE_FINALISE_HOOKS = ()
    _MIXIN_FAIL_EXECUTE_HOOKS = ()
    _MIXIN_POSTFIX_PREHOOKS = ()
    _MIXIN_POSTFIX_HOOKS = ()
    _MIXIN_SPAWN_HOOKS = ()

    _MIXIN_CLI_OPTS_EXTEND = ()
    _MIXIN_STDIN_OPTS_EXTEND = ()

    _MIXIN_EXECUTE_OVERWRITE = None

    def __new__(cls, *args, **kwargs):
        if not issubclass(cls, AlgoComponent):
            # This class cannot be instanciated by itself !
            raise RuntimeError(
                "< {0.__name__:s} > is a mixin class: it cannot be instantiated.".format(
                    cls
                )
            )
        else:
            return super().__new__(cls)

    @classmethod
    @_clsmtd_mixin_locked
    def mixin_tweak_footprint(cls, fplocal):
        """Update the footprint definition list."""
        for fp in cls._MIXIN_EXTRA_FOOTPRINTS:
            assert isinstance(fp, footprints.Footprint)
            fplocal.insert(0, fp)

    @classmethod
    @_clsmtd_mixin_locked
    def _get_algo_wrapped(
        cls, targetcls, targetmtd, hooks, prehooks=(), reentering=False
    ):
        """Wraps **targetcls**'s **targetmtd** method."""
        orig_mtd = getattr(targetcls, targetmtd)
        if prehooks and reentering:
            raise ValueError(
                "Conflicting values between prehooks and reenterin."
            )

        def wrapped_method(self, *kargs, **kwargs):
            for phook in prehooks:
                phook(self, *kargs, **kwargs)
            rv = orig_mtd(self, *kargs, **kwargs)
            if reentering:
                kargs = [
                    rv,
                ] + list(kargs)
            for phook in hooks:
                rv = phook(self, *kargs, **kwargs)
                if reentering:
                    kargs[0] = rv
            if reentering:
                return rv

        wrapped_method.__name__ = orig_mtd.__name__
        wrapped_method.__doc__ = (orig_mtd.__doc__ or "").rstrip(
            "\n"
        ) + "\n\nDecorated by :class:`{0.__module__:s}{0.__name__:s}`.".format(
            cls
        )
        wrapped_method.__dict__.update(orig_mtd.__dict__)
        return wrapped_method

    @classmethod
    @_clsmtd_mixin_locked
    def mixin_algo_deco(cls, targetcls):
        """
        Applies all the necessary decorators to the **targetcls**
        :class:`AlgoComponent` class.
        """
        if not issubclass(targetcls, AlgoComponent):
            raise RuntimeError(
                "This class can only be mixed in AlgoComponent classes."
            )
        for targetmtd, hooks, prehooks, reenter in [
            (
                "prepare",
                cls._MIXIN_PREPARE_HOOKS,
                cls._MIXIN_PREPARE_PREHOOKS,
                False,
            ),
            ("fail_execute", cls._MIXIN_FAIL_EXECUTE_HOOKS, (), False),
            ("execute_finalise", cls._MIXIN_EXECUTE_FINALISE_HOOKS, (), False),
            (
                "postfix",
                cls._MIXIN_POSTFIX_HOOKS,
                cls._MIXIN_POSTFIX_PREHOOKS,
                False,
            ),
            ("spawn_hook", cls._MIXIN_SPAWN_HOOKS, (), False),
            ("spawn_command_options", cls._MIXIN_CLI_OPTS_EXTEND, (), True),
            ("spawn_stdin_options", cls._MIXIN_STDIN_OPTS_EXTEND, (), True),
        ]:
            if hooks or prehooks:
                setattr(
                    targetcls,
                    targetmtd,
                    cls._get_algo_wrapped(
                        targetcls, targetmtd, hooks, prehooks, reenter
                    ),
                )
        return targetcls

    @classmethod
    @_clsmtd_mixin_locked
    def mixin_execute_overwrite(cls):
        return cls._MIXIN_EXECUTE_OVERWRITE

    @classmethod
    def mixin_execute_companion(cls):
        """Find on which class "super" should be called (if_MIXIN_EXECUTE_OVERWRITE is used)."""
        comp = getattr(cls, "_algo_meta_execute_companion", ())
        if not comp:
            raise RuntimeError("unable to find a suitable companion class")
        return comp


class AlgoComponentMpiDecoMixin(AlgoComponentDecoMixin):
    """
    This is the base class for Mixin class targeting :class:`Parallel`
    classes.

    It inherits all the behaviour of the :class:`AlgoComponentDecoMixin` base
    class. But in addition, it allows to decorate additional :class:`Parallel`'s
    methods using the following class variables:

      * :data:`_MIXIN_MPIBINS_HOOKS`: Tuple of methods that will be
        executed after the original ``_bootstrap_mpibins_hack`` method. Such
        methods will receive five arguments (``self`` set aside):

            * The list of :class:`mpitools.MpiBinaryDescription` objects returned
              by the original ``_bootstrap_mpibins_hack`` method;
            * The list of :class:`mpitools.MpiBinaryDescription` objects as
              provided by the first caller;
            * The list of binary ResourceHandlers as provided to the ``run``
              method;
            * A dictionary of options as provided to the ``run`` method;
            * A boolean indicating if an MPI envelope is provided by the user.

      * :data:`_MIXIN_MPIENVELOPE_HOOKS`: Tuple of methods that will be
        executed after the original ``_bootstrap_mpienvelope_hack`` method. Such
        methods will receive four arguments (``self`` set aside):

            * The list of dictionaries describing the envelope returned
              by the original``_bootstrap_mpienvelope_hack`` method;
            * The list of dictionaries describing the envelope as
              provided by the first caller;
            * The list of binary ResourceHandlers as provided to the ``run``
              method;
            * A dictionary of options as provided to the ``run`` method;
            * The :class:`mpitools.MpiTool` that is used to generate the
              MPI command line

    """

    _MIXIN_MPIBINS_HOOKS = ()
    _MIXIN_MPIENVELOPE_HOOKS = ()
    _MIXIN_MPIENVELOPE_POSTHOOKS = ()

    @classmethod
    @_clsmtd_mixin_locked
    def mixin_algo_deco(cls, targetcls):
        """
        Applies all the necessary decorators to the **targetcls**
        :class:`AlgoComponent` class.
        """
        targetcls = AlgoComponentDecoMixin.mixin_algo_deco(targetcls)
        if not issubclass(targetcls, Parallel):
            raise RuntimeError(
                "This class can only be mixed in Parallel classes."
            )
        for targetmtd, hooks, prehooks, reenter in [
            ("_bootstrap_mpibins_hack", cls._MIXIN_MPIBINS_HOOKS, (), True),
            (
                "_bootstrap_mpienvelope_hack",
                cls._MIXIN_MPIENVELOPE_HOOKS,
                (),
                True,
            ),
            (
                "_bootstrap_mpienvelope_posthack",
                cls._MIXIN_MPIENVELOPE_POSTHOOKS,
                (),
                True,
            ),
        ]:
            if hooks or prehooks:
                setattr(
                    targetcls,
                    targetmtd,
                    cls._get_algo_wrapped(
                        targetcls, targetmtd, hooks, prehooks, reenter
                    ),
                )
        return targetcls


class AlgoComponentMeta(footprints.FootprintBaseMeta):
    """Meta class for building :class:`AlgoComponent` classes.

    In addition of performing footprints' usual stuff, it processes mixin classes
    that derives from the :class:`AlgoComponentDecoMixin` class. See the
    documentation of this class for more details.
    """

    def __new__(cls, n, b, d):
        # Mixin candidates: a mixin must only be dealt with once hence the
        # condition on issubclass(base, AlgoComponent)
        candidates = [
            base
            for base in b
            if (
                issubclass(base, AlgoComponentDecoMixin)
                and not issubclass(base, AlgoComponent)
            )
        ]
        # Tweak footprints
        todobases = [base for base in candidates if base.MIXIN_AUTO_FPTWEAK]
        if todobases:
            fplocal = d.get("_footprint", list())
            if not isinstance(fplocal, list):
                fplocal = [
                    fplocal,
                ]
            for base in todobases:
                base.mixin_tweak_footprint(fplocal)
            d["_footprint"] = fplocal
        # Overwrite the execute method...
        todobases_exc = [
            base
            for base in candidates
            if base.mixin_execute_overwrite() is not None
        ]
        if len(todobases_exc) > 1:
            raise RuntimeError(
                "Cannot overwrite < execute > multiple times: {:s}".format(
                    ",".join([base.__name__ for base in todobases_exc])
                )
            )
        if todobases_exc:
            if "execute" in d:
                raise RuntimeError(
                    "< execute > is already defined in the target class: cannot proceed"
                )
            d["execute"] = todobases_exc[0].mixin_execute_overwrite()
        # Create the class as usual
        fpcls = super().__new__(cls, n, b, d)
        if todobases_exc:
            setattr(fpcls, "_algo_meta_execute_companion", fpcls)
        # Apply decorators
        todobases = [base for base in candidates if base.MIXIN_AUTO_DECO]
        for base in reversed(todobases):
            base.mixin_algo_deco(fpcls)
        return fpcls


class AlgoComponent(footprints.FootprintBase, metaclass=AlgoComponentMeta):
    """Component in charge of any kind of processing."""

    _SERVERSYNC_RAISEONEXIT = True
    _SERVERSYNC_RUNONSTARTUP = True
    _SERVERSYNC_STOPONEXIT = True

    _abstract = True
    _collector = ("component",)
    _footprint = dict(
        info="Abstract algo component",
        attr=dict(
            engine=dict(
                info="The way the executable should be run.",
                values=[
                    "algo",
                ],
            ),
            flyput=dict(
                info="Activate a background job in charge off on the fly processing.",
                type=bool,
                optional=True,
                default=False,
                access="rwx",
                doc_visibility=footprints.doc.visibility.GURU,
                doc_zorder=-99,
            ),
            flypoll=dict(
                info="The system method called by the flyput background job.",
                optional=True,
                default="io_poll",
                access="rwx",
                doc_visibility=footprints.doc.visibility.GURU,
                doc_zorder=-99,
            ),
            flyargs=dict(
                info="Arguments for the *flypoll* method.",
                type=footprints.FPTuple,
                optional=True,
                default=footprints.FPTuple(),
                doc_visibility=footprints.doc.visibility.GURU,
                doc_zorder=-99,
            ),
            flymapping=dict(
                info="Allow renaming of output files during on the fly processing.",
                optional=True,
                default=False,
                access="rwx",
                doc_visibility=footprints.doc.visibility.GURU,
                doc_zorder=-99,
            ),
            timeout=dict(
                info="Default timeout (in sec.) used  when waiting for an expected resource.",
                type=int,
                optional=True,
                default=180,
                doc_zorder=-50,
            ),
            server_run=dict(
                info="Run the executable as a server.",
                type=bool,
                optional=True,
                values=[False],
                default=False,
                access="rwx",
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
            serversync_method=dict(
                info="The method that is used to synchronise with the server.",
                optional=True,
                doc_visibility=footprints.doc.visibility.GURU,
            ),
            serversync_medium=dict(
                info="The medium that is used to synchronise with the server.",
                optional=True,
                doc_visibility=footprints.doc.visibility.GURU,
            ),
            extendpypath=dict(
                info="The list of things to be prepended in the python's path.",
                type=footprints.FPList,
                default=footprints.FPList([]),
                optional=True,
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug("Algo component init %s", self.__class__)
        self._fslog = list()
        self._promises = None
        self._expected = None
        self._delayed_excs = list()
        self._server_synctool = None
        self._server_process = None
        super().__init__(*args, **kw)

    @property
    def realkind(self):
        """Default kind is ``algo``."""
        return "algo"

    @property
    def fslog(self):
        """Changes on the filesystem during the execution."""
        return self._fslog

    def fstag(self):
        """Defines a tag specific to the current algo component."""
        return "-".join((self.realkind, self.engine))

    def fsstamp(self, opts):
        """Ask the current context to put a stamp on file system."""
        self.context.fstrack_stamp(tag=self.fstag())

    def fscheck(self, opts):
        """Ask the current context to check changes on file system since last stamp."""
        self._fslog.append(self.context.fstrack_check(tag=self.fstag()))

    @property
    def promises(self):
        """Build and return list of actual promises of the current component."""
        if self._promises is None:
            self._promises = [
                x
                for x in self.context.sequence.outputs()
                if x.rh.provider.expected
            ]
        return self._promises

    @property
    def expected_resources(self):
        """Return the list of really expected inputs."""
        if self._expected is None:
            self._expected = [
                x
                for x in self.context.sequence.effective_inputs()
                if x.rh.is_expected()
            ]
        return self._expected

    def delayed_exception_add(self, exc, traceback=True):
        """Store the exception so that it will be handled at the end of the run."""
        logger.error("An exception is delayed")
        if traceback:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            print("Exception type: {!s}".format(exc_type))
            print("Exception info: {!s}".format(exc_value))
            print("Traceback:")
            print("\n".join(py_traceback.format_tb(exc_traceback)))
        self._delayed_excs.append(exc)

    def algoassert(self, assertion, msg=""):
        if not assertion:
            raise AlgoComponentAssertionError(msg)

    def grab(self, sec, comment="resource", sleep=10, timeout=None):
        """Wait for a given resource and get it if expected."""
        local = sec.rh.container.localpath()
        self.system.header("Wait for " + comment + " ... [" + local + "]")
        if timeout is None:
            timeout = self.timeout
        if sec.rh.wait(timeout=timeout, sleep=sleep):
            if sec.rh.is_expected():
                sec.get(incache=True)
        elif sec.fatal:
            logger.critical("Missing expected resource <%s>", local)
            raise ValueError("Could not get " + local)
        else:
            logger.error("Missing expected resource <%s>", local)

    def export(self, packenv):
        """Export environment variables in given pack."""
        for k, v in config.from_config(section=packenv).items():
            if k not in self.env:
                logger.info("Setting %s env %s = %s", packenv.upper(), k, v)
                self.env[k] = v

    def prepare(self, rh, opts):
        """Set some defaults env values."""
        if config.is_defined(section="env"):
            self.export("env")

    def absexcutable(self, xfile):
        """Retuns the absolute pathname of the ``xfile`` executable."""
        absx = self.system.path.abspath(xfile)
        return absx

    def flyput_method(self):
        """Check out what could be a valid io_poll command."""
        return getattr(
            self, "io_poll_method", getattr(self.system, self.flypoll, None)
        )

    def flyput_args(self):
        """Return actual io_poll prefixes."""
        return getattr(self, "io_poll_args", tuple(self.flyargs))

    def flyput_kwargs(self):
        """Return actual io_poll prefixes."""
        return getattr(self, "io_poll_kwargs", dict())

    def flyput_check(self):
        """Check default args for io_poll command."""
        actual_args = list()
        if self.flymapping:
            # No checks when mapping is activated
            return self.flyput_args()
        else:
            for arg in self.flyput_args():
                logger.info("Check arg <%s>", arg)
                if any(
                    [
                        x.rh.container.basename.startswith(arg)
                        for x in self.promises
                    ]
                ):
                    logger.info(
                        "Match some promise %s",
                        str(
                            [
                                x.rh.container.basename
                                for x in self.promises
                                if x.rh.container.basename.startswith(arg)
                            ]
                        ),
                    )
                    actual_args.append(arg)
                else:
                    logger.info(
                        "Do not match any promise %s",
                        str([x.rh.container.basename for x in self.promises]),
                    )
            return actual_args

    def flyput_sleep(self):
        """Return a sleeping time in seconds between io_poll commands."""
        return getattr(
            self, "io_poll_sleep", self.env.get("IO_POLL_SLEEP", 20)
        )

    def flyput_outputmapping(self, item):
        """Map output to another filename."""
        return item, "unknown"

    def _flyput_job_internal_search(
        self, io_poll_method, io_poll_args, io_poll_kwargs
    ):
        data = list()
        for arg in io_poll_args:
            logger.info("Polling check arg %s", arg)
            rc = io_poll_method(arg, **io_poll_kwargs)
            try:
                data.extend(rc.result)
            except AttributeError:
                data.extend(rc)
            data = [x for x in data if x]
            logger.info("Polling retrieved data %s", str(data))
        return data

    def _flyput_job_internal_put(self, data):
        for thisdata in data:
            if self.flymapping:
                mappeddata, mappedfmt = self.flyput_outputmapping(thisdata)
                if not mappeddata:
                    raise AlgoComponentError(
                        "The mapping method failed for {:s}.".format(thisdata)
                    )
                if thisdata != mappeddata:
                    logger.info(
                        "Linking <%s> to <%s> (fmt=%s) before put",
                        thisdata,
                        mappeddata,
                        mappedfmt,
                    )
                    self.system.cp(
                        thisdata, mappeddata, intent="in", fmt=mappedfmt
                    )
            else:
                mappeddata = thisdata
            candidates = [
                x
                for x in self.promises
                if x.rh.container.abspath
                == self.system.path.abspath(mappeddata)
            ]
            if candidates:
                logger.info("Polled data is promised <%s>", mappeddata)
                bingo = candidates.pop()
                bingo.put(incache=True)
            else:
                logger.warning("Polled data not promised <%s>", mappeddata)

    def flyput_job(
        self,
        io_poll_method,
        io_poll_args,
        io_poll_kwargs,
        event_complete,
        event_free,
        queue_context,
    ):
        """Poll new data resources."""
        logger.info("Polling with method %s", str(io_poll_method))
        logger.info("Polling with args %s", str(io_poll_args))

        time_sleep = self.flyput_sleep()
        redo = True

        # Start recording the changes in the current context
        ctxrec = self.context.get_recorder()

        while redo and not event_complete.is_set():
            event_free.clear()
            try:
                data = self._flyput_job_internal_search(
                    io_poll_method, io_poll_args, io_poll_kwargs
                )
                self._flyput_job_internal_put(data)
            except Exception as trouble:
                logger.error(
                    "Polling trouble: %s. %s",
                    str(trouble),
                    py_traceback.format_exc(),
                )
                redo = False
            finally:
                event_free.set()
            if redo and not data and not event_complete.is_set():
                logger.info("Get asleep for %d seconds...", time_sleep)
                self.system.sleep(time_sleep)

        # Stop recording and send back the results
        ctxrec.unregister()
        logger.info("Sending the Context recorder to the master process.")
        queue_context.put(ctxrec)
        queue_context.close()

        if redo:
            logger.info("Polling exit on complete event")
        else:
            logger.warning("Polling exit on abort")

    def flyput_begin(self):
        """Launch a co-process to handle promises."""

        nope = (None, None, None, None)
        if not self.flyput:
            return nope

        sh = self.system
        sh.subtitle("On the fly - Begin")

        if not self.promises:
            logger.info("No promise, no co-process")
            return nope

        # Find out a polling method
        io_poll_method = self.flyput_method()
        if not io_poll_method:
            logger.error(
                "No method or shell function defined for polling data"
            )
            return nope

        # Be sure that some default args could match local promises names
        io_poll_args = self.flyput_check()
        if not io_poll_args:
            logger.error("Could not check default arguments for polling data")
            return nope

        # Additional named attributes
        io_poll_kwargs = self.flyput_kwargs()

        # Define events for a nice termination
        event_stop = multiprocessing.Event()
        event_free = multiprocessing.Event()
        queue_ctx = multiprocessing.Queue()

        p_io = multiprocessing.Process(
            name=self.footprint_clsname(),
            target=self.flyput_job,
            args=(
                io_poll_method,
                io_poll_args,
                io_poll_kwargs,
                event_stop,
                event_free,
                queue_ctx,
            ),
        )

        # The co-process is started
        p_io.start()

        return (p_io, event_stop, event_free, queue_ctx)

    def manual_flypolling(self):
        """Call the flyput method and returns the list of newly available files."""
        # Find out a polling method
        io_poll_method = self.flyput_method()
        if not io_poll_method:
            raise AlgoComponentError("Unable to find an io_poll_method")
        # Find out some polling prefixes
        io_poll_args = self.flyput_check()
        if not io_poll_args:
            raise AlgoComponentError("Unable to find an io_poll_args")
        # Additional named attributes
        io_poll_kwargs = self.flyput_kwargs()
        # Starting polling each of the prefixes
        return self._flyput_job_internal_search(
            io_poll_method, io_poll_args, io_poll_kwargs
        )

    def manual_flypolling_job(self):
        """Call the flyput method and deal with promised files."""
        data = self.manual_flypolling()
        self._flyput_job_internal_put(data)

    def flyput_end(self, p_io, e_complete, e_free, queue_ctx):
        """Wait for the co-process in charge of promises."""
        e_complete.set()
        logger.info("Waiting for polling process... <%s>", p_io.pid)
        t0 = date.now()
        e_free.wait(60)
        # Get the Queue and update the context
        time_sleep = self.flyput_sleep()
        try:
            # allow 5 sec to put data into queue (it should be more than enough)
            ctxrec = queue_ctx.get(block=True, timeout=time_sleep + 5)
        except queue.Empty:
            logger.warning("Impossible to get the Context recorder")
            ctxrec = None
        finally:
            queue_ctx.close()
        if ctxrec is not None:
            ctxrec.replay_in(self.context)
        p_io.join(30)
        t1 = date.now()
        waiting = t1 - t0
        logger.info(
            "Waiting for polling process took %f seconds",
            waiting.total_seconds(),
        )
        if p_io.is_alive():
            logger.warning("Force termination of polling process")
            p_io.terminate()
        logger.info("Polling still alive ? %s", str(p_io.is_alive()))
        return not p_io.is_alive()

    def server_begin(self, rh, opts):
        """Start a subprocess and run the server in it."""
        self._server_event = multiprocessing.Event()
        self._server_process = multiprocessing.Process(
            name=self.footprint_clsname(),
            target=self.server_job,
            args=(rh, opts),
        )
        self._server_process.start()

    def server_job(self, rh, opts):
        """Actually run the server and catch all Exceptions.

        If the server crashes, is killed or whatever, the Exception is displayed
        and the appropriate Event is set.
        """
        self.system.signal_intercept_on()
        try:
            self.execute_single(rh, opts)
        except Exception:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            print("Exception type: {!s}".format(exc_type))
            print("Exception info: {!s}".format(exc_value))
            print("Traceback:")
            print("\n".join(py_traceback.format_tb(exc_traceback)))
            # Alert the main process of the error
            self._server_event.set()

    def server_alive(self):
        """Is the server still running ?"""
        return (
            self._server_process is not None
            and self._server_process.is_alive()
        )

    def server_end(self):
        """End the server.

        A first attempt is made to terminate it nicely. If it doesn't work,
        a SIGTERM is sent.
        """
        rc = False
        # This test should always succeed...
        if (
            self._server_synctool is not None
            and self._server_process is not None
        ):
            # Is the process still running ?
            if self._server_process.is_alive():
                # Try to stop it nicely
                if (
                    self._SERVERSYNC_STOPONEXIT
                    and self._server_synctool.trigger_stop()
                ):
                    t0 = date.now()
                    self._server_process.join(30)
                    waiting = date.now() - t0
                    logger.info(
                        "Waiting for the server to stop took %f seconds",
                        waiting.total_seconds(),
                    )
                rc = not self._server_event.is_set()
                # Be less nice if needed...
                if (
                    not self._SERVERSYNC_STOPONEXIT
                ) or self._server_process.is_alive():
                    logger.warning("Force termination of the server process")
                    self._server_process.terminate()
                    self.system.sleep(
                        1
                    )  # Allow some time for the process to terminate
                    if not self._SERVERSYNC_STOPONEXIT:
                        rc = False
            else:
                rc = not self._server_event.is_set()
            logger.info(
                "Server still alive ? %s", str(self._server_process.is_alive())
            )
            # We are done with the server
            self._server_synctool = None
            self._server_process = None
            del self._server_event
            # Check the rc
            if not rc:
                raise AlgoComponentError("The server process ended badly.")
        return rc

    def spawn_pre_dirlisting(self):
        """Print a directory listing just before run."""
        self.system.subtitle(
            "{:s} : directory listing (pre-execution)".format(self.realkind)
        )
        self.system.dir(output=False, fatal=False)

    def spawn_hook(self):
        """Last chance to say something before execution."""
        pass

    def spawn(self, args, opts, stdin=None):
        """
        Spawn in the current system the command as defined in raw ``args``.

        The followings environment variables could drive part of the execution:

          * VORTEX_DEBUG_ENV : dump current environment before spawn
        """
        sh = self.system

        if self.env.true("vortex_debug_env"):
            sh.subtitle(
                "{:s} : dump environment (os bound: {!s})".format(
                    self.realkind, self.env.osbound()
                )
            )
            self.env.osdump()

        # On-the-fly coprocessing initialisation
        p_io, e_complete, e_free, q_ctx = self.flyput_begin()

        sh.remove("core")
        sh.softlink("/dev/null", "core")
        self.spawn_hook()
        self.target.spawn_hook(sh)
        self.spawn_pre_dirlisting()
        sh.subtitle("{:s} : start execution".format(self.realkind))
        try:
            sh.spawn(
                args, output=False, stdin=stdin, fatal=opts.get("fatal", True)
            )
        finally:
            # On-the-fly coprocessing cleaning
            if p_io:
                self.flyput_end(p_io, e_complete, e_free, q_ctx)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict()

    def spawn_command_line(self, rh):
        """Split the shell command line of the resource to be run."""
        opts = self.spawn_command_options()
        return shlex.split(rh.resource.command_line(**opts))

    def spawn_stdin_options(self):
        """Prepare options for the resource's stdin generator."""
        return dict()

    def spawn_stdin(self, rh):
        """Generate the stdin File-Like object of the resource to be run."""
        opts = self.spawn_stdin_options()
        stdin_text = rh.resource.stdin_text(**opts)
        if stdin_text is not None:
            plocale = locale.getlocale()[1] or "ascii"
            tmpfh = tempfile.TemporaryFile(dir=self.system.pwd(), mode="w+b")
            if isinstance(stdin_text, str):
                tmpfh.write(stdin_text.encode(plocale))
            else:
                tmpfh.write(stdin_text)
            tmpfh.seek(0)
            return tmpfh
        else:
            return None

    def execute_single(self, rh, opts):
        """Abstract method.

        When server_run is True, this method is used to start the server.
        Otherwise, this method is called by each :meth:`execute` call.
        """
        pass

    def execute(self, rh, opts):
        """Abstract method."""
        if self.server_run:
            # First time here ?
            if self._server_synctool is None:
                if self.serversync_method is None:
                    raise ValueError("The serversync_method must be provided.")
                self._server_synctool = footprints.proxy.serversynctool(
                    method=self.serversync_method,
                    medium=self.serversync_medium,
                    raiseonexit=self._SERVERSYNC_RAISEONEXIT,
                )
                self._server_synctool.set_servercheck_callback(
                    self.server_alive
                )
                self.server_begin(rh, opts)
                # Wait for the first request
                self._server_synctool.trigger_wait()
                if self._SERVERSYNC_RUNONSTARTUP:
                    self._server_synctool.trigger_run()
            else:
                # Acknowledge that we are ready and wait for the next request
                self._server_synctool.trigger_run()
        else:
            self.execute_single(rh, opts)

    def fail_execute(self, e, rh, kw):
        """This method is called if :meth:`execute` raise an exception."""
        pass

    def execute_finalise(self, opts):
        """Abstract method.

        This method is called inconditionaly when :meth:`execute` exits (even
        if an Exception was raised).
        """
        if self.server_run:
            self.server_end()

    def postfix_post_dirlisting(self):
        self.system.subtitle(
            "{:s} : directory listing (post-run)".format(self.realkind)
        )
        self.system.dir(output=False, fatal=False)

    def postfix(self, rh, opts):
        """Some basic informations."""
        self.postfix_post_dirlisting()

    def dumplog(self, opts):
        """Dump to local file the internal log of the current algo component."""
        self.system.pickle_dump(self.fslog, "log." + self.fstag())

    def delayed_exceptions(self, opts):
        """Gather all the delayed exceptions and raises one if necessary."""
        if len(self._delayed_excs) > 0:
            excstmp = self._delayed_excs
            self._delayed_excs = list()
            raise DelayedAlgoComponentError(excstmp)

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        return True

    def abortfabrik(self, step, msg):
        """A shortcut to avoid next steps of the run."""

        def fastexit(self, *args, **kw):
            logger.warning(
                "Run <%s> skipped because abort occurred [%s]", step, msg
            )

        return fastexit

    def abort(self, msg="Not documented"):
        """A shortcut to avoid next steps of the run."""
        for step in ("prepare", "execute", "postfix"):
            setattr(self, step, self.abortfabrik(step, msg))

    def run(self, rh=None, **kw):
        """Sequence for execution : prepare / execute / postfix."""
        self._status = True

        # Get instance shorcuts to context and system objects
        self.ticket = vortex.sessions.current()
        self.context = self.ticket.context
        self.system = self.context.system
        self.target = kw.pop("target", None)
        if self.target is None:
            self.target = self.system.default_target

        # Before trying to do anything, check the executable
        if not self.valid_executable(rh):
            logger.warning(
                "Resource %s is not a valid executable", rh.resource
            )
            return False

        # A cloned environment will be bound to the OS
        self.env = self.context.env.clone()
        with self.env:
            # The actual "run" recipe
            self.prepare(rh, kw)  # 1
            self.fsstamp(kw)  # 2
            try:
                self.execute(rh, kw)  # 3
            except Exception as e:
                self.fail_execute(e, rh, kw)  # 3.1
                raise
            finally:
                self.execute_finalise(kw)  # 3.2
            self.fscheck(kw)  # 4
            self.postfix(rh, kw)  # 5
            self.dumplog(kw)  # 6
            self.delayed_exceptions(kw)  # 7

        # Free local references
        self.env = None
        self.system = None

        return self._status

    def quickview(self, nb=0, indent=0):
        """Standard glance to objects."""
        tab = "  " * indent
        print("{}{:02d}. {:s}".format(tab, nb, repr(self)))
        for subobj in ("kind", "engine", "interpreter"):
            obj = getattr(self, subobj, None)
            if obj:
                print("{}  {:s}: {!s}".format(tab, subobj, obj))
        print()

    def setlink(
        self,
        initrole=None,
        initkind=None,
        initname=None,
        inittest=lambda x: True,
    ):
        """Set a symbolic link for actual resource playing defined role."""
        initsec = [
            x
            for x in self.context.sequence.effective_inputs(
                role=initrole, kind=initkind
            )
            if inittest(x.rh)
        ]

        if not initsec:
            logger.warning(
                "Could not find logical role %s with kind %s - assuming already renamed",
                initrole,
                initkind,
            )

        if len(initsec) > 1:
            logger.warning(
                "More than one role %s with kind %s", initrole, initkind
            )

        if initname is not None:
            for l in [x.rh.container.localpath() for x in initsec]:
                if not self.system.path.exists(initname):
                    self.system.symlink(l, initname)
                    break

        return initsec


class PythonFunction(AlgoComponent):
    """Execute a function defined in Python module.  The function is passed the
    current :class:`sequence <vortex.layout.dataflow.Sequence>`, as well as a
    keyword arguments described by attribute ``func_kwargs``.  Example:

    .. code-block:: python

        >>> exe = toolbox.executable(
        ...     role           = 'Script',
        ...     format         = 'ascii',
        ...     hostname       = 'localhost',
        ...     kind           = 'script',
        ...     language       = 'python',
        ...     local          = 'module.py',
        ...     remote         = '/path/to/module.py',
        ...     tube           = 'file',
        ... )
        >>> tbalgo = toolbox.algo(
        ...     engine="function",
        ...     func_name="my_plugin_entry_point_function",
        ...     func_kwargs={ntasks: 35, subnproc: 4},
        ... )
        >>> tbalgo.run(exe[0])

    .. code-block:: python

        # /path/to/module.py
        # ...
        def my_plugin_entry_point_function(
            sequence, ntasks, subnproc,
        ):
            for input in sequence.effective_inputs(role=gridpoint):
                # ...
    """

    _footprint = dict(
        info="Execute a Python function in a given module",
        attr=dict(
            engine=dict(values=["function"]),
            func_name=dict(info="The function's name"),
            func_kwargs=dict(
                info=(
                    "A dictionary containing the function's keyword arguments"
                ),
                type=footprints.FPDict,
                default=footprints.FPDict({}),
                optional=True,
            ),
        ),
    )

    def prepare(self, rh, opts):
        spec = importlib.util.spec_from_file_location(
            name="module", location=rh.container.localpath()
        )
        mod = importlib.util.module_from_spec(spec)
        sys.path.extend(self.extendpypath)
        try:
            spec.loader.exec_module(mod)
        except AttributeError:
            raise AttributeError
        self.func = getattr(mod, self.func_name)

    def execute(self, rh, opts):
        self.func(
            self.context.sequence,
            **self.func_kwargs,
        )

    def execute_finalise(self, opts):
        for p in self.extendpypath:
            sys.path.remove(p)


class ExecutableAlgoComponent(AlgoComponent):
    """Component in charge of running executable resources."""

    _abstract = True

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        return rh is not None


class xExecutableAlgoComponent(ExecutableAlgoComponent):
    """Component in charge of running executable resources."""

    _abstract = True

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        rc = super().valid_executable(rh)
        if rc:
            # Ensure that the input file is executable
            xrh = (
                rh
                if isinstance(rh, (list, tuple))
                else [
                    rh,
                ]
            )
            for arh in xrh:
                self.system.xperm(arh.container.localpath(), force=True)
        return rc


class TaylorRun(AlgoComponent):
    """
    Run any taylorism Worker in the current environment.

    This abstract class includes helpers to use the taylorism package in order
    to introduce an external parallelisation. It is designed to work well with a
    taylorism Worker class that inherits from
    :class:`vortex.tools.parallelism.TaylorVortexWorker`.
    """

    _abstract = True
    _footprint = dict(
        info="Abstract algo component based on the taylorism package.",
        attr=dict(
            kind=dict(),
            verbose=dict(
                info="Run in verbose mode",
                type=bool,
                default=False,
                optional=True,
                doc_zorder=-50,
            ),
            ntasks=dict(
                info="The maximum number of parallel tasks",
                type=int,
                default=DelayedEnvValue("VORTEX_SUBMIT_TASKS", 1),
                optional=True,
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._boss = None

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        return dict(kind=self.kind, taskdebug=self.verbose)

    def _default_pre_execute(self, rh, opts):
        """Various initialisations. In particular it creates the task scheduler (Boss)."""
        # Start the task scheduler
        self._boss = Boss(
            verbose=self.verbose,
            scheduler=footprints.proxy.scheduler(
                limit="threads", max_threads=self.ntasks
            ),
        )
        self._boss.make_them_work()

    def _add_instructions(self, common_i, individual_i):
        """Give a new set of instructions to the Boss."""
        self._boss.set_instructions(common_i, individual_i)

    def _default_post_execute(self, rh, opts):
        """Summarise the results of the various tasks that were run."""
        logger.info(
            "All the input files were dealt with: now waiting for the parallel processing to finish"
        )
        self._boss.wait_till_finished()
        logger.info(
            "The parallel processing has finished. here are the results:"
        )
        report = self._boss.get_report()
        prp = ParallelResultParser(self.context)
        for r in report["workers_report"]:
            rc = prp(r)
            if isinstance(rc, Exception):
                self.delayed_exception_add(rc, traceback=False)
                rc = False
            self._default_rc_action(rh, opts, r, rc)

    def _default_rc_action(self, rh, opts, report, rc):
        """How should we process the return code ?"""
        if not rc:
            logger.warning(
                "Apparently something went sideways with this task (rc=%s).",
                str(rc),
            )

    def execute(self, rh, opts):
        """
        This should be adapted to your needs...

        A usual sequence is::

            self._default_pre_execute(rh, opts)
            common_i = self._default_common_instructions(rh, opts)
            # Update the common instructions
            common_i.update(dict(someattribute='Toto', ))

            # Your own code here

            # Give some instructions to the boss
            self._add_instructions(common_i, dict(someattribute=['Toto', ],))

            # Your own code here

            self._default_post_execute(rh, opts)

        """
        raise NotImplementedError


class Expresso(ExecutableAlgoComponent):
    """Run a script resource in the good environment."""

    _footprint = dict(
        info="AlgoComponent that simply runs a script",
        attr=dict(
            interpreter=dict(
                info="The interpreter needed to run the script.",
                values=["current", "awk", "ksh", "bash", "perl", "python"],
            ),
            interpreter_path=dict(
                info="The interpreter command.",
                optional=True,
            ),
            engine=dict(values=["exec", "launch"]),
        ),
    )

    @property
    def _actual_interpreter(self):
        """Return the interpreter command."""
        if self.interpreter == "current":
            if self.interpreter_path is not None:
                raise ValueError(
                    "*interpreter=current* and *interpreter_path* attributes are incompatible"
                )
            return sys.executable
        else:
            if self.interpreter_path is None:
                return self.interpreter
            else:
                if self.system.xperm(self.interpreter_path):
                    return self.interpreter_path
                else:
                    raise AlgoComponentError(
                        "The '{:s}' interpreter is not executable".format(
                            self.interpreter_path
                        )
                    )

    def _interpreter_args_fix(self, rh, opts):
        absexec = self.absexcutable(rh.container.localpath())
        if self.interpreter == "awk":
            return ["-f", absexec]
        else:
            return [
                absexec,
            ]

    def execute_single(self, rh, opts):
        """
        Run the specified resource handler through the current interpreter,
        using the resource command_line method as args.
        """
        # Generic config
        args = [
            self._actual_interpreter,
        ]
        args.extend(self._interpreter_args_fix(rh, opts))
        args.extend(self.spawn_command_line(rh))
        logger.info("Run script %s", args)
        rh_stdin = self.spawn_stdin(rh)
        if rh_stdin is not None:
            plocale = locale.getlocale()[1] or "ascii"
            logger.info(
                "Script stdin:\n%s", rh_stdin.read().decode(plocale, "replace")
            )
            rh_stdin.seek(0)
        # Python path stuff
        newpypath = ":".join(self.extendpypath)
        if "pythonpath" in self.env:
            newpypath += ":{:s}".format(self.env.pythonpath)
        # launching the program...
        with self.env.delta_context(pythonpath=newpypath):
            self.spawn(args, opts, stdin=rh_stdin)


class ParaExpresso(TaylorRun):
    """
    Run any script in the current environment.

    This abstract class includes helpers to use the taylorism package in order
    to introduce an external parallelisation. It is designed to work well with a
    taylorism Worker class that inherits from
    :class:`vortex.tools.parallelism.VortexWorkerBlindRun`.
    """

    _abstract = True
    _footprint = dict(
        info="AlgoComponent that simply runs a script using the taylorism package.",
        attr=dict(
            interpreter=dict(
                info="The interpreter needed to run the script.",
                values=["current", "awk", "ksh", "bash", "perl", "python"],
            ),
            engine=dict(values=["exec", "launch"]),
            interpreter_path=dict(
                info="The full path to the interpreter.",
                optional=True,
            ),
            extendpypath=dict(
                info="The list of things to be prepended in the python's path.",
                type=footprints.FPList,
                default=footprints.FPList([]),
                optional=True,
            ),
        ),
    )

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        return rh is not None

    def _interpreter_args_fix(self, rh, opts):
        absexec = self.absexcutable(rh.container.localpath())
        if self.interpreter == "awk":
            return ["-f", absexec]
        else:
            return [
                absexec,
            ]

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        ddict = super()._default_common_instructions(rh, opts)
        actual_interpreter = (
            sys.executable
            if self.interpreter == "current"
            else self.interpreter
        )
        ddict["progname"] = actual_interpreter
        ddict["progargs"] = footprints.FPList(
            self._interpreter_args_fix(rh, opts) + self.spawn_command_line(rh)
        )
        ddict["progenvdelta"] = footprints.FPDict()
        # Deal with the python path
        newpypath = ":".join(self.extendpypath)
        if "pythonpath" in self.env:
            self.env.pythonpath += ":{:s}".format(newpypath)
        if newpypath:
            ddict["progenvdelta"]["pythonpath"] = newpypath
        return ddict


class BlindRun(xExecutableAlgoComponent):
    """
    Run any executable resource in the current environment. Mandatory argument is:
     * engine ( values =  blind )
    """

    _footprint = dict(
        info="AlgoComponent that simply runs a serial binary",
        attr=dict(engine=dict(values=["blind"])),
    )

    def execute_single(self, rh, opts):
        """
        Run the specified resource handler as an absolute executable,
        using the resource command_line method as args.
        """

        args = [self.absexcutable(rh.container.localpath())]
        args.extend(self.spawn_command_line(rh))
        logger.info("BlindRun executable resource %s", args)
        rh_stdin = self.spawn_stdin(rh)
        if rh_stdin is not None:
            plocale = locale.getlocale()[1] or "ascii"
            logger.info(
                "BlindRun executable stdin (fileno:%d):\n%s",
                rh_stdin.fileno(),
                rh_stdin.read().decode(plocale, "replace"),
            )
            rh_stdin.seek(0)
        self.spawn(args, opts, stdin=rh_stdin)


class ParaBlindRun(TaylorRun):
    """
    Run any executable resource (without MPI) in the current environment.

    This abstract class includes helpers to use the taylorism package in order
    to introduce an external parallelisation. It is designed to work well with a
    taylorism Worker class that inherits from
    :class:`vortex.tools.parallelism.VortexWorkerBlindRun`.
    """

    _abstract = True
    _footprint = dict(
        info="Abstract AlgoComponent that runs a serial binary using the taylorism package.",
        attr=dict(
            engine=dict(values=["blind"]),
            taskset=dict(
                info="Topology/Method to set up the CPU affinity of the child task.",
                default=None,
                optional=True,
                values=[
                    "{:s}{:s}".format(t, m)
                    for t in ("raw", "socketpacked", "numapacked")
                    for m in ("", "_taskset", "_gomp", "_omp", "_ompverbose")
                ],
            ),
            taskset_bsize=dict(
                info="The number of threads used by one task",
                type=int,
                default=1,
                optional=True,
            ),
        ),
    )

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        rc = rh is not None
        if rc:
            # Ensure that the input file is executable
            xrh = (
                rh
                if isinstance(rh, (list, tuple))
                else [
                    rh,
                ]
            )
            for arh in xrh:
                self.system.xperm(arh.container.localpath(), force=True)
        return rc

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        ddict = super()._default_common_instructions(rh, opts)
        ddict["progname"] = self.absexcutable(rh.container.localpath())
        ddict["progargs"] = footprints.FPList(self.spawn_command_line(rh))
        ddict["progtaskset"] = self.taskset
        ddict["progtaskset_bsize"] = self.taskset_bsize
        return ddict


class Parallel(xExecutableAlgoComponent):
    """
    Run a binary launched with MPI support.
    """

    _footprint = dict(
        info="AlgoComponent that simply runs an MPI binary",
        attr=dict(
            engine=dict(values=["parallel"]),
            mpitool=dict(
                info="The object used to launch the parallel program",
                optional=True,
                type=mpitools.MpiTool,
                doc_visibility=footprints.doc.visibility.GURU,
            ),
            mpiname=dict(
                info=(
                    "The mpiname of a class in the mpitool collector "
                    + "(used only if *mpitool* is not provided)"
                ),
                optional=True,
                alias=["mpi"],
                doc_visibility=footprints.doc.visibility.GURU,
            ),
            mpiverbose=dict(
                info="Boost logging verbosity in mpitools",
                optional=True,
                default=False,
                doc_visibility=footprints.doc.visibility.GURU,
            ),
            binaries=dict(
                info="List of MpiBinaryDescription objects",
                optional=True,
                type=footprints.FPList,
                doc_visibility=footprints.doc.visibility.GURU,
            ),
            binarysingle=dict(
                info="If *binaries* is missing, the default binary role for single binaries",
                optional=True,
                default="basicsingle",
                doc_visibility=footprints.doc.visibility.GURU,
            ),
            binarymulti=dict(
                info="If *binaries* is missing, the default binary role for multiple binaries",
                type=footprints.FPList,
                optional=True,
                default=footprints.FPList(
                    [
                        "basic",
                    ]
                ),
                doc_visibility=footprints.doc.visibility.GURU,
            ),
        ),
    )

    def _mpitool_attributes(self, opts):
        """Return the dictionary of attributes needed to create the mpitool object."""
        # Read the appropriate configuration in the target file
        conf_dict = config.from_config(section="mpitool")
        if self.mpiname:
            conf_dict["mpiname"] = self.mpiname
        # Make "mpirun" the default mpi command name
        if "mpiname" not in conf_dict.keys():
            conf_dict["mpiname"] = "mpirun"
        possible_attrs = functools.reduce(
            lambda s, t: s | t,
            [
                set(cls.footprint_retrieve().attr.keys())
                for cls in footprints.proxy.mpitools
            ],
        )
        nonkeys = set(conf_dict.keys()) - possible_attrs
        if nonkeys:
            msg = (
                "The following keywords are unknown configuration"
                'keys for section "mpitool":\n'
            )

            raise ValueError(msg + "\n".join(nonkeys))
        return conf_dict

    def spawn_command_line(self, rh):
        """Split the shell command line of the resource to be run."""
        return [super(Parallel, self).spawn_command_line(r) for r in rh]

    def _bootstrap_mpibins_hack(self, bins, rh, opts, use_envelope):
        return copy.deepcopy(bins)

    def _bootstrap_mpienvelope_hack(self, envelope, rh, opts, mpi):
        return copy.deepcopy(envelope)

    def _bootstrap_mpienvelope_posthack(self, envelope, rh, opts, mpi):
        return None

    def _bootstrap_mpitool(self, rh, opts):
        """Initialise the mpitool object and finds out the command line."""

        # Rh is a list binaries...
        if not isinstance(rh, collections.abc.Iterable):
            rh = [
                rh,
            ]

        # Find the MPI launcher
        mpi = self.mpitool
        if not mpi:
            mpi = footprints.proxy.mpitool(
                sysname=self.system.sysname, **self._mpitool_attributes(opts)
            )
        if not mpi:
            logger.critical(
                "Component %s could not find any mpitool",
                self.footprint_clsname(),
            )
            raise AttributeError("No valid mpitool attr could be found.")

        # Setup various useful things (env, system, ...)
        mpi.import_basics(self)

        mpi_opts = opts.get("mpiopts", dict())

        envelope = []
        use_envelope = "envelope" in mpi_opts
        if use_envelope:
            envelope = mpi_opts.pop("envelope")
            if envelope == "auto":
                blockspec = dict(
                    nn=self.env.get("VORTEX_SUBMIT_NODES", 1),
                )
                if "VORTEX_SUBMIT_TASKS" in self.env:
                    blockspec["nnp"] = self.env.get("VORTEX_SUBMIT_TASKS")
                else:
                    raise ValueError(
                        "when envelope='auto', VORTEX_SUBMIT_TASKS must be set up."
                    )
                envelope = [
                    blockspec,
                ]
            elif isinstance(envelope, dict):
                envelope = [
                    envelope,
                ]
            elif isinstance(envelope, (list, tuple)):
                pass
            else:
                raise AttributeError("Invalid envelope specification")
            if envelope:
                envelope_ntasks = sum([d["nn"] * d["nnp"] for d in envelope])
            if not envelope:
                use_envelope = False

        if not use_envelope:
            # Some MPI presets
            mpi_desc = dict()
            for mpi_k in ("tasks", "openmp"):
                mpi_kenv = "VORTEX_SUBMIT_" + mpi_k.upper()
                if mpi_kenv in self.env:
                    mpi_desc[mpi_k] = self.env.get(mpi_kenv)

        # Binaries may be grouped together on the same nodes
        bin_groups = mpi_opts.pop("groups", [])

        # Find out the command line
        bargs = self.spawn_command_line(rh)

        # Potential Source files
        sources = []

        # The usual case: no indications, 1 binary + a potential ioserver
        if len(rh) == 1 and not self.binaries:
            # In such a case, defining group does not makes sense
            self.algoassert(
                not bin_groups,
                "With only one binary, groups should not be defined",
            )

            # The main program
            allowbind = mpi_opts.pop("allowbind", True)
            distribution = mpi_opts.pop(
                "distribution",
                self.env.get("VORTEX_MPIBIN_DEF_DISTRIBUTION", None),
            )
            if use_envelope:
                master = footprints.proxy.mpibinary(
                    kind=self.binarysingle,
                    ranks=envelope_ntasks,
                    openmp=self.env.get("VORTEX_SUBMIT_OPENMP", None),
                    allowbind=allowbind,
                    distribution=distribution,
                )
            else:
                master = footprints.proxy.mpibinary(
                    kind=self.binarysingle,
                    nodes=self.env.get("VORTEX_SUBMIT_NODES", 1),
                    allowbind=allowbind,
                    distribution=distribution,
                    **mpi_desc,
                )
            master.options = mpi_opts
            master.master = self.absexcutable(rh[0].container.localpath())
            master.arguments = bargs[0]
            bins = [
                master,
            ]
            # Source files ?
            if hasattr(rh[0].resource, "guess_binary_sources"):
                sources.extend(
                    rh[0].resource.guess_binary_sources(rh[0].provider)
                )

        # Multiple binaries are to be launched: no IO server support here.
        elif len(rh) > 1 and not self.binaries:
            # Binary roles
            if len(self.binarymulti) == 1:
                bnames = self.binarymulti * len(rh)
            else:
                if len(self.binarymulti) != len(rh):
                    raise ParallelInconsistencyAlgoComponentError(
                        "self.binarymulti"
                    )
                bnames = self.binarymulti

            # Check mpiopts shape
            for k, v in mpi_opts.items():
                if not isinstance(v, collections.abc.Iterable):
                    raise ValueError(
                        "In such a case, mpiopts must be Iterable"
                    )
                if len(v) != len(rh):
                    raise ParallelInconsistencyAlgoComponentError(
                        "mpiopts[{:s}]".format(k)
                    )
            # Check bin_group shape
            if bin_groups:
                if len(bin_groups) != len(rh):
                    raise ParallelInconsistencyAlgoComponentError("bin_group")

            # Create MpiBinaryDescription objects
            bins = list()
            allowbinds = mpi_opts.pop(
                "allowbind",
                [
                    True,
                ]
                * len(rh),
            )
            distributions = mpi_opts.pop(
                "distribution",
                [
                    self.env.get("VORTEX_MPIBIN_DEF_DISTRIBUTION", None),
                ]
                * len(rh),
            )
            for i, r in enumerate(rh):
                if use_envelope:
                    bins.append(
                        footprints.proxy.mpibinary(
                            kind=bnames[i],
                            allowbind=allowbinds[i],
                            distribution=distributions[i],
                        )
                    )
                else:
                    bins.append(
                        footprints.proxy.mpibinary(
                            kind=bnames[i],
                            nodes=self.env.get("VORTEX_SUBMIT_NODES", 1),
                            allowbind=allowbinds[i],
                            distribution=distributions[i],
                            **mpi_desc,
                        )
                    )
                # Reshape mpiopts
                bins[i].options = {k: v[i] for k, v in mpi_opts.items()}
                if bin_groups:
                    bins[i].group = bin_groups[i]
                bins[i].master = self.absexcutable(r.container.localpath())
                bins[i].arguments = bargs[i]
                # Source files ?
                if hasattr(r.resource, "guess_binary_sources"):
                    sources.extend(r.resource.guess_binary_sources(r.provider))

        # Nothing to do: binary descriptions are provided by the user
        else:
            if len(self.binaries) != len(rh):
                raise ParallelInconsistencyAlgoComponentError("self.binaries")
            bins = self.binaries
            for i, r in enumerate(rh):
                bins[i].master = self.absexcutable(r.container.localpath())
                bins[i].arguments = bargs[i]

        # The global envelope
        envelope = self._bootstrap_mpienvelope_hack(envelope, rh, opts, mpi)
        if envelope:
            mpi.envelope = envelope

        # The binaries description
        mpi.binaries = self._bootstrap_mpibins_hack(
            bins, rh, opts, use_envelope
        )
        upd_envelope = self._bootstrap_mpienvelope_posthack(
            envelope, rh, opts, mpi
        )
        if upd_envelope:
            mpi.envelope = upd_envelope

        # The source files
        mpi.sources = sources

        if envelope:
            # Check the consistency between nranks and the total number of processes
            envelope_ntasks = sum([d.nprocs for d in mpi.envelope])
            mpibins_total = sum([m.nprocs for m in mpi.binaries])
            if not envelope_ntasks == mpibins_total:
                raise AlgoComponentError(
                    (
                        "The number of requested ranks ({:d}) must be equal "
                        "to the number of processes available in the envelope ({:d})"
                    ).format(mpibins_total, envelope_ntasks)
                )

        args = mpi.mkcmdline()
        for b in mpi.binaries:
            logger.info(
                "Run %s in parallel mode. Args: %s.",
                b.master,
                " ".join(b.arguments),
            )
        logger.info("Full MPI command line: %s", " ".join(args))

        # Setup various useful things (env, system, ...)
        mpi.import_basics(self)

        return mpi, args

    @contextlib.contextmanager
    def _tweak_mpitools_logging(self):
        if self.mpiverbose:
            m_loggers = dict()
            for m_logger_name in [
                l for l in loggers.lognames if "mpitools" in l
            ]:
                m_logger = loggers.getLogger(m_logger_name)
                m_loggers[m_logger] = m_logger.level
                m_logger.setLevel(logging.DEBUG)
            try:
                yield
            finally:
                for m_logger, prev_level in m_loggers.items():
                    m_logger.setLevel(prev_level)
        else:
            yield

    def execute_single(self, rh, opts):
        """Run the specified resource handler through the `mpitool` launcher

        An argument named `mpiopts` could be provided as a dictionary: it may
        contain indications on the number of nodes, tasks, ...
        """

        self.system.subtitle("{:s} : parallel engine".format(self.realkind))

        with self._tweak_mpitools_logging():
            # Return a mpitool object and the mpicommand line
            mpi, args = self._bootstrap_mpitool(rh, opts)

            # Specific parallel settings
            mpi.setup(opts)

            # This is actual running command
            self.spawn(args, opts)

            # Specific parallel cleaning
            mpi.clean(opts)


@algo_component_deco_mixin_autodoc
class ParallelIoServerMixin(AlgoComponentMpiDecoMixin):
    """Adds an IOServer capabilities (footprints attributes + MPI bianries alteration)."""

    _MIXIN_EXTRA_FOOTPRINTS = [
        footprints.Footprint(
            info="Abstract IoServer footprints' attributes.",
            attr=dict(
                ioserver=dict(
                    info="The object used to launch the IOserver part of the binary.",
                    type=mpitools.MpiBinaryIOServer,
                    optional=True,
                    default=None,
                    doc_visibility=footprints.doc.visibility.GURU,
                ),
                ioname=dict(
                    info=(
                        "The binary_kind of a class in the mpibinary collector "
                        + "(used only if *ioserver* is not provided)"
                    ),
                    optional=True,
                    default="ioserv",
                    doc_visibility=footprints.doc.visibility.GURU,
                ),
                iolocation=dict(
                    info="Location of the IO server within the binary list",
                    type=int,
                    default=-1,
                    optional=True,
                ),
            ),
        ),
    ]

    def _bootstrap_mpibins_ioserver_hack(
        self, bins, bins0, rh, opts, use_envelope
    ):
        """If requested, adds an extra binary that will act as an IOServer."""
        master = bins[-1]
        # A potential IO server
        io = self.ioserver
        if not io and int(self.env.get("VORTEX_IOSERVER_NODES", -1)) >= 0:
            io = footprints.proxy.mpibinary(
                kind=self.ioname,
                nodes=self.env.VORTEX_IOSERVER_NODES,
                tasks=(
                    self.env.VORTEX_IOSERVER_TASKS
                    or master.options.get("nnp", master.tasks)
                ),
                openmp=(
                    self.env.VORTEX_IOSERVER_OPENMP
                    or master.options.get("openmp", master.openmp)
                ),
                iolocation=self.iolocation,
            )
            io.options = {
                x[3:]: opts[x] for x in opts.keys() if x.startswith("io_")
            }
            io.master = master.master
            io.arguments = master.arguments
        if (
            not io
            and int(self.env.get("VORTEX_IOSERVER_COMPANION_TASKS", -1)) >= 0
        ):
            io = footprints.proxy.mpibinary(
                kind=self.ioname,
                nodes=master.options.get("nn", master.nodes),
                tasks=self.env.VORTEX_IOSERVER_COMPANION_TASKS,
                openmp=(
                    self.env.VORTEX_IOSERVER_OPENMP
                    or master.options.get("openmp", master.openmp)
                ),
            )
            io.options = {
                x[3:]: opts[x] for x in opts.keys() if x.startswith("io_")
            }
            io.master = master.master
            io.arguments = master.arguments
            if master.group is not None:
                # The master binary is already in a group ! Use it.
                io.group = master.group
            else:
                io.group = "auto_masterwithio"
                master.group = "auto_masterwithio"
        if (
            not io
            and self.env.get("VORTEX_IOSERVER_INCORE_TASKS", None) is not None
        ):
            if hasattr(master, "incore_iotasks"):
                master.incore_iotasks = self.env.VORTEX_IOSERVER_INCORE_TASKS
        if (
            not io
            and self.env.get("VORTEX_IOSERVER_INCORE_FIXER", None) is not None
        ):
            if hasattr(master, "incore_iotasks_fixer"):
                master.incore_iotasks_fixer = (
                    self.env.VORTEX_IOSERVER_INCORE_FIXER
                )
        if (
            not io
            and self.env.get("VORTEX_IOSERVER_INCORE_DIST", None) is not None
        ):
            if hasattr(master, "incore_iodist"):
                master.incore_iodist = self.env.VORTEX_IOSERVER_INCORE_DIST
        if io:
            rh.append(rh[0])
            if master.group is None:
                if "nn" in master.options:
                    master.options["nn"] = (
                        master.options["nn"] - io.options["nn"]
                    )
                else:
                    logger.warning(
                        'The "nn" option is not available in the master binary '
                        + "mpi options. Consequently it can be fixed..."
                    )
            if self.iolocation >= 0:
                bins.insert(self.iolocation, io)
            else:
                bins.append(io)
        return bins

    _MIXIN_MPIBINS_HOOKS = (_bootstrap_mpibins_ioserver_hack,)


@algo_component_deco_mixin_autodoc
class ParallelOpenPalmMixin(AlgoComponentMpiDecoMixin):
    """Class mixin to be used with OpenPALM programs.

    It will automatically add the OpenPALM driver binary to the list of
    binaries. The location of the OpenPALM driver should be automatically
    detected provided that a section with ``role=OpenPALM Driver`` lies in the
    input's sequence. Alternatively, the path to the OpenPALM driver can be
    provided using the **openpalm_driver** footprint's argument.
    """

    _MIXIN_EXTRA_FOOTPRINTS = [
        footprints.Footprint(
            info="Abstract OpenPALM footprints' attributes.",
            attr=dict(
                openpalm_driver=dict(
                    info=(
                        "The path to the OpenPALM driver binary. "
                        + "When omitted, the input sequence is looked up "
                        + "for section with ``role=OpenPALM Driver``."
                    ),
                    optional=True,
                    doc_visibility=footprints.doc.visibility.ADVANCED,
                ),
                openpalm_overcommit=dict(
                    info=(
                        "Run the OpenPALM driver on the first node in addition "
                        + "to existing tasks. Otherwise dedicated tasks are used."
                    ),
                    type=bool,
                    default=True,
                    optional=True,
                    doc_visibility=footprints.doc.visibility.ADVANCED,
                ),
                openpalm_binddriver=dict(
                    info="Try to bind the OpenPALM driver binary.",
                    type=bool,
                    optional=True,
                    default=False,
                    doc_visibility=footprints.doc.visibility.ADVANCED,
                ),
                openpalm_binkind=dict(
                    info="The binary kind for the OpenPALM driver.",
                    optional=True,
                    default="basic",
                    doc_visibility=footprints.doc.visibility.GURU,
                ),
            ),
        ),
    ]

    @property
    def _actual_openpalm_driver(self):
        """Returns the OpenPALM's driver location."""
        path = self.openpalm_driver
        if path is None:
            drivers = self.context.sequence.effective_inputs(
                role="OpenPALMDriver"
            )
            if not drivers:
                raise AlgoComponentError("No OpenPALM driver was provided.")
            elif len(drivers) > 1:
                raise AlgoComponentError(
                    "Several OpenPALM driver were provided."
                )
            path = drivers[0].rh.container.localpath()
        else:
            if not self.system.path.exists(path):
                raise AlgoComponentError(
                    "No OpenPALM driver was provider ({:s} does not exists).".format(
                        path
                    )
                )
        return path

    def _bootstrap_mpibins_openpalm_hack(
        self, bins, bins0, rh, opts, use_envelope
    ):
        """Adds the OpenPALM driver to the binary list."""
        single_bin = len(bins) == 1
        master = bins[0]
        driver = footprints.proxy.mpibinary(
            kind=self.openpalm_binkind,
            nodes=1,
            tasks=self.env.VORTEX_OPENPALM_DRV_TASKS or 1,
            openmp=self.env.VORTEX_OPENPALM_DRV_OPENMP or 1,
            allowbind=opts.pop(
                "palmdrv_bind",
                self.env.get(
                    "VORTEX_OPENPALM_DRV_BIND", self.openpalm_binddriver
                ),
            ),
        )
        driver.options = {
            x[8:]: opts[x] for x in opts.keys() if x.startswith("palmdrv_")
        }
        driver.master = self._actual_openpalm_driver
        self.system.xperm(driver.master, force=True)
        bins.insert(0, driver)
        if not self.openpalm_overcommit and single_bin:
            # Tweak the number of tasks of the master program in order to accommodate
            # the driver
            # NB: If multiple binaries are provided, the user must do this by
            # himself (i.e. leave enough room for the driver's task).
            if "nn" in master.options:
                master.options["nn"] = master.options["nn"] - 1
            else:
                # Ok, tweak nprocs instead (an envelope might be defined)
                try:
                    nprocs = master.nprocs
                except mpitools.MpiException:
                    logger.error(
                        'Neither the "nn" option nor the nprocs is '
                        + "available for the master binary. Consequently "
                        + "it can be fixed..."
                    )
                else:
                    master.options["np"] = nprocs - driver.nprocs
        return bins

    _MIXIN_MPIBINS_HOOKS = (_bootstrap_mpibins_openpalm_hack,)

    def _bootstrap_mpienvelope_openpalm_posthack(
        self, env, env0, rh, opts, mpi
    ):
        """
        Tweak the MPI envelope in order to execute the OpenPALM driver on the
        appropriate node.
        """
        master = mpi.binaries[
            1
        ]  # The first "real" program that will be launched
        driver = mpi.binaries[0]  # The OpenPALM driver
        if self.openpalm_overcommit:
            # Execute the driver on the first compute node
            if env or env0:
                env = env or copy.deepcopy(env0)
                # An envelope is already defined... update it
                if not ("nn" in env[0] and "nnp" in env[0]):
                    raise AlgoComponentError(
                        "'nn' and 'nnp' must be defined in the envelope"
                    )
                if env[0]["nn"] > 1:
                    env[0]["nn"] -= 1
                    newenv = copy.copy(env[0])
                    newenv["nn"] = 1
                    newenv["nnp"] += driver.nprocs
                    env.insert(0, newenv)
                else:
                    env[0]["nnp"] += driver.nprocs
            else:
                # Setup a new envelope
                if not ("nn" in master.options and "nnp" in master.options):
                    raise AlgoComponentError(
                        "'nn' and 'nnp' must be defined for the master executable"
                    )
                env = [
                    dict(
                        nn=1,
                        nnp=master.options["nnp"] + driver.nprocs,
                        openmp=master.options.get("openmp", 1),
                    )
                ]
                if master.options["nn"] > 1:
                    env.append(
                        dict(
                            nn=master.options["nn"] - 1,
                            nnp=master.options["nnp"],
                            openmp=master.options.get("openmp", 1),
                        )
                    )
                if len(mpi.binaries) > 2:
                    env.extend([b.options for b in mpi.binaries[2:]])
        return env

    _MIXIN_MPIENVELOPE_POSTHOOKS = (_bootstrap_mpienvelope_openpalm_posthack,)
