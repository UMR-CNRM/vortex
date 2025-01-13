"""
This package defines a class for default contexts used
by a PoolWorker process of the Jeeves daemon.
"""

import logging

from bronx.fancies import loggers

logger = loggers.getLogger(__name__)


class AttrDict(dict):
    """Dict object that can be accessed by attributes.

    >>> obj = AttrDict()
    >>> obj.test = 'hi'
    >>> print(obj['test'])
    hi

    >>> obj['test'] = "bye"
    >>> print(obj.test)
    bye

    >>> print(len(obj))
    1

    >>> obj.clear()
    >>> print(len(obj))
    0

    >>> obj.a
    Traceback (most recent call last):
        ...
    AttributeError: 'AttrDict' object has no attribute 'a'
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self


class VortexWorker:
    """Context for a vortex session handled by an asynchronous process such as Jeeves.

    An _oper_ profile should be used from Jeeves: the default is to use a _research_ profile.
    See :mod:`vortex.gloves`.
    """

    _PRIVATESESSION_TAG = "asyncworker_view"
    _PRIVATEGLOVE_TAG = "asyncworker_id"
    _PRIVATESESSION = None
    _PRIVATEMODULES = set()

    def __init__(
        self, modules=tuple(), verbose=False, logger=None, profile=None
    ):
        self._logger = logger
        self._modules = modules
        self._context_lock = False
        self._context_prev_ticket = None
        self.verbose = verbose
        self.profile = profile
        self.rc = True

    @property
    def logger(self):
        return self._logger

    @property
    def modules(self):
        return self._modules

    @property
    def session(self):
        """The session associated with Async Worker."""
        if self._PRIVATESESSION is None:
            import vortex

            t = vortex.sessions.get(
                tag=self._PRIVATESESSION_TAG,
                glove=vortex.sessions.getglove(
                    tag=self._PRIVATEGLOVE_TAG, profile=self.profile
                ),
            )
            sh = t.system()
            import vortex.tools.lfi  # @UnusedImport
            import vortex.tools.grib  # @UnusedImport
            import vortex.tools.folder  # @UnusedImport
            import footprints as fp

            fp.proxy.addon(kind="lfi", shell=sh)
            fp.proxy.addon(kind="grib", shell=sh)
            fp.proxy.addon(kind="allfolders", shell=sh, verboseload=False)
            self._PRIVATESESSION = t
        return self._PRIVATESESSION

    def get_dataset(self, ask):
        """Struct friendly access to data request."""
        return AttrDict(ask.data)

    def reset_loggers(self, logger):
        if not self.verbose:
            # footprints & bronx can be very talkative... we try to limit that !
            global_level = logger.getEffectiveLevel()
            f_logger = loggers.getLogger("footprints")
            b_logger = loggers.getLogger("bronx")
            if global_level <= logging.INFO and not self.verbose:
                f_logger.setLevel(logging.INFO)
                b_logger.setLevel(logging.INFO)
            else:
                f_logger.setLevel(logging.NOTSET)
                b_logger.setLevel(logging.NOTSET)

    def __enter__(self, *args):
        if self._context_lock:
            raise RuntimeError(
                "Imbricated context manager calls are forbidden."
            )
        self._context_lock = True
        if self.logger is None:
            self._logger = logger
        else:
            self.reset_loggers(self.logger)
        # Activate our own session
        import vortex

        self._context_prev_ticket = vortex.sessions.current()
        if not self.session.active:
            self.session.activate()
        # Import extra modules
        for modname in self.modules:
            if modname not in self._PRIVATEMODULES:
                self.session.sh.import_module(modname)
                self._PRIVATEMODULES.add(modname)
        # Ok, let's talk...
        self.logger.info(
            "VORTEX enter glove_profile=%s ", self.session.glove.profile
        )
        self.logger.debug(
            "       modules=%s addons=%s",
            self.modules,
            self.session.sh.loaded_addons(),
        )
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Well... nothing much to do..."""
        if exc_value is not None:
            self.logger.critical("VORTEX exits on error", exc_info=exc_value)
            self.rc = False
        else:
            self.logger.debug("VORTEX exits nicely.")
        self._context_prev_ticket.activate()
        self._context_lock = False
        return True


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=False)
