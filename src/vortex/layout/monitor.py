#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines generic classes that are used to check the states of a list of
sections
"""

import time
from collections import defaultdict, namedtuple

from footprints import loggers, observers
logger = loggers.getLogger(__name__)


#: No automatic export.
__all__ = []


#: Definition of a EntrySt tuple
EntryStateTuple = namedtuple('EntryStateTuple',
                             ['ufo', 'expected', 'available', 'failed'],
                             verbose=False)

#: Predefined EntrySt values
EntrySt = EntryStateTuple(ufo='ufo', expected='expected', available='available',
                          failed='failed')

#: Definition of a GangSt tuple
GangStateTuple = namedtuple('GangStateTuple',
                            ['ufo', 'collectable', 'failed'],
                            verbose=False)

#: Predefined GangSt values
GangSt = GangStateTuple(ufo='undecided', collectable='collectable', failed='failed')


class InputMonitorEntry(object):

    def __init__(self, section):
        """An entry manipulated by a :class:`BasicInputMonitor` object.

        :param vortex.layout.dataflow.Section section: The section associated
            with this entry
        """
        self._nchecks = 0
        self._section = section
        self._state = EntrySt.ufo
        self._obsboard = observers.SecludedObserverBoard()
        self._obsboard.notify_new(self, dict(state=self._state))

    def __del__(self):
        self._obsboard.notify_del(self, dict(state=self._state))
        del self._obsboard

    @property
    def observerboard(self):
        """The entry's observer board."""
        return self._obsboard

    def get_state(self):
        return self._state

    def set_state(self, newstate):
        previous = self._state
        self._state = newstate
        if newstate != previous:
            self._obsboard.notify_upd(self, dict(state=self._state,
                                                 previous_state=previous))

    state = property(get_state, set_state, doc="The entry's state.")

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


class BasicInputMonitor(object):

    def __init__(self, sequence, role=None, kind=None,
                 caching_freq=20, crawling_threshold=100):
        """
        This object looks into the effective_inputs and check regularly the
        status of each of the sections. If an expected resource is found the
        "get" command is issued.

        If the list of inputs is too long (see the **crawling_threshold**
        option), not all of the inputs will be checked at once: The first
        **crawling_threshold** inputs will always be checked and an additional
        batch of **crawling_threshold** other inputs will be checked (in a round
        robin manner)

        If the inputs we are looking at have a *term* attribute, the input lists
        will automatically be ordered according to the *term*.

        :param Sequence sequence: The sequence object that is used as a source
            of inputs
        :param str role: The role of the sections that will be watched
        :param str kind: The kind of the sections that will be watched (used only
            if role is not specified)
        :param int caching_freq: We will update the sections statuses every N
            seconds
        :param int crawling_threshold: Maximum number of section status  to
            update at once
        """
        self._seq = sequence
        self._role = role
        self._kind = kind
        self._caching_freq = caching_freq
        self._crawling_threshold = crawling_threshold
        self._inactive_since = time.time()
        self._kangaroo_idx = 0

        assert(not(self._role is None and self._kind is None))

        # Generate the first list of sections
        toclassify = [InputMonitorEntry(x)
                      for x in self._seq.filtered_inputs(role=self._role, kind=self._kind)]
        # Initialise other lists
        self._members = dict()
        for st in EntrySt:
            self._members[st] = list()

        # Sort the list of UFOs if sensitive (i.e if all resources have a term)
        has_term = 0
        map_term = defaultdict(int)
        for e in toclassify:
            if hasattr(e.section.rh.resource, 'term'):
                has_term += 1
                map_term[e.section.rh.resource.term.fmthm] += 1
        if toclassify and has_term == len(toclassify):
            toclassify.sort(lambda a, b: cmp(a.section.rh.resource.term,
                                             b.section.rh.resource.term))
            # Use a crawling threshold that is large enough to span a little bit
            # more than one term.
            self._crawling_threshold = max(self._crawling_threshold,
                                           int(max(map_term.values()) * 1.25))

        # Map to classify UFOs
        self._map_stages = dict(expected=EntrySt.expected,
                                get=EntrySt.available)

        while toclassify:
            self._classify_ufo(toclassify.pop(0), onfails=EntrySt.ufo)

        # Give some time to the caller to process the first available files (if any)
        self._last_refresh = time.time() if len(self._members[EntrySt.available]) else 0

    def _append_entry(self, queue, e):
        self._members[queue].append(e)
        e.state = queue

    def _classify_ufo(self, e, onfails):
        self._append_entry(self._map_stages.get(e.section.stage, onfails), e)

    def _update_timestamp(self):
        self._inactive_since = time.time()

    def _check_entry_index(self, index):
        found = 0
        e = self._members[EntrySt.expected][index]
        e.check_done()
        if e.section.rh.is_grabable():
            found = 1
            self._update_timestamp()
            e = self._members[EntrySt.expected].pop(index)
            if e.section.rh.is_grabable(check_exists=True):
                logger.info("The local resource %s becomes available",
                            e.section.rh.container.localpath())
                e.section.get(incache=True)
                self._append_entry(EntrySt.available, e)
            else:
                logger.warning("The local resource %s has failed",
                               e.section.rh.container.localpath())
                self._append_entry(EntrySt.failed, e)
        return found

    def _refresh(self):
        curtime = time.time()
        # Tweak the caching_frequency
        if (len(self._members[EntrySt.ufo]) and
                len(self._members[EntrySt.expected]) <= self._crawling_threshold and
                not len(self._members[EntrySt.available])):
            # If UFO are still there and not much resources are expected,
            # decrease the caching time
            eff_caching_freq = max(3, self._caching_freq / 5)
        else:
            eff_caching_freq = self._caching_freq

        # Crawl into the monitored input if sensible
        if curtime > self._last_refresh + eff_caching_freq:
            self._last_refresh = curtime
            found = 0
            # Crawl into the ufo list
            # Always process the first self._crawling_threshold elements
            for i_e in range(min(self._crawling_threshold, len(self._members[EntrySt.ufo])) - 1, -1, -1):
                logger.info("First get on local file: %s",
                            self._members[EntrySt.ufo][i_e].section.rh.container.localpath())
                e = self._members[EntrySt.ufo].pop(i_e)
                e.check_done()
                self._update_timestamp()
                e.section.get(incache=True, fatal=False)  # Do not crash at this stage
                self._classify_ufo(e, onfails=self._failed)
            # Crawl into the expected list
            # Always process the first self._crawling_threshold elements
            for i_e in range(min(self._crawling_threshold, len(self._members[EntrySt.expected])) - 1, -1, -1):
                logger.debug("Checking local file: %s",
                             self._members[EntrySt.expected][i_e].section.rh.container.localpath())
                found += self._check_entry_index(i_e)
            # Do we attempt the kangaroo check ?
            if (len(self._members[EntrySt.expected]) > self._crawling_threshold and
                    found < self._crawling_threshold / 4):
                l_len = len(self._members[EntrySt.expected]) - self._crawling_threshold
                self._kangaroo_idx += self._crawling_threshold + 1
                if self._kangaroo_idx >= l_len:
                    l_endid = l_len - 1
                    self._kangaroo_idx = 0
                else:
                    l_endid = self._kangaroo_idx - 1
                for i_e in range(self._crawling_threshold + l_endid,
                                 max(l_endid - 1, self._crawling_threshold - 1), -1):
                    logger.debug("Checking local file (kangaroo): %s",
                                 self._members[EntrySt.expected][i_e].section.rh.container.localpath())
                    found += self._check_entry_index(i_e)

    @property
    def all_done(self):
        """Is there any ufo or expected sections left ?"""
        self._refresh()
        return (len(self._members[EntrySt.expected]) == 0 and
                len(self._members[EntrySt.ufo]) == 0)

    @property
    def members(self):
        """Members classified by state."""
        return self._members

    def itermembers(self):
        """Iterate over all members."""
        for st in EntrySt:
            for e in self._members[st]:
                yield e

    @property
    def inactive_time(self):
        """The time (in sec) since the last action (successful or not)."""
        return time.time() - self._inactive_since

    @property
    def ufo(self):
        """The list of sections in an unknown state."""
        return self._members[EntrySt.ufo]

    @property
    def expected(self):
        """The list of expected sections."""
        self._refresh()
        return self._members[EntrySt.expected]

    @property
    def available(self):
        """The list of sections that were successfully fetched."""
        self._refresh()
        return self._members[EntrySt.available]

    @property
    def failed(self):
        """The list of sections that ended with an error."""
        self._refresh()
        return self._members[EntrySt.failed]
