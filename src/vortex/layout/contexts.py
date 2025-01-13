"""
This modules defines the physical layout.
"""

import footprints
from bronx.fancies import loggers
from bronx.stdtypes.history import PrivateHistory
from bronx.patterns import getbytag, observer
from bronx.stdtypes.tracking import Tracker

from vortex.tools.env import Environment
import vortex.tools.prestaging
from vortex.tools.delayedactions import PrivateDelayedActionsHub
from . import dataflow

#: No automatic export.
__all__ = []

logger = loggers.getLogger(__name__)

_RHANDLERS_OBSBOARD = "Resources-Handlers"
_STORES_OBSBOARD = "Stores-Activity"

_PRESTAGE_REQ_ACTION = "prestage_req"


# Module Interface
def get(**kw):
    """Return actual context object matching description."""
    return Context(**kw)


def keys():
    """Return the list of current context tags."""
    return Context.tag_keys()


def values():
    """Return the list of current context values."""
    return Context.tag_values()


def items():
    """Return the items of the contexts table."""
    return Context.tag_items()


def current():
    """Return the context with the focus on, if any."""
    tf = Context.tag_focus()
    if tf is not None:
        tf = Context(tag=tf)
    return tf


def switch(tag=None):
    """Set the session associated to the actual ``tag`` as active."""
    return current().switch(tag=tag)


class ContextObserverRecorder(observer.Observer):
    """Record events related to a given Context.

    In order to start recording, this object should be associated with a
    :obj:`Context` object using the :meth:`register` method. The recording will
    be stopped when the :meth:`unregister` method is called. The recording is
    automatically stopped whenever the object is pickled.

    At any time, the `record` can be replayed in a given Context using the
    :meth:`replay_in` method.
    """

    def __init__(self):
        self._binded_context = None
        self._tracker_recorder = None
        self._stages_recorder = None
        self._prestaging_recorder = None

    def __del__(self):
        self.unregister()

    def __getstate__(self):
        # Objects have to be unregistered before being pickled
        self.unregister()
        return self.__dict__

    def register(self, context):
        """Associate a particular :obj:`Context` object and start recording.

        :param context: The :obj:`Context` object that will be recorded.
        """
        self._binded_context = context
        self._tracker_recorder = dataflow.LocalTracker()
        self._stages_recorder = list()
        self._prestaging_recorder = list()
        observer.get(tag=_RHANDLERS_OBSBOARD).register(self)
        observer.get(tag=_STORES_OBSBOARD).register(self)

    def unregister(self):
        """Stop recording."""
        if self._binded_context is not None:
            self._binded_context = None
            observer.get(tag=_RHANDLERS_OBSBOARD).unregister(self)
            observer.get(tag=_STORES_OBSBOARD).unregister(self)

    def updobsitem(self, item, info):
        if (self._binded_context is not None) and self._binded_context.active:
            logger.debug("Recording upd item %s", item)
            if info["observerboard"] == _RHANDLERS_OBSBOARD:
                processed_item = item.as_dict()
                self._stages_recorder.append((processed_item, info))
                self._tracker_recorder.update_rh(item, info)
            elif info["observerboard"] == _STORES_OBSBOARD:
                self._tracker_recorder.update_store(item, info)
                if info["action"] == _PRESTAGE_REQ_ACTION:
                    self._prestaging_recorder.append(info)

    def replay_in(self, context):
        """Replays the observer's record in a given context.

        :param context: The :obj:`Context` object where the record will be replayed.
        """
        # First the stages of the sequence
        if self._stages_recorder:
            logger.info(
                "The recorder is replaying stages for context <%s>",
                context.tag,
            )
            for pr_item, info in self._stages_recorder:
                rh_stack = set()
                for section in context.sequence.fastsearch(pr_item):
                    if section.rh.as_dict() == pr_item:
                        context.sequence.section_updstage(section, info)
                        rh_stack.add(section.rh)
                for rh in rh_stack:
                    rh.external_stage_update(info.get("stage"))
        # Then the localtracker
        if self._tracker_recorder is not None:
            logger.info(
                "The recorder is updating the LocalTracker for context <%s>",
                context.tag,
            )
            context.localtracker.append(self._tracker_recorder)
        # Finally the prestaging requests
        if self._prestaging_recorder:
            logger.info(
                "The recorder is replaying prestaging requests for context <%s>",
                context.tag,
            )
            for info in self._prestaging_recorder:
                context.prestaging_hub(**info)


class DiffHistory(PrivateHistory):
    """Keep track of all the toolbox.diff made in this Context."""

    def append_record(self, rc, localcontainer, remotehandler):
        """Adds a new diff record in the current DiffHistory."""
        rcmap = {True: "PASS", False: "FAIL"}
        containerstr = (
            str(localcontainer)
            if localcontainer.is_virtual()
            else localcontainer.localpath()
        )
        self.append(
            "{:s}: {:s} (Ref: {!s})".format(
                rcmap[bool(rc)], containerstr, remotehandler.provider
            )
        )

    def datastore_inplace_overwrite(self, other):
        """Used by a DataStore object to refill a DiffHistory."""
        self.reset()
        self._history.extend(other.get())
        self._count = other.count


class Context(getbytag.GetByTag, observer.Observer):
    """Physical layout of a session or task, etc."""

    _tag_default = "ctx"

    def __init__(
        self, path=None, topenv=None, sequence=None, localtracker=None
    ):
        """Initiate a new execution context."""
        logger.debug("Context initialisation %s", self)
        if path is None:
            logger.critical("Try to define a new context without virtual path")
            raise ValueError("No virtual path given to new context.")
        if topenv is None:
            logger.critical("Try to define a new context without a topenv.")
            raise ValueError("No top environment given to new context.")
        self._env = Environment(
            env=topenv, verbose=topenv.verbose(), contextlock=self
        )
        self._path = path + "/" + self.tag
        self._session = None
        self._rundir = None
        self._stamp = "-".join(("vortex", "stamp", self.tag, str(id(self))))
        self._fstore = dict()
        self._fstamps = set()
        self._wkdir = None
        self._record = False
        self._prestaging_hub = None  # Will be initialised on demand
        self._delayedactions_hub = None  # Will be initialised on demand

        if sequence:
            self._sequence = sequence
        else:
            self._sequence = dataflow.Sequence()

        if localtracker:
            self._localtracker = localtracker
        else:
            # Create the localtracker within the Session's datastore
            if self.session.datastore.check(
                "context_localtracker", dict(path=self.path)
            ):
                self._localtracker = self.session.datastore.get(
                    "context_localtracker", dict(path=self.path)
                )
            else:
                self._localtracker = self.session.datastore.insert(
                    "context_localtracker",
                    dict(path=self.path),
                    dataflow.LocalTracker(),
                )

        # Create the localtracker within the Session's datastore
        if self.session.datastore.check(
            "context_diffhistory", dict(path=self.path)
        ):
            self._dhistory = self.session.datastore.get(
                "context_diffhistory", dict(path=self.path)
            )
        else:
            self._dhistory = self.session.datastore.insert(
                "context_diffhistory", dict(path=self.path), DiffHistory()
            )

        observer.get(tag=_RHANDLERS_OBSBOARD).register(self)
        observer.get(tag=_STORES_OBSBOARD).register(self)

    @property
    def active(self):
        """Returns wether this Context is currently active or not."""
        return self.has_focus()

    def _enforce_active(self):
        if not self.active:
            raise RuntimeError(
                "It's not allowed to call this method on an inactive Context."
            )

    def newobsitem(self, item, info):
        """
        Resources-Handlers / Store-Activity observing facility.
        Register a new section in void active context with the resource handler ``item``.
        """
        if self.active:
            logger.debug(
                "Notified %s new item of class %s and id %s",
                self,
                item.__class__,
                id(item),
            )
            if self._record and info["observerboard"] == _RHANDLERS_OBSBOARD:
                self._sequence.section(rh=item, stage="load")

    def updobsitem(self, item, info):
        """
        Resources-Handlers / Store-Activity observing facility.
        Track the new stage of the section containing the resource handler ``item``.
        """
        if self.active:
            logger.debug("Notified %s upd item %s", self, item)
            if info["observerboard"] == _RHANDLERS_OBSBOARD:
                if "stage" in info:
                    # Update the sequence
                    for section in self._sequence.fastsearch(item):
                        if section.rh is item:
                            self._sequence.section_updstage(section, info)
                if ("stage" in info) or ("clear" in info):
                    # Update the local tracker
                    self._localtracker.update_rh(item, info)
            elif info["observerboard"] == _STORES_OBSBOARD:
                # Update the local tracker
                self._localtracker.update_store(item, info)
                if info["action"] == _PRESTAGE_REQ_ACTION:
                    self.prestaging_hub.record(**info)

    def get_recorder(self):
        """Return a :obj:`ContextObserverRecorder` object recording the changes in this Context."""
        rec = ContextObserverRecorder()
        rec.register(self)
        return rec

    def focus_loose_hook(self):
        """Save the current Environment and working directory."""
        super().focus_loose_hook()
        self._env = self.env
        if self._wkdir is not None:
            self._wkdir = self.system.getcwd()

    def focus_gain_allow(self):
        super().focus_gain_allow()
        # It's not possible to activate a Context that lies outside the current
        # session
        if not self.session.active:
            raise RuntimeError(
                "It's not allowed to switch to a Context that belongs to an inactive session"
            )

    def focus_gain_hook(self):
        super().focus_gain_hook()
        # Activate the environment (if necessary)
        if not self._env.active():
            self._env.active(True)
        # Jump to the latest working directory
        if self._wkdir is not None:
            self.system.cd(self._wkdir)

    @classmethod
    def switch(cls, tag=None):
        """
        Allows the user to switch to another context,
        assuming that the provided tag is already known.
        """
        if tag in cls.tag_keys():
            obj = Context(tag=tag)
            obj.catch_focus()
            return obj
        else:
            logger.error("Try to switch to an undefined context: %s", tag)
            return None

    def activate(self):
        """Force the current context as active."""
        return self.catch_focus()

    @property
    def path(self):
        """Return the virtual path of the current context."""
        return self._path

    @property
    def session(self):
        """Return the session bound to the current virtual context path."""
        if self._session is None:
            from vortex import sessions

            self._session = sessions.get(
                tag=[x for x in self.path.split("/") if x][0]
            )
        return self._session

    def _get_rundir(self):
        """Return the path of the directory associated to that context."""
        return self._rundir

    def _set_rundir(self, path):
        """Set a new rundir."""
        if self._rundir:
            logger.warning(
                "Context <%s> is changing its working directory <%s>",
                self.tag,
                self._rundir,
            )
        if self.system.path.isdir(path):
            self._rundir = path
            logger.info("Context <%s> set rundir <%s>", self.tag, self._rundir)
        else:
            logger.error(
                "Try to change context <%s> to invalid path <%s>",
                self.tag,
                path,
            )

    rundir = property(_get_rundir, _set_rundir)

    def cocoon(self):
        """Change directory to the one associated to that context."""
        self._enforce_active()
        if self.rundir is None:
            subpath = self.path.replace(self.session.path, "", 1)
            self._rundir = self.session.rundir + subpath
        self.system.cd(self.rundir, create=True)
        self._wkdir = self.rundir

    @property
    def env(self):
        """Return the :class:`~vortex.tools.env.Environment` object associated to that context."""
        if self.active:
            return Environment.current()
        else:
            return self._env

    @property
    def prestaging_hub(self):
        """Return the prestaging hub associated with this context.

        see :class:`vortex.tools.prestaging` for more details.
        """
        if self._prestaging_hub is None:
            self._prestaging_hub = vortex.tools.prestaging.get_hub(
                tag="contextbound_{:s}".format(self.tag),
                sh=self.system,
                email=self.session.glove.email,
            )
        return self._prestaging_hub

    @property
    def delayedactions_hub(self):
        """Return the delayed actions hub associated with this context.

        see :class:`vortex.tools.delayedactions` for more details.
        """
        if self._delayedactions_hub is None:
            self._delayedactions_hub = PrivateDelayedActionsHub(
                sh=self.system, contextrundir=self.rundir
            )
        return self._delayedactions_hub

    @property
    def system(self):
        """Return the :class:`~vortex.tools.env.System` object associated to the root session."""
        return self.session.system()

    @property
    def sequence(self):
        """Return the :class:`~vortex.layout.dataflow.Sequence` object associated to that context."""
        return self._sequence

    @property
    def localtracker(self):
        """Return the :class:`~vortex.layout.dataflow.LocalTracker` object associated to that context."""
        return self._localtracker

    @property
    def diff_history(self):
        return self._dhistory

    @property
    def subcontexts(self):
        """The current contexts virtually included in the current one."""
        rootpath = self.path + "/"
        return [
            x
            for x in self.__class__.tag_values()
            if x.path.startswith(rootpath)
        ]

    def newcontext(self, name, focus=False):
        """
        Create a new child context, attached to the current one.
        The tagname of the new kid is given through the mandatory ``name`` argument,
        as well as the default ``focus``.
        """
        if name in self.__class__.tag_keys():
            raise RuntimeError(
                "A context with tag={!s} already exists.".format(name)
            )
        newctx = self.__class__(tag=name, topenv=self.env, path=self.path)
        if focus:
            self.__class__.set_focus(newctx)
        return newctx

    def stamp(self, tag="default"):
        """Return a stamp name that could be used for any generic purpose."""
        return self._stamp + "." + str(tag)

    def fstrack_stamp(self, tag="default"):
        """Set a stamp to track changes on the filesystem."""
        self._enforce_active()
        stamp = self.stamp(tag)
        self._fstamps.add(self.system.path.abspath(stamp))
        self.system.touch(stamp)
        self._fstore[stamp] = set(self.system.ffind())

    def fstrack_check(self, tag="default"):
        """
        Return a anonymous dictionary with for the each key, the list of entries
        in the file system that are concerned since the last associated ``tag`` stamp.
        Keys are: ``deleted``, ``created``, ``updated``.
        """
        self._enforce_active()
        stamp = self.stamp(tag)
        if not self.system.path.exists(stamp):
            logger.warning("Missing stamp %s", stamp)
            return None
        ffinded = set(self.system.ffind())
        bkuptrace = self.system.trace
        self.system.trace = False
        fscheck = Tracker(self._fstore[stamp], ffinded)
        stroot = self.system.stat(stamp)
        fscheck.updated = [
            f
            for f in fscheck.unchanged
            if self.system.stat(f).st_mtime > stroot.st_mtime
        ]
        self.system.trace = bkuptrace
        return fscheck

    @property
    def record(self):
        """Automatic recording of section while loading resource handlers."""
        return self._record

    def record_off(self):
        """Avoid automatic recording of section while loading resource handlers."""
        self._record = False

    def record_on(self):
        """Activate automatic recording of section while loading resource handlers."""
        self._record = True

    def clear_promises(
        self, netloc="promise.cache.fr", scheme="vortex", storeoptions=None
    ):
        """Remove all promises that have been made in this context.

        :param netloc: Netloc of the promise's cache store to clean up
        :param scheme: Scheme of the promise's cache store to clean up
        :param storeoptions: Option dictionary passed to the store (may be None)
        """
        self.system.header(
            "Clear promises for {}://{} in context {}".format(
                scheme, netloc, self.path
            )
        )
        skeleton = dict(scheme=scheme, netloc=netloc)
        promises = self.localtracker.grep_uri("put", skeleton)
        if promises:
            logger.info("Some promises are left pending...")
            if storeoptions is None:
                storeoptions = dict()
            store = footprints.proxy.store(
                scheme=scheme, netloc=netloc, **storeoptions
            )
            for promise in [pr.copy() for pr in promises]:
                del promise["scheme"]
                del promise["netloc"]
                store.delete(promise)
        else:
            logger.info("No promises were left pending.")

    def clear_stamps(self):
        """Remove local context stamps."""
        if self._fstore:
            fstamps = list(self._fstamps)
            self.system.rmall(*fstamps)
            logger.info("Removing context stamps %s", fstamps)
            self._fstore = dict()
            self._fstamps = set()

    def free_resources(self):
        """Try to free up memory (removing temporary stuff, caches, ...)."""
        self.sequence.free_resources()
        self.clear_stamps()

    def clear(self):
        """Make a clear place of local cocoon directory."""
        self.sequence.clear()
        self.clear_stamps()

    def exit(self):
        """Clean exit from the current context."""
        try:
            self.clear()
        except TypeError:
            logger.error("Could not clear local context <%s>", self.tag)
        # Nullify some variable to help during garbage collection
        self._prestaging_hub = None
        if self._delayedactions_hub:
            self._delayedactions_hub.clear()
            self._delayedactions_hub = None
