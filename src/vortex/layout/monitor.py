#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines generic classes that are used to check the state of a list of
sections
"""

import time
from collections import defaultdict, namedtuple

from footprints import loggers, observers
logger = loggers.getLogger(__name__)


#: No automatic export.
__all__ = []


#: Class for possible states of a :class:`InputMonitorEntry` object
EntryStateTuple = namedtuple('EntryStateTuple',
                             ['ufo', 'expected', 'available', 'failed'],
                             verbose=False)

#: Predefined :class:`InputMonitorEntry` state values
EntrySt = EntryStateTuple(ufo='ufo', expected='expected', available='available',
                          failed='failed')

#: Class for possible states of a :class:`_Gang` object
GangStateTuple = namedtuple('GangStateTuple',
                            ['ufo', 'collectable', 'pcollectable', 'failed'],
                            verbose=False)

#: Predefined :class:`_Gang` state values
GangSt = GangStateTuple(ufo='undecided', collectable='collectable',
                        pcollectable='collectable_partial', failed='failed')


class _StateFull(object):
    """A class with a state."""

    _mystates = EntrySt  # The name of possible states

    def __init__(self):
        """Initialise the state attribute and setup the observer."""
        self._state = self._mystates.ufo
        self._obsboard = observers.SecludedObserverBoard()
        self._obsboard.notify_new(self, dict(state=self._state))

    def __del__(self):
        self._obsboard.notify_del(self, dict(state=self._state))
        del self._obsboard

    @property
    def observerboard(self):
        """The entry's observer board."""
        return self._obsboard

    def _get_state(self):
        return self._state

    def _set_state(self, newstate):
        if newstate != self._state:
            previous = self._state
            self._state = newstate
            self._obsboard.notify_upd(self, dict(state=self._state,
                                                 previous_state=previous))

    state = property(_get_state, _set_state, doc="The entry's state.")


class _StateFullMembersList(object):
    """A class with members."""

    _mstates = EntrySt  # The name of possible member's states
    _mcontainer = list  # The container class for the members

    def __init__(self):
        """Initialise the members list."""
        self._members = dict()
        for st in self._mstates:
            self._members[st] = self._mcontainer()

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
            for e in self._members[st]:
                yield e

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


class BasicInputMonitor(_StateFullMembersList):

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

        :param vortex.layout.dataflow.Sequence sequence: The sequence object that
            is used as a source of inputs
        :param str role: The role of the sections that will be watched
        :param str kind: The kind of the sections that will be watched (used only
            if role is not specified)
        :param int caching_freq: We will update the sections statuses every N
            seconds
        :param int crawling_threshold: Maximum number of section statuses  to
            update at once
        """
        _StateFullMembersList.__init__(self)

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


class _Gang(observers.Observer, _StateFull, _StateFullMembersList):
    """A Gang is a collection of :class:`InputMonitorEntry` objects or a collection of :class:`_Gang` objects.

    The members of the Gang are classified depending on their state. The state
    of each of the members may change, that's why the Gang registers as an
    observer to its members.

    Since a Gang may be a collection of Gangs, a Gang is also an observee.
    """

    _mystates = GangSt
    _mcontainer = set

    def __init__(self):
        """

        :parameters: None
        """
        _StateFull.__init__(self)
        _StateFullMembersList.__init__(self)
        self._nmembers = 0
        self.info = dict()

    @property
    def nickname(self):
        """A fancy representation of the info dict."""
        if not self.info:
            return 'Anonymous'
        else:
            return ", ".join(['{:s}={!s}'.format(k, v)
                              for k, v in self.info.iteritems()])

    def add_member(self, *members):
        """Introduce one or several members to the Gang."""
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
        observers.Observer.updobsitem(self, item, info)
        # Move the item around
        self._members[info['previous_state']].remove(item)
        self._members[info['state']].add(item)
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

    # We need to refresh the state just before accessing it (since the state may
    # be time dependant)
    def _get_state(self):
        self._refresh_state()
        return super(_Gang, self)._get_state()

    state = property(_get_state, _StateFull._set_state, doc="The Gang's state.")


class BasicGang(_Gang):
    """A Gang of :class:`InputMonitorEntry` objects.

    Such a Gang may have 4 states:

        * undecided: Some of the members are still expected (and the
          *waitlimit* time is not exhausted)
        * collectable: All the members are available
        * collectable_partial: At least *minsize* members are available, but some
          of the members are late (because the *waitlimit* time is exceeded) or
          have failed.
        * failed: There are to much failed members (given *minsize*)
    """

    _mstates = EntrySt

    def __init__(self, minsize=0, waitlimit=0):
        """

        :param int minsize: The minimum size for this Gang to be collectable
                            (0 for all present)
        :param int waitlimit: If > 0, wait no more that N sec after the first change
                              of state
        """
        self.minsize = minsize
        self.waitlimit = waitlimit
        self._firstseen = None
        super(BasicGang, self).__init__()

    def updobsitem(self, item, info):
        super(BasicGang, self).updobsitem(item, info)
        if info['previous_state'] == self._mstates.expected:
            self._firstseen = time.time()

    @property
    def _eff_minsize(self):
        """If minsize==0, the effective minsize will be equal to the Gang's len."""
        return self.minsize if self.minsize > 0 else len(self)

    @property
    def _ufo_members(self):
        """The number of ufo members (from a Gang point of view)."""
        return len(self._members[self._mstates.ufo]) + len(self._members[self._mstates.expected])

    def _is_collectable(self):
        return len(self._members[self._mstates.available]) == len(self)

    def _is_pcollectable(self):
        return (len(self._members[self._mstates.available]) >= self._eff_minsize and
                (self._ufo_members == 0 or
                 (self.waitlimit > 0 and self._firstseen is not None and
                  time.time() - self._firstseen > self.waitlimit)
                 )
                )

    def _is_undecided(self):
        return len(self._members[self._mstates.available]) + self._ufo_members >= self._eff_minsize


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

    def has_collectable(self):
        """Is there at least one collectable member ?"""
        return len(self._members[self._mstates.collectable])

    def has_pcollectable(self):
        """Is there at least one collectable or collectable_partial member ?"""
        return (len(self._members[self._mstates.pcollectable]) +
                len(self._members[self._mstates.collectable]))

    def pop_collectable(self):
        """Retrieve a collectable member."""
        return self._members[self._mstates.collectable].pop()

    def pop_pcollectable(self):
        """Retrieve a collectable or a collectable_partial member."""
        if self.has_collectable():
            return self.pop_collectable()
        else:
            return self._members[self._mstates.pcollectable].pop()

    def _is_collectable(self):
        return len(self._members[self._mstates.collectable]) == len(self)

    def _is_pcollectable(self):
        return (len(self._members[self._mstates.collectable]) +
                len(self._members[self._mstates.pcollectable])) == len(self)

    def _is_undecided(self):
        return len(self._members[self._mstates.failed]) == 0

    def _refresh_state(self):
        for member in self.memberslist:
            member.state  # Update the member's state (they might be time dependent
        super(MetaGang, self)._refresh_state()


class AutoMetaGang(MetaGang):
    """
    A :class:`MetaGang` with a method that automatically populate the object
    given a :class:`BasicInputMonitor` object.
    """

    def autofill(self, bm, grouping_keys, allowmissing=0, waitlimit=0):
        """
        Crawl into the *bm* :class:`BasicInputMonitor`'s entries, create
        :class:`BasicGang` objects based on the resource's attribute listed in
        *grouping_keys* and finally adds these gangs to the current object.

        :param vortex.layout.monitor.BasicInputMonitor bm: The BasicInputMonitor
                                                           that will be explored
        :param list grouping_keys: The attributes that are used to discriminate the gangs
        :param int allowmissing: The number of missing members allowed for a gang
            (It will be used to initialise the member gangs *minsize* attribute)
        :param int waitlimit: The *waitlimit* attribute of the members Gangs
        """
        # Initialise the gangs
        mdict = defaultdict(list)
        for entry in bm.memberslist:
            entryid = tuple([getattr(entry.section.rh.resource, key) for key in grouping_keys])
            mdict[entryid].append(entry)
        # Finalise the Gangs setup and use them...
        for entryid, members in mdict.iteritems():
            gang = BasicGang(waitlimit=waitlimit,
                             minsize=len(members) - allowmissing)
            gang.add_member(* members)
            gang.info = {k: v for k, v in zip(grouping_keys, entryid)}
            self.add_member(gang)
