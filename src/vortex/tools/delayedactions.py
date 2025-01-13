"""
Advanced tools that deals with delayed actions.

The entry point to the delayed action mechanism is the :class:`PrivateDelayedActionsHub`
class. One :class:`PrivateDelayedActionsHub` object is created in each
:class:`~vortex.dataflow.contexts.Context`
(see :meth:`vortex.dataflow.contexts.Context.delayedactions_hub`). When working
with delayed actions, you must always use the :class:`PrivateDelayedActionsHub`
object associated with the current active :class:`~vortex.dataflow.contexts.Context`.

Example::

    # Get the DelayedActionsHub object from the current context

    >>> from vortex import sessions

    >>> cur_da_hub = sessions.current().context.delayedactions_hub

    # Instruct Vortex to sleep (in parallel !)

    >>> dactions = [cur_da_hub.register(n, kind='sleep') for n in (1, 3, 2)]

    # How does it look like in the logs for the first action ?

    >>> cur_da_hub.actionhistory(dactions[0])  # doctest:+ELLIPSIS
    <....DemoSleepDelayedActionHandler object at 0x...> says:
    [...][...] : NEW  id=sleeper_action_...: request=1
    [...][...] : UPD  id=sleeper_action_...: result=<multiprocessing.pool.ApplyResult object at 0x...> ...

    # Wait for all the sleepers to wake up... It would be possible to do that
    # explicitly by calling the ``finalise`` method, but ``retrieve`` implicitly
    # calls ``finalise`` so we don't bother !

    >>> for daction in dactions:
    ...     action = cur_da_hub.retrieve(daction, bareobject=True)
    ...     if action.status == d_action_status.done:
    ...         print('I slept for {0.request:d} seconds and It was good :-)'.format(action))
    ...     else:
    ...         print('I failed to get asleep for {0.request:d} seconds :-('.format(action))
    I slept for 1 seconds and It was good :-)
    I slept for 3 seconds and It was good :-)
    I slept for 2 seconds and It was good :-)

    # And now, what are the log saying ?

    >>> cur_da_hub.actionhistory(dactions[0])  # doctest:+ELLIPSIS
    <....DemoSleepDelayedActionHandler object at 0x...> says:
    [...][...] : NEW  id=sleeper_action_0000000000000001: request=1
    [...][...] : UPD  id=sleeper_action_0000000000000001: result=<multiprocessing.pool.ApplyResult object at 0x...> ...
    [...][...] : UPD  id=sleeper_action_0000000000000001: status=done (instead of: void)
    [...][...] : USED id=sleeper_action_0000000000000001

"""

from collections import namedtuple, defaultdict
import multiprocessing
import os
import tempfile
import time

from bronx.fancies import loggers
from bronx.fancies.dump import lightdump
from bronx.stdtypes.history import PrivateHistory
from bronx.patterns import getbytag, observer

import footprints
from footprints import proxy as fpx

from vortex.tools.systems import OSExtended

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

#: Definition of a named tuple DelayedActionStatusTuple
DelayedActionStatusTuple = namedtuple(
    "DelayedActionStatusTuple", ["void", "failed", "done", "unclear"]
)

#: Predefined DelayedActionStatus values (void=Not ready yet,
#                                         failed=processed but KO,
#                                         done=processed and OK,
#                                         unclear=processed but cannot tell whether it is KO or OK)
d_action_status = DelayedActionStatusTuple(
    void=0, failed=-1, done=1, unclear=-2
)


# Module Interface
def get_hub(**kw):
    """Return the actual :class:`DelayedActionsHub` object matching the *tag* (or create one)."""
    return DelayedActionsHub(**kw)


class DelayedAction:
    """Simple object describing one action to be performed."""

    def __init__(self, obsboard, r_id, request):
        """
        :param SecludedObserverBoard obsboard: The Observer board that will be used
                                               to publish the results.
        :param r_id: Any kind of ID that uniquely identifies the delayed action
        :param request: Any kind of data that describes the action to be performed
        """
        self._obsboard = obsboard
        self._id = r_id
        self._request = request
        self._status = d_action_status.void
        self._result = None
        self._obsboard.notify_new(self, dict())

    @property
    def id(self):
        """The delayed action ID."""
        return self._id

    @property
    def request(self):
        """The data describing the action."""
        return self._request

    def _set_status(self, value):
        oldres = self.statustext
        self._status = value
        self._obsboard.notify_upd(
            self,
            info=dict(changed="status", queryproxy="statustext", prev=oldres),
        )

    @property
    def status(self):
        """The delayed action status (see :data:`d_action_status` for possible values)."""
        return self._status

    def _get_result(self):
        return self._result

    def _set_result(self, result):
        oldres = self._result
        self._result = result
        self._obsboard.notify_upd(
            self, info=dict(changed="result", prev=oldres)
        )

    result = property(
        _get_result,
        _set_result,
        doc="Where to find the delayed action result.",
    )

    @property
    def statustext(self):
        """A string that descibres the delayed action status."""
        for k, v in d_action_status._asdict().items():
            if self._status == v:
                return k
        logger.warning("What is this idiotic status (%s) ???", self.status)
        return str(self.status)

    def mark_as_failed(self):
        """Change the status to ``failed``."""
        logger.info(
            "Marking early-get %s as failed (request=%s)",
            self.id,
            self.request,
        )
        self._set_status(d_action_status.failed)

    def mark_as_done(self):
        """Change the status to ``done``."""
        logger.debug(
            "Marking early-get %s as done (request=%s)", self.id, self.request
        )
        self._set_status(d_action_status.done)

    def mark_as_unclear(self):
        """Change the status to ``unclear``."""
        logger.info(
            "Marking early-get %s as unclear/unconclusive (request=%s)",
            self.id,
            self.request,
        )
        self._set_status(d_action_status.unclear)

    def __str__(self):
        return "id={0._id}: {0.statustext:6s} result={0.result!s}".format(self)


class AbstractDelayedActionsHandler(
    footprints.FootprintBase, observer.Observer
):
    """Abstract class that handles a bunch of similar delayed actions."""

    _abstract = True
    _collector = ("delayedactionshandler",)
    _footprint = dict(
        info="Abstract class that deal with delayed actions.",
        attr=dict(
            system=dict(info="The current system object", type=OSExtended),
            observerboard=dict(
                info="The observer board where delayed actions updates are published.",
                type=observer.SecludedObserverBoard,
            ),
            stagedir=dict(info="The temporary directory (if need be)"),
        ),
    )

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._resultsmap = dict()
        self._history = PrivateHistory(timer=True)
        self.observerboard.register(self)
        self._custom_init()

    def destroy(self):
        """Cleanup everything... (useful when multiprocessing is used)"""
        self._resultsmap = None
        self._history = None

    def _custom_init(self):
        """This method may be specialised in actual DelayedActionsHandler classes."""
        pass

    def newobsitem(self, item, info):  # @UnusedVariable
        """To get informed when a new :class:`DelayedAction` object is created."""
        if item.id in self._resultsmap:
            self._history.append(
                "NEW ", "id={0.id!s}: request={0.request!s}".format(item)
            )

    def updobsitem(self, item, info):
        """To get informed when a new :class:`DelayedAction` object is updates."""
        if item.id in self._resultsmap:
            what = info["changed"]
            newval = getattr(item, info.get("queryproxy", what))
            oldval = info["prev"]
            self._history.append(
                "UPD ",
                "id={0.id!s}: {1:s}={2!s} (instead of: {3!s})".format(
                    item, what, newval, oldval
                ),
            )

    @property
    def history(self):
        """The :class:`PrivateHistory` object where all of this object's activity is logged."""
        return self._history

    def grephistory(self, r_id):
        """Return the log lines matching the **r_id** delayed action ID."""
        return self.history.grep("id={!s}".format(r_id))

    def showhistory(self, r_id):
        """Print the log lines matching the **r_id** delayed action ID."""
        return self.history.showgrep("id={!s}".format(r_id))

    def __contains__(self, r_id):
        return r_id in self._resultsmap

    def dispence_resultid(self):
        """Return a unique ID that will identify a new :class:`DelayedAction` object."""
        raise NotImplementedError()

    def _create_delayed_action(self, r_id, request):
        """Create a :class:`DelayedAction` object given **r_id** and **request**."""
        return DelayedAction(self.observerboard, r_id, request)

    def register(self, request):
        """Create a new :class:`DelayedAction` object from a user's **request**."""
        r_id = self.dispence_resultid()
        self._resultsmap[r_id] = None  # For newobitem to work...
        d_action = self._create_delayed_action(r_id, request)
        self._resultsmap[r_id] = d_action
        self._custom_register(d_action)
        return r_id

    def _custom_register(self, action):
        """Any action to be performed each time a new delayed action is registered."""
        pass

    @property
    def dirty(self):
        """Is there any of the object's delayed actions that needs finalising ?"""
        return any(
            [
                a.status == d_action_status.void
                for a in self._resultsmap.values()
            ]
        )

    def finalise(self, *r_ids):
        """Given a **r_ids** list of delayed action IDs, wait upon actions completion."""
        raise NotImplementedError()

    def retrieve(self, r_id, bareobject=False):
        """Given a **r_id** delayed action ID, returns the corresponding result.

        If need be, :meth:`finalise` is called.
        """
        action = self._resultsmap[r_id]
        try:
            if action.status == d_action_status.void:
                self.finalise(r_id)
                assert action.status != d_action_status.void, (
                    "Finalise does not seem to work."
                )
        finally:
            del self._resultsmap[r_id]
            self._history.append("USED", "id={!s}".format(action.id))
        if bareobject:
            return action
        else:
            if action.status == d_action_status.done:
                return action.result
            else:
                return False

    def __str__(self):
        return self.describe(fulldump=False)

    def describe(self, fulldump=False):
        """Print the object's characteristics and content."""
        res = "DelayedActionsHandler object of class: {:s}\n".format(
            self.__class__
        )
        for k, v in self.footprint_as_shallow_dict().items():
            res += "  * {:s}: {!s}\n".format(k, v)
        if fulldump:
            res += "\n  * Todo list (i.e still to be processed):\n\n"
            res += "\n".join(
                [
                    "{:48s}:\n      request: {!s}".format(r_id, a.request)
                    for r_id, a in self._resultsmap.items()
                    if a.status == d_action_status.void
                ]
            )
            res += "\n  * Done (i.e the delayed action succeeded):\n\n"
            res += "\n".join(
                [
                    "{:48s}:\n      request: {!s}".format(r_id, a.request)
                    for r_id, a in self._resultsmap.items()
                    if a.status == d_action_status.done
                ]
            )
            res += "\n  * Failed (i.e the delayed action failed):\n\n"
            res += "\n".join(
                [
                    "{:48s}:\n      request: {!s}".format(r_id, a.request)
                    for r_id, a in self._resultsmap.items()
                    if a.status == d_action_status.failed
                ]
            )
            res += (
                "\n  * Unclear (i.e processed but the result is unclear):\n\n"
            )
            res += "\n".join(
                [
                    "{:48s}:\n      request: {!s}".format(r_id, a.request)
                    for r_id, a in self._resultsmap.items()
                    if a.status == d_action_status.unclear
                ]
            )
        return res


class AbstractFileBasedDelayedActionsHandler(AbstractDelayedActionsHandler):
    """
    A specialised version of :class:`AbstractDelayedActionsHandler` where
    a unique file (created in the ``stagedir``) is associated with each of the
    delayed action.
    """

    _abstract = True

    @property
    def resultid_stamp(self):
        """Some kind of string that identifies the present object."""
        raise NotImplementedError()

    def dispence_resultid(self):
        """Return a unique ID that will identify a new :class:`DelayedAction` object."""
        t_temp = tempfile.mkstemp(
            prefix="{:s}_{:d}".format(
                self.resultid_stamp, self.system.getpid()
            ),
            dir=self.stagedir,
        )
        os.close(t_temp[0])
        return self.system.path.basename(t_temp[1])

    def _create_delayed_action(self, r_id, request):
        """Create a :class:`DelayedAction` object given **r_id** and **request**."""
        d_action = DelayedAction(self.observerboard, r_id, request)
        d_action.result = self.system.path.join(self.stagedir, r_id)
        return d_action


def demo_sleeper_function(seconds):
    """Sleep for a while (demo)."""
    time.sleep(seconds)


class DemoSleepDelayedActionHandler(AbstractDelayedActionsHandler):
    """A Sleeper delayed action handler (Demonstration purposes)."""

    _footprint = dict(
        info="Demonstration purposes (sleep for a while).",
        attr=dict(
            kind=dict(
                values=[
                    "sleep",
                ],
            ),
        ),
    )

    def dispence_resultid(self):
        """Return a unique ID that will identify a new :class:`DelayedAction` object."""
        self._counter += 1
        return "sleeper_action_{:016d}".format(self._counter)

    def _custom_init(self):
        """Create the multiprocessing pool."""
        self._ppool = multiprocessing.Pool(processes=2)
        self._counter = 0

    def destroy(self):
        """Destry the multiprocessing pool before leaving."""
        self._ppool.close()
        self._ppool.terminate()
        self._ppool = None
        super().destroy()

    def _create_delayed_action(self, r_id, request):
        """Start the asynchronous processing."""
        daction = DelayedAction(self.observerboard, r_id, request)
        daction.result = self._ppool.apply_async(
            demo_sleeper_function, (request,)
        )
        return daction

    def finalise(self, *r_ids):
        """Wait until completion."""
        for r_id in r_ids:
            action = self._resultsmap[r_id]
            action.result.wait()
            if action.result.successful():
                action.mark_as_done()
            else:
                action.mark_as_failed()


class AbstractFtpArchiveDelayedGetHandler(
    AbstractFileBasedDelayedActionsHandler
):
    """Includes some FTP related methods"""

    _abstract = True
    _footprint = dict(
        info="Fetch multiple files using an FTP archive.",
        attr=dict(
            kind=dict(
                values=[
                    "archive",
                ],
            ),
            storage=dict(),
            goal=dict(
                values=[
                    "get",
                ]
            ),
            tube=dict(
                values=[
                    "ftp",
                ],
            ),
            raw=dict(
                type=bool,
                optional=True,
                default=False,
            ),
            logname=dict(optional=True),
        ),
    )

    @property
    def resultid_stamp(self):
        bangfmt = (
            "{0.logname:s}@{0.storage:s}" if self.logname else "{0.storage:s}"
        )
        return ("rawftget_" + bangfmt).format(self)

    def register(self, request):
        """Create a new :class:`DelayedAction` object from a user's **request**."""
        assert isinstance(request, (tuple, list)) and len(request) == 2, (
            "Request needs to be a two element tuple or list (location, format)"
        )
        # Check for duplicated entries...
        target = request[0]
        for v in self._resultsmap.values():
            if target == v.request[0]:
                return None
        # Ok, let's proceed...
        return super().register(request)

    @property
    def _ftp_hostinfos(self):
        """Return the FTP hostname end port number."""
        s_storage = self.storage.split(":", 1)
        hostname = s_storage[0]
        port = None
        if len(s_storage) > 1:
            try:
                port = int(s_storage[1])
            except ValueError:
                logger.error(
                    "Invalid port number < %s >. Ignoring it", s_storage[1]
                )
        return hostname, port


class RawFtpDelayedGetHandler(AbstractFtpArchiveDelayedGetHandler):
    """
    When FtServ is used, accumulate "GET" requests for several files and fetch
    them during a unique ``ftget`` system call.

    :note: The *request* needs to be a two-elements tuple where the first element
           is the path to the file that shoudl be fetched and the second element
           the file format.
    :note: The **result** returned by the :meth:`retrieve` method will be the
           path to the temporary file where the resource has been fetched.
    """

    _footprint = dict(
        info="Fetch multiple files using FtServ.",
        attr=dict(
            raw=dict(
                optional=False,
                values=[
                    True,
                ],
            ),
        ),
    )

    def finalise(self, *r_ids):  # @UnusedVariable
        """Given a **r_ids** list of delayed action IDs, wait upon actions completion."""
        todo = defaultdict(list)
        for k, v in self._resultsmap.items():
            if v.status == d_action_status.void:
                a_fmt = (
                    v.request[1]
                    if self.system.fmtspecific_mtd(
                        "batchrawftget", v.request[1]
                    )
                    else None
                )
                todo[a_fmt].append(k)
        rc = True
        if todo:
            for a_fmt, a_todolist in todo.items():
                sources = list()
                destinations = list()
                extras = dict()
                if a_fmt is not None:
                    extras["fmt"] = a_fmt
                for k in a_todolist:
                    sources.append(self._resultsmap[k].request[0])
                    destinations.append(self._resultsmap[k].result)
                try:
                    logger.info(
                        "Running the ftserv command for format=%s.", str(a_fmt)
                    )
                    hostname, port = self._ftp_hostinfos
                    rc = self.system.batchrawftget(
                        sources,
                        destinations,
                        hostname=hostname,
                        logname=self.logname,
                        port=port,
                        **extras,
                    )
                except OSError:
                    rc = [
                        None,
                    ] * len(sources)
                for i, k in enumerate(a_todolist):
                    if rc[i] is True:
                        self._resultsmap[k].mark_as_done()
                    elif rc[i] is False:
                        self._resultsmap[k].mark_as_failed()
                    else:
                        self._resultsmap[k].mark_as_unclear()
        return rc


class PrivateDelayedActionsHub:
    """
    Manages all of the delayed actions request by forwarding them to the appropriate
    :class:`AbstractDelayedActionsHandler` object.

    If no, :class:`AbstractDelayedActionsHandler` class is able to handle
    the delayed action, just returns ``None`` to inform the caller that the
    requested action can't be performed
    """

    def __init__(self, sh, contextrundir):
        """
        :param vortex.tools.systems.OSExtended sh: The current usable System object
        :param str contextrundir: The current context's run directory where the
                                  staging area/directory will be created. If ``None``,
                                  the staging directory is created in the current
                                  working directory.
        """
        self._sh = sh
        self._contextrundir = contextrundir
        self._stagedir = None
        self._delayedactionshandlers = set()
        self._obsboard = observer.SecludedObserverBoard()
        self._resultsmap = dict()

    @property
    def observerboard(self):
        """The Observer board associated with this Hub;

        :note: Anyone is free to register to it in order be kept informed when a
               delayed action associated with this Hub is updated.
        """
        return self._obsboard

    @property
    def stagedir(self):
        """This Hub staging area/directory (i.e. where results can be stored)."""
        if self._stagedir is None:
            self._stagedir = tempfile.mkdtemp(
                prefix="dactions_staging_area_",
                dir=(
                    self._contextrundir
                    if self._contextrundir
                    else self._sh.pwd()
                ),
            )
        return self._stagedir

    def showhistory(self):
        """
        Print the complete logs of all of the :class:`AbstractDelayedActionsHandler`
        objects leveraged by this Hub.
        """
        for handler in self._delayedactionshandlers:
            print("{!r} says:\n".format(handler))
            handler.history.show()

    def actionhistory(self, r_id):
        """Print the log lines associated to a given request (identified by its **r_id** ID)."""
        for handler in self._delayedactionshandlers:
            hst = handler.grephistory(r_id)
            if hst:
                print("{!r} says:".format(handler))
                handler.showhistory(r_id)

    def register(self, request, **kwargs):
        """Take into consideration a new delayed action request.

        :param request: A description of the user's request
        :param dict kwargs: Any argument that will be used to create the
                            :class:`AbstractDelayedActionsHandler` object
        """
        # Prestaging tool descriptions
        myhandler_desc = dict(
            system=self._sh,
            observerboard=self._obsboard,
            stagedir=self.stagedir,
        )
        myhandler_desc.update(kwargs)
        myhandler = None
        # Scan pre-existing prestaging tools to find a suitable one
        for ahandler in self._delayedactionshandlers:
            if ahandler.footprint_reusable() and ahandler.footprint_compatible(
                myhandler_desc
            ):
                logger.debug(
                    "Re-usable Actions Handler found: %s",
                    lightdump(myhandler_desc),
                )
                myhandler = ahandler
                break
        # If necessary, create a new one
        if myhandler is None:
            myhandler = fpx.delayedactionshandler(
                _emptywarning=False, **myhandler_desc
            )
            if myhandler is not None:
                logger.debug(
                    "Fresh prestaging tool created: %s",
                    lightdump(myhandler_desc),
                )
                self._delayedactionshandlers.add(myhandler)
        # Let's role
        if myhandler is None:
            logger.debug(
                "Unable to find a delayed actions handler with: %s",
                lightdump(myhandler_desc),
            )
            return None
        else:
            resultid = myhandler.register(request)
            if resultid is not None:
                self._resultsmap[resultid] = myhandler
        return resultid

    @property
    def dirty(self):
        """Is there any of the hub's delayed actions that needs finalising ?"""
        dirtyflag = False
        for ahandler in self._delayedactionshandlers:
            dirtyflag = dirtyflag or ahandler.dirty
        return dirtyflag

    def finalise(self, *r_ids):
        """Given a **r_ids** list of delayed action IDs, wait upon actions completion."""
        todo = defaultdict(set)
        for r_id in r_ids:
            todo[self._resultsmap[r_id]].add(r_id)
        for ahandler, r_ids in todo.items():
            ahandler.finalise(*list(r_ids))

    def retrieve(self, resultid, bareobject=False):
        """Given a **resultid** delayed action ID, returns the corresponding result."""
        try:
            res = self._resultsmap[resultid].retrieve(
                resultid, bareobject=bareobject
            )
        finally:
            del self._resultsmap[resultid]
        return res

    def clear(self):
        """Destroy all of the associated handlers and reset everything."""
        for a_handler in self._delayedactionshandlers:
            a_handler.destroy()
        self._delayedactionshandlers = set()
        self._obsboard = observer.SecludedObserverBoard()
        self._resultsmap = dict()
        self._stagedir = None

    def __repr__(self):
        return "{:s} | n_delayedactionshandlers={:d}>".format(
            super().__repr__().rstrip(">"), len(self._delayedactionshandlers)
        )

    def __str__(self):
        return (
            repr(self)
            + "\n\n"
            + "\n\n".join(
                [
                    ahandler.describe(fulldump=True)
                    for ahandler in self._delayedactionshandlers
                ]
            )
        )


class DelayedActionsHub(PrivateDelayedActionsHub, getbytag.GetByTag):
    """
    A subclass of :class:`PrivateDelayedActionsHub` that uses
    :class:`footprints.util.GetByTag` to remain persistent in memory.

    Therefore, a *tag* attribute needs to be specified when building/retrieving
    an object of this class.
    """

    pass


if __name__ == "__main__":
    import doctest

    doctest.testmod()
