#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Contains classes for Schedulers.

Among a set of instructions to be passed to a Worker, and according to its own
criteria, the Scheduler determine at the current moment the ones that can be
launched right now simultaneously, and those that must be delayed.

A scheduler hence basically has one method:
launchable(pending_instructions, workers, report).

Its parameters (constant among execution) can be attributed in its constructor.
Other quantities, variables among execution, must be available within
*workers* (work being done) and *report* (work done).

A set of basic schedulers is given.
"""

from __future__ import print_function, absolute_import, unicode_literals, division


class BaseScheduler(object):
    """Abstract class."""
    def launchable(self, pending_instructions, workers, report):
        """
        Split *pending_instructions* into "launchable" and "not_yet_launchable"
        instructions according to the scheduler own rules.

        For that purpose and in a generic manner, the scheduler may need:\n
        - *pending_instructions*: todo
        - *workers*: being done
        - *report*: done.
        """
        raise NotImplementedError('launchable() method must be implemented in \
                                   inheritant classes. (BaseScheduler is abstract).')


class LaxistScheduler(BaseScheduler):
    """No sorting is done !"""
    def launchable(self, pending_instructions, workers, report):
        return pending_instructions


class MaxThreadsScheduler(BaseScheduler):
    """
    A basic scheduler that dequeue the pending list as long as a maximum number
    of simultaneous tasks (*max_threads*) is not reached.
    """
    import multiprocessing as mpc

    def __init__(self, max_threads=mpc.cpu_count() / 2):
        """*max_threads* to be launched simultaneously."""
        self.max_threads = max_threads

    def launchable(self, pending_instructions, workers, report):
        available_threads = self.max_threads - len(workers)
        launchable = pending_instructions[0:max(available_threads, 0)]
        not_yet_launchable = pending_instructions[max(available_threads, 0):]

        return (launchable, not_yet_launchable)


class MaxMemoryScheduler(BaseScheduler):
    """
    A basic scheduler that dequeue the pending list as long as a critical memory
    level (according to 'memory' element of workers instructions (in MB) and
    total system memory) is not reached.
    """

    def __init__(self, max_memory_percentage=0.75, total_system_memory='compute'):
        """
        *max_memory_percentage*: max memory level as a percentage of the total
        system memory.
        *total_system_memory*: total system memory in MB;
        if 'compute', computed (Unix only).
        """
        import os

        if total_system_memory == 'compute':
            total_system_memory = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
            total_system_memory = float(total_system_memory) / (1024 ** 2.)
        self.max_memory = max_memory_percentage * total_system_memory

    def launchable(self, pending_instructions, workers, report):
        assert all([hasattr(w, 'memory') for w in workers.values()])
        used_memory = sum([w.memory for w in workers.values()])
        launchable = []
        not_yet_launchable = []
        for instructions in pending_instructions:
            if used_memory + instructions['memory'] < self.max_memory:
                launchable.append(instructions)
                used_memory += instructions['memory']
            else:
                not_yet_launchable.append(instructions)

        return (launchable, not_yet_launchable)


class SingleOpenFileScheduler(MaxThreadsScheduler):
    """
    Ensure that files will not be open 2 times simultaneously by 2 workers.
    And with a maximum threads number.
    """

    def launchable(self, pending_instructions, workers, report):
        launchable = []
        not_yet_launchable = []
        open_files = [w.fileA for w in workers.values()] + [w.fileB for w in workers.values()]
        # check files are not already open by other worker
        for pi in pending_instructions:
            if pi['fileA'] in open_files or pi['fileB'] in open_files:
                not_yet_launchable.append(pi)
            else:
                launchable.append(pi)
        # and finally sort with regards to MaxThreads
        (launchable, nyl) = super(SingleOpenFileScheduler, self).launchable(launchable, workers, report)
        not_yet_launchable.extend(nyl)

        return (launchable, not_yet_launchable)
