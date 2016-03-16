#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module defines generic classes that are used to check the states a list of
sections
"""

import time
from collections import defaultdict

from footprints import loggers
logger = loggers.getLogger(__name__)


#: No automatic export.
__all__ = []


class _InputMonitorEntry(object):

    def __init__(self, section):
        self._nchecks = 0
        self._section = section

    @property
    def nchecks(self):
        return self._nchecks

    def check_done(self):
        self._nchecks += 1

    @property
    def section(self):
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
        toclassify = [_InputMonitorEntry(x)
                      for x in self._seq.filtered_inputs(role=self._role, kind=self._kind)]
        # Initialise other lists
        self._ufo = list()
        self._expected = list()
        self._available = list()
        self._failed = list()

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
        self._map_stages = dict(expected=self._expected,
                                get=self._available)

        while toclassify:
            self._classify_ufo(toclassify.pop(0), onfails=self._ufo)

        # Give some time to the caller to process the first available files (if any)
        self._last_refresh = time.time() if len(self._available) else 0

    def _classify_ufo(self, e, onfails):
        self._map_stages.get(e.section.stage, onfails).append(e)

    def _check_entry_index(self, index):
        found = 0
        e = self._expected[index]
        e.check_done()
        if e.section.rh.is_grabable():
            found = 1
            e = self._expected.pop(index)
            if e.section.rh.is_grabable(check_exists=True):
                logger.info("The local resource %s becomes available",
                            e.section.rh.container.localpath())
                e.section.get(incache=True)
                self._available.append(e)
            else:
                logger.warning("The local resource %s has failed",
                               e.section.rh.container.localpath())
                self._failed.append(e)
        return found

    def _refresh(self):
        curtime = time.time()
        if (len(self._ufo) and
                len(self._expected) <= self._crawling_threshold and
                not len(self._available)):
            # If UFO are still there and not much resources are expected,
            # decrease the caching time
            eff_caching_freq = max(3, self._caching_freq / 5)
        elif len(self._available):
            # All available files weren't processed: give some more time to the
            # caller
            eff_caching_freq = self._caching_freq * 3
        else:
            eff_caching_freq = self._caching_freq
        if curtime > self._last_refresh + eff_caching_freq:
            self._last_refresh = curtime
            found = 0
            # Crawl into the ufo list
            # Always process the first self._crawling_threshold elements
            for i_e in range(min(self._crawling_threshold, len(self._ufo)) - 1, -1, -1):
                logger.info("First get on local file: %s",
                            self._ufo[i_e].section.rh.container.localpath())
                e = self._ufo.pop(i_e)
                e.check_done()
                e.section.get(incache=True, fatal=False)  # Do not crash at this stage
                self._classify_ufo(e, onfails=self._failed)
            # Crawl into the expected list
            # Always process the first self._crawling_threshold elements
            for i_e in range(min(self._crawling_threshold, len(self._expected)) - 1, -1, -1):
                logger.debug("Checking local file: %s",
                             self._expected[i_e].section.rh.container.localpath())
                found += self._check_entry_index(i_e)
            # Do we attempt the kangaroo check ?
            if (len(self._expected) > self._crawling_threshold and
                    found < self._crawling_threshold / 4):
                l_len = len(self._expected) - self._crawling_threshold
                self._kangaroo_idx += self._crawling_threshold + 1
                if self._kangaroo_idx >= l_len:
                    l_endid = l_len - 1
                    self._kangaroo_idx = 0
                else:
                    l_endid = self._kangaroo_idx - 1
                for i_e in range(self._crawling_threshold + l_endid,
                                 max(l_endid - 1, self._crawling_threshold - 1), -1):
                    logger.debug("Checking local file (kangaroo): %s",
                                 self._expected[i_e].section.rh.container.localpath())
                    found += self._check_entry_index(i_e)

    @property
    def all_done(self):
        """Is there any expected sections left ?"""
        self._refresh()
        return len(self._expected) == 0 and len(self._ufo) == 0

    @property
    def ufo(self):
        """The list of resources in an unknown state."""
        return self._ufo

    @property
    def expected(self):
        """The list of expected sections."""
        self._refresh()
        return self._expected

    @property
    def available(self):
        """The list of sections that were successfully fetched."""
        self._refresh()
        return self._available

    @property
    def failed(self):
        """The list of sections that ended with an error."""
        self._refresh()
        return self._failed
