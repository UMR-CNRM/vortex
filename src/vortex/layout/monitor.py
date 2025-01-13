"""
This module defines generic classes that are used to check the state of a list of
sections
"""

import queue

from collections import defaultdict, namedtuple, OrderedDict
from itertools import islice, compress
import multiprocessing
import sys
import threading
import time
import traceback

from bronx.fancies import loggers
from bronx.patterns import observer
from bronx.stdtypes import date

from vortex.tools.parallelism import ParallelSilencer, ParallelResultParser

logger = loggers.getLogger(__name__)

#: No automatic export.
__all__ = []


#: Class for possible states of a :class:`InputMonitorEntry` object
EntryStateTuple = namedtuple(
    "EntryStateTuple", ["ufo", "expected", "available", "failed"]
)

#: Predefined :class:`InputMonitorEntry` state values
EntrySt = EntryStateTuple(
    ufo="ufo", expected="expected", available="available", failed="failed"
)

#: Class for possible states of a :class:`_Gang` object
GangStateTuple = namedtuple(
    "GangStateTuple", ["ufo", "collectable", "pcollectable", "failed"]
)

#: Predefined :class:`_Gang` state values
GangSt = GangStateTuple(
    ufo="undecided",
    collectable="collectable",
    pcollectable="collectable_partial",
    failed="failed",
)


class LayoutMonitorError(Exception):
    """The default exception for this module."""

    pass


class _StateFull:
    """Defines an abstract interface: a class with a state."""

    _mystates = EntrySt  # The name of possible states

    def __init__(self):
        """Initialise the state attribute and setup the observer."""
        self._state = self._mystates.ufo
        self._obsboard = observer.SecludedObserverBoard()
        self._obsboard.notify_new(self, dict(state=self._state))

    @property
    def observerboard(self):
        """The entry's observer board."""
        return self._obsboard

    def _state_changed(self, previous, new):
        pass

    def _get_state(self):
        return self._state

    def _set_state(self, newstate):
        if newstate != self._state:
            previous = self._state
            self._state = newstate
            self._state_changed(previous, self._state)
            self._obsboard.notify_upd(
                self, dict(state=self._state, previous_state=previous)
            )

    state = property(_get_state, _set_state, doc="The entry's state.")


class _StateFullMembersList:
    """Defines an abstract interface: a class with members."""

    _mstates = EntrySt  # The name of possible member's states
    _mcontainer = set  # The container class for the members

    def __init__(self):
        """Initialise the members list."""
        self._members = dict()
        for st in self._mstates:
            self._members[st] = self._mcontainer()

    def _unregister_i(self, item):
        item.observerboard.unregister(self)
        return item

    @property
    def members(self):
        """Members classified by state."""
        return self._members

    def _itermembers(self):
        """
        Iterate over all members: not safe if a given member is move from a
        queue to another. That's why it's not public.
        """
        for st in self._mstates:
            yield from self._members[st]

    @property
    def memberslist(self):
        """The list of all the members."""
        return list(self._itermembers())


class InputMonitorEntry(_StateFull):
    def __init__(self, section):
        """An entry manipulated by a :class:`BasicInputMonitor` object.

        :param vortex.layout.dataflow.Section section: The section associated
            with this entry
        """
        _StateFull.__init__(self)
        self._nchecks = 0
        self._section = section

    @property
    def nchecks(self):
        """
        The number of checks performed for this entry before it was moved to
        `available` or `failed`.
        """
        return self._nchecks

    def check_done(self):
        """Internal use: increments the nchecks count."""
        self._nchecks += 1

    @property
    def section(self):
        """The section associated with this entry."""
        return self._section


class _MonitorSilencer(ParallelSilencer):
    """My own Silencer."""

    def export_result(self, key, ts, prevstate, state):
        """Returns the recorded data, plus state related informations."""
        return dict(
            report=super().export_result(),
            name="Input #{!s}".format(key),
            key=key,
            prevstate=prevstate,
            state=state,
            timestamp=ts,
        )


class ManualInputMonitor(_StateFullMembersList):
    """
    This object looks into the *targets* list of :class:`InputMonitorEntry`
    objects and check regularly the status of each of the enclosed sections. If
    an expected resource is found the "get" command is issued.
    """

    _mcontainer = OrderedDict

    def __init__(
        self,
        context,
        targets,
        caching_freq=20,
        crawling_threshold=100,
        mute=False,
    ):
        """
        If the list of inputs is too long (see the *crawling_threshold*
        option), not all of the inputs will be checked at once: The first
        *crawling_threshold* inputs will always be checked and an additional
        batch of *crawling_threshold* other inputs will be checked (in a round
        robin manner)

        If the inputs we are looking at have a *term* attribute, the input lists
        will automatically be ordered according to the *term*.

        :param vortex.layout.contexts.Context context: The object that is used
            as a source of inputs
        :param targets: The list of :class:`InputMonitorEntry` to look after
        :param int caching_freq: We will update the sections statuses every N
            seconds
        :param int crawling_threshold: Maximum number of section statuses to
            update at once

        :warning: The state of the sections is looked up by a background process.
            Consequently the **stop** method must always be called when the
            processing is done (in order for the background process to terminate).
        """
        _StateFullMembersList.__init__(self)

        self._ctx = context
        self._seq = context.sequence
        self._caching_freq = caching_freq
        self._crawling_threshold = crawling_threshold
        self._mute = mute
        self._inactive_since = time.time()
        self._last_healthcheck = 0

        # Control objects for multiprocessing
        self._mpqueue = multiprocessing.Queue(maxsize=0)  # No limit !
        self._mpquit = multiprocessing.Event()
        self._mperror = multiprocessing.Event()
        self._mpjob = None

        # Generate the first list of sections
        toclassify = list(targets)

        # Sort the list of UFOs if sensible (i.e. if all resources have a term)
        has_term = 0
        map_term = defaultdict(int)
        for e in toclassify:
            if hasattr(e.section.rh.resource, "term"):
                has_term += 1
                map_term[e.section.rh.resource.term.fmthm] += 1
        if toclassify and has_term == len(toclassify):
            toclassify.sort(key=lambda e: e.section.rh.resource.term)
            # Use a crawling threshold that is large enough to span a little bit
            # more than one term.
            self._crawling_threshold = max(
                self._crawling_threshold, int(max(map_term.values()) * 1.25)
            )

        # Create key/value pairs
        toclassify = [(i, e) for i, e in enumerate(toclassify)]

        # Classify the input depending on there stage
        self._map_stages = dict(
            expected=EntrySt.expected, get=EntrySt.available
        )
        while toclassify:
            e = toclassify.pop(0)
            self._append_entry(self._find_state(e[1], onfails=EntrySt.ufo), e)

    def start(self):
        """Start the background updater task."""
        self._mpjob = multiprocessing.Process(
            name="BackgroundUpdater",
            target=self._background_updater_job,
            args=(),
        )
        self._mpjob.start()

    def stop(self):
        """Ask the background process in charge of updates to stop."""
        # Is the process still running ?
        if self._mpjob.is_alive():
            # Try to stop it nicely
            self._mpquit.set()
            t0 = date.now()
            self._mpjob.join(5)
            waiting = date.now() - t0
            logger.info(
                "Waiting for the background process to stop took %f seconds",
                waiting.total_seconds(),
            )
            # Be less nice if needed...
            if self._mpjob.is_alive():
                logger.warning("Force termination of the background process")
                self._mpjob.terminate()
                time.sleep(1)  # Allow some time for the process to terminate
            # Wrap up
            rc = not self._mperror.is_set()
            logger.info("Server still alive ? %s", str(self._mpjob.is_alive()))
            if not rc:
                raise LayoutMonitorError("The background process ended badly.")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exctype, excvalue, exctb):
        self.stop()

    def _itermembers(self):
        """
        Iterate over all members: not safe if a given member is move from a
        queue to another. That's why it's not public.
        """
        for st in self._mstates:
            yield from self._members[st].values()

    def _find_state(self, e, onfails=EntrySt.failed):
        """Find the entry's state given the section's stage."""
        return self._map_stages.get(e.section.stage, onfails)

    def _append_entry(self, queue, e):
        """Add an entry into one of the processing queues."""
        self._members[queue][e[0]] = e[1]
        e[1].state = queue

    def _key_update(self, res):
        """Process a result dictionary of the _background_updater method."""
        e = self._members[res["prevstate"]].pop(res["key"], None)
        # The entry might be missing if someone mess with the _memebers dicitonary
        if e is not None:
            self._append_entry(res["state"], (res["key"], e))
            self._inactive_since = res["timestamp"]

    def _background_updater(self):
        """This method loops on itself regularly to update the entry's state."""

        # Initialisation
        last_refresh = 0
        kangaroo_idx = 0

        # Stop if we are asked to or if there is nothing more to do
        while not self._mpquit.is_set() and not (
            len(self._members[EntrySt.expected]) == 0
            and len(self._members[EntrySt.ufo]) == 0
        ):
            # Tweak the caching_frequency
            if (
                len(self._members[EntrySt.ufo])
                and len(self._members[EntrySt.expected])
                <= self._crawling_threshold
                and not len(self._members[EntrySt.available])
            ):
                # If UFO are still there and not much resources are expected,
                # decrease the caching time
                eff_caching_freq = max(3, self._caching_freq / 5)
            else:
                eff_caching_freq = self._caching_freq

            curtime = time.time()
            # Crawl into the monitored input if sensible
            if curtime > last_refresh + eff_caching_freq:
                last_refresh = curtime
                result_stack = list()

                # Crawl into the ufo list
                # Always process the first self._crawling_threshold elements
                for k, e in islice(
                    self._members[EntrySt.ufo].items(),
                    self._crawling_threshold,
                ):
                    if self._mpquit.is_set():  # Are we ordered to stop ?
                        break
                    with _MonitorSilencer(
                        self._ctx, "inputmonitor_updater"
                    ) as psi:
                        logger.info(
                            "First get on local file: %s",
                            e.section.rh.container.localpath(),
                        )
                        e.section.get(
                            incache=True, fatal=False
                        )  # Do not crash at this stage
                        res = psi.export_result(
                            k, curtime, e.state, self._find_state(e)
                        )
                    self._mpqueue.put_nowait(res)
                    result_stack.append(res)

                # What are the expected elements we will look for ?
                # 1. The first self._crawling_threshold elements
                exp_compress = [
                    1,
                ] * min(
                    self._crawling_threshold,
                    len(self._members[EntrySt.expected]),
                )
                # 2. An additional set of self._crawling_threshold rotating elements
                for i in range(
                    max(
                        0,
                        len(self._members[EntrySt.expected])
                        - self._crawling_threshold,
                    )
                ):
                    kdiff = i - kangaroo_idx
                    exp_compress.append(
                        1
                        if kdiff >= 0 and kdiff < self._crawling_threshold
                        else 0
                    )

                # Crawl into the chosen items of the expected list
                (visited, found, kangaroo_incr) = (0, 0, 0)
                for i, (k, e) in enumerate(
                    compress(
                        self._members[EntrySt.expected].items(), exp_compress
                    )
                ):
                    if self._mpquit.is_set():  # Are we ordered to stop ?
                        break

                    # Kangaroo check ?
                    kangaroo = i >= self._crawling_threshold
                    kangaroo_incr += int(kangaroo)
                    if kangaroo and found > self._crawling_threshold / 2:
                        # If a lot of resources were already found, avoid harassment
                        break

                    logger.debug(
                        "Checking local file: %s (kangaroo=%s)",
                        e.section.rh.container.localpath(),
                        kangaroo,
                    )
                    e.check_done()
                    # Is the promise file still there or not ?
                    if e.section.rh.is_grabable():
                        visited += 1
                        with _MonitorSilencer(
                            self._ctx, "inputmonitor_updater"
                        ) as psi:
                            if e.section.rh.is_grabable(check_exists=True):
                                logger.info(
                                    "The local resource %s becomes available",
                                    e.section.rh.container.localpath(),
                                )
                                # This will crash in case of an error, but this should
                                # not happen since we checked the resource just above
                                e.section.get(incache=True)
                                found += 1
                                res = psi.export_result(
                                    k, curtime, e.state, self._find_state(e)
                                )
                            else:
                                logger.warning(
                                    "The local resource %s has failed",
                                    e.section.rh.container.localpath(),
                                )
                                res = psi.export_result(
                                    k, curtime, e.state, EntrySt.failed
                                )
                        self._mpqueue.put_nowait(res)
                        result_stack.append(res)

                # Update the kangaroo index
                kangaroo_idx = kangaroo_idx + kangaroo_incr - visited
                if (
                    kangaroo_idx
                    > len(self._members[EntrySt.expected])
                    - self._crawling_threshold
                    - 1
                ):
                    kangaroo_idx = 0

                # Effectively update the internal _members dictionary
                for r in result_stack:
                    self._key_update(r)

            # Do frequent checks to look carefully into the _mpquit event
            time.sleep(0.25)

    def _background_updater_job(self):
        """Start the updater and check for uncatched exceptions."""
        self._ctx.system.signal_intercept_on()
        try:
            self._background_updater()
        except Exception:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            print("Exception type: {!s}".format(exc_type))
            print("Exception info: {!s}".format(exc_value))
            print("Traceback:")
            print("\n".join(traceback.format_tb(exc_traceback)))
            # Alert the main process of the error
            self._mperror.set()

    def _refresh(self):
        """Called whenever the user asks something."""
        # Look into the result queue
        prp = None
        # That's bad...
        if self._mperror.is_set():
            self.stop()
            raise LayoutMonitorError("The background process ended badly.")
        # Process all the available update messages
        while True:
            try:
                r = self._mpqueue.get_nowait()
            except queue.Empty:
                break
            if prp is None:
                prp = ParallelResultParser(self._ctx)
            if not self._mute:
                self._ctx.system.highlight(
                    "The InputMonitor got news for: {!s}".format(r["name"])
                )
            prp(r)
            print()
            self._key_update(r)

    @property
    def all_done(self):
        """Are there any ufo or expected sections left ?"""
        self._refresh()
        return (
            len(self._members[EntrySt.expected]) == 0
            and len(self._members[EntrySt.ufo]) == 0
        )

    @property
    def inactive_time(self):
        """The time (in sec) since the last action (successful or not)."""
        return time.time() - self._inactive_since

    @property
    def ufo(self):
        """The dictionary of sections in an unknown state."""
        self._refresh()
        return self._members[EntrySt.ufo]

    @property
    def expected(self):
        """The dictionary of expected sections."""
        self._refresh()
        return self._members[EntrySt.expected]

    @property
    def available(self):
        """The dictionary of sections that were successfully fetched."""
        self._refresh()
        return self._members[EntrySt.available]

    def pop_available(self):
        """Pop an entry in the 'available' dictionary."""
        return self._unregister_i(self.available.popitem(last=False)[1])

    @property
    def failed(self):
        """The dictionary of failed sections."""
        self._refresh()
        return self._members[EntrySt.failed]

    def health_check(self, interval=0):
        """Log the monitor's state.

        :param int interval: Log something at most every *interval* seconds.
        """
        time_now = time.time()
        if time_now - self._last_healthcheck > interval:
            self._last_healthcheck = time_now
            logger.info(
                "Still waiting (ufo=%d, expected=%d, available=%d, failed=%d)...",
                len(self._members[EntrySt.ufo]),
                len(self._members[EntrySt.expected]),
                len(self._members[EntrySt.available]),
                len(self._members[EntrySt.failed]),
            )

    def is_timedout(self, timeout, exception=None):
        """Check if a timeout occurred.

        :param int timeout: The wanted timeout in seconds.
        :param Exception exception: The exception that will be raised if a timeout occurs.
        """
        rc = False
        self._refresh()
        if (timeout > 0) and (self.inactive_time > timeout):
            logger.error("The waiting loop timed out (%d seconds)", timeout)
            logger.error(
                "The following files are still unaccounted for: %s",
                ",".join(
                    [
                        e.section.rh.container.localpath()
                        for e in self.expected.values()
                    ]
                ),
            )
            rc = True
        if rc and exception is not None:
            raise exception("The waiting loop timed-out")
        return rc


class BasicInputMonitor(ManualInputMonitor):
    """
    This object looks into the effective_inputs and checks regularly the
    status of each section. If an expected resource is found the "get"
    command is issued.
    """

    _mcontainer = OrderedDict

    def __init__(
        self,
        context,
        role=None,
        kind=None,
        caching_freq=20,
        crawling_threshold=100,
        mute=False,
    ):
        """
        If the list of inputs is too long (see the *crawling_threshold*
        option), not all of the inputs will be checked at once: The first
        *crawling_threshold* inputs will always be checked and an additional
        batch of *crawling_threshold* other inputs will be checked (in a round
        robin manner)

        If the inputs we are looking at have a *term* attribute, the input lists
        will automatically be ordered according to the *term*.

        :param vortex.layout.contexts.Context context: The object that is used
            as a source of inputs
        :param str role: The role of the sections that will be watched
        :param str kind: The kind of the sections that will be watched (used only
            if role is not specified)
        :param int caching_freq: We will update the sections statuses every N
            seconds
        :param int crawling_threshold: Maximum number of section statuses to
            update at once

        :warning: The state of the sections is looked up by a background process.
            Consequently the **stop** method must always be called when the
            processing is done (in order for the background process to terminate).
        """
        self._role = role
        self._kind = kind
        assert not (self._role is None and self._kind is None)
        ManualInputMonitor.__init__(
            self,
            context,
            [
                InputMonitorEntry(x)
                for x in context.sequence.filtered_inputs(
                    role=self._role, kind=self._kind
                )
            ],
            caching_freq=caching_freq,
            crawling_threshold=crawling_threshold,
            mute=mute,
        )


class _Gang(observer.Observer, _StateFull, _StateFullMembersList):
    """
    A Gang is a collection of :class:`InputMonitorEntry` objects or a collection
    of :class:`_Gang` objects.

    The members of the Gang are classified depending on their state. The state
    of each of the members may change, that's why the Gang registers as an
    observer to its members.

    The state of a Gang depends on the states of its members.

    :note: Since a Gang may be a collection of Gangs, a Gang is also an observee.
    """

    _mystates = GangSt

    def __init__(self):
        """

        :parameters: None
        """
        _StateFull.__init__(self)
        _StateFullMembersList.__init__(self)
        self._nmembers = 0
        self.info = dict()
        self._t_lock = threading.RLock()

    @property
    def nickname(self):
        """A fancy representation of the Gang's motive."""
        if not self.info:
            return "Anonymous"
        else:
            return ", ".join(
                ["{:s}={!s}".format(k, v) for k, v in self.info.items()]
            )

    def add_member(self, *members):
        """Introduce one or several members to the Gang."""
        with self._t_lock:
            for member in members:
                member.observerboard.register(self)
                self._members[member.state].add(member)
                self._nmembers += 1
            self._refresh_state()

    def __len__(self):
        """The number of gang members."""
        return self._nmembers

    def updobsitem(self, item, info):
        """React to an observee notification."""
        with self._t_lock:
            observer.Observer.updobsitem(self, item, info)
            # Move the item around
            self._members[info["previous_state"]].remove(item)
            self._members[info["state"]].add(item)
            # Update my own state
            self._refresh_state()

    def _is_collectable(self):
        raise NotImplementedError

    def _is_pcollectable(self):
        raise NotImplementedError

    def _is_undecided(self):
        raise NotImplementedError

    def _refresh_state(self):
        """Update the state of the Gang."""
        if self._is_collectable():
            self.state = self._mystates.collectable
        elif self._is_pcollectable():
            self.state = self._mystates.pcollectable
        elif self._is_undecided():
            self.state = self._mystates.ufo
        else:
            self.state = self._mystates.failed


class BasicGang(_Gang):
    """A Gang of :class:`InputMonitorEntry` objects.

    Such a Gang may have 4 states:

        * undecided: Some of the members are still expected (and the
          *waitlimit* time is not exhausted)
        * collectable: All the members are available
        * collectable_partial: At least *minsize* members are available, but some
          of the members are late (because the *waitlimit* time is exceeded) or
          have failed.
        * failed: There are to many failed members (given *minsize*)
    """

    _mstates = EntrySt

    def __init__(self, minsize=0, waitlimit=0):
        """

        :param int minsize: The minimum size for this Gang to be in a
                            collectable_partial state (0 means that all the
                            members must be available)
        :param int waitlimit: If > 0, wait no more than N sec after the first change
                              of state
        """
        self.minsize = minsize
        self.waitlimit = waitlimit
        self._waitlimit_timer = None
        self._firstseen = None
        super().__init__()

    def _state_changed(self, previous, new):
        super()._state_changed(previous, new)
        # Remove the waitlimit timer
        if self._waitlimit_timer is not None and not self._ufo_members:
            self._waitlimit_timer.cancel()
            logger.debug(
                "Waitlimit Timer thread canceled: %s (Gang: %s)",
                self._waitlimit_timer,
                self.nickname,
            )
            self._waitlimit_timer = None
        # Print some diagnosis data
        if self.info and new != self._mystates.ufo:
            msg = "State changed from {:s} to {:s} for Gang: {:s}".format(
                previous, new, self.nickname
            )
            if new == self._mystates.pcollectable:
                if self._ufo_members:
                    logger.warning(
                        "%s\nSome of the Gang's members are still expected "
                        + "but the %d seconds waitlimit is exhausted.",
                        msg,
                        self.waitlimit,
                    )
                else:
                    logger.warning(
                        "%s\nSome of the Gang's members have failed.", msg
                    )
            else:
                logger.info(msg)

    def _set_waitlimit_timer(self):
        if self.waitlimit > 0:

            def _waitlimit_check():
                with self._t_lock:
                    self._refresh_state()
                    logger.debug(
                        "Waitlimit Timer thread done: %s (Gang: %s)",
                        self._waitlimit_timer,
                        self.nickname,
                    )
                    self._waitlimit_timer = None

            self._waitlimit_timer = threading.Timer(
                self.waitlimit + 1, _waitlimit_check
            )
            self._waitlimit_timer.daemon = True
            self._waitlimit_timer.start()
            logger.debug(
                "Waitlimit Timer thread started: %s (Gang: %s)",
                self._waitlimit_timer,
                self.nickname,
            )

    def add_member(self, *members):
        with self._t_lock:
            super().add_member(*members)
            if self._firstseen is None and any(
                [m.state == self._mstates.available for m in members]
            ):
                self._firstseen = time.time()
                self._set_waitlimit_timer()

    def updobsitem(self, item, info):
        with self._t_lock:
            super().updobsitem(item, info)
            if (
                self._firstseen is None
                and info["state"] == self._mstates.available
            ):
                self._firstseen = time.time()
                self._set_waitlimit_timer()

    @property
    def _eff_minsize(self):
        """If minsize==0, the effective minsize will be equal to the Gang's len."""
        return self.minsize if self.minsize > 0 else len(self)

    @property
    def _ufo_members(self):
        """The number of ufo members (from a Gang point of view)."""
        return len(self._members[self._mstates.ufo]) + len(
            self._members[self._mstates.expected]
        )

    def _is_collectable(self):
        return len(self._members[self._mstates.available]) == len(self)

    def _is_pcollectable(self):
        return len(
            self._members[self._mstates.available]
        ) >= self._eff_minsize and (
            self._ufo_members == 0
            or (
                self._firstseen is not None
                and time.time() - self._firstseen > self.waitlimit > 0
            )
        )

    def _is_undecided(self):
        return (
            len(self._members[self._mstates.available]) + self._ufo_members
            >= self._eff_minsize
        )


class MetaGang(_Gang):
    """A Gang of :class:`_Gang` objects.

    Such a Gang may have 4 states:

        * undecided: Some of the members are still undecided
        * collectable: All the members are collectable
        * collectable_partial: Some of the member are only collectable_partial
          and the rest are collectable
        * failed: One of the member has failed
    """

    _mstates = GangSt

    def has_ufo(self):
        """Is there at least one UFO member ?"""
        return len(self._members[self._mstates.ufo])

    def has_collectable(self):
        """Is there at least one collectable member ?"""
        return len(self._members[self._mstates.collectable])

    def has_pcollectable(self):
        """Is there at least one collectable or collectable_partial member ?"""
        return len(self._members[self._mstates.pcollectable]) + len(
            self._members[self._mstates.collectable]
        )

    def pop_collectable(self):
        """Retrieve a collectable member."""
        return self._unregister_i(
            self._members[self._mstates.collectable].pop()
        )

    def pop_pcollectable(self):
        """Retrieve a collectable or a collectable_partial member."""
        if self.has_collectable():
            return self.pop_collectable()
        else:
            return self._unregister_i(
                self._members[self._mstates.pcollectable].pop()
            )

    def consume_colectable(self):
        """Retriece all collectable members (as a generator)."""
        while self.has_collectable():
            yield self.pop_collectable()

    def consume_pcolectable(self):
        """Retriece all collectable or collectable_partial members (as a generator)."""
        while self.has_pcollectable():
            yield self.pop_pcollectable()

    def _is_collectable(self):
        return len(self._members[self._mstates.collectable]) == len(self)

    def _is_pcollectable(self):
        return (
            len(self._members[self._mstates.collectable])
            + len(self._members[self._mstates.pcollectable])
        ) == len(self)

    def _is_undecided(self):
        return len(self._members[self._mstates.failed]) == 0


class AutoMetaGang(MetaGang):
    """
    A :class:`MetaGang` with a method that automatically populates the Gang
    given a :class:`BasicInputMonitor` object.
    """

    def autofill(self, bm, grouping_keys, allowmissing=0, waitlimit=0):
        """
        Crawl into the *bm* :class:`BasicInputMonitor`'s entries, create
        :class:`BasicGang` objects based on the resource's attributes listed in
        *grouping_keys* and finally add these gangs to the current object.

        :param vortex.layout.monitor.BasicInputMonitor bm: The BasicInputMonitor
                                                           that will be explored
        :param list[str] grouping_keys: The attributes that are used to discriminate the gangs
        :param int allowmissing: The number of missing members allowed for a gang
            (It will be used to initialise the member gangs *minsize* attribute)
        :param int waitlimit: The *waitlimit* attribute of the member gangs
        """
        # Initialise the gangs
        mdict = defaultdict(list)
        for entry in bm.memberslist:
            entryid = tuple(
                [
                    entry.section.rh.wide_key_lookup(key)
                    for key in grouping_keys
                ]
            )
            mdict[entryid].append(entry)
        # Finalise the Gangs setup and use them...
        for entryid, members in mdict.items():
            gang = BasicGang(
                waitlimit=waitlimit, minsize=len(members) - allowmissing
            )
            gang.add_member(*members)
            gang.info = {k: v for k, v in zip(grouping_keys, entryid)}
            self.add_member(gang)
