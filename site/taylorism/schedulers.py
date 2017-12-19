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

Dependencies
------------

``footprints`` (MF package)
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from footprints import FootprintBase
from bronx.system import cpus

import os
import multiprocessing


class BaseScheduler(FootprintBase):
    """Abstract base class for schedulers."""

    _abstract = True
    _collector = ('scheduler',)
    _footprint = dict(
        attr = dict(
            identity = dict(
                info     = "Scheduler identity.",
                optional = True,
                default  = 'anonymous',
            ),
        )
    )

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

    def _all_tickets(self):
        return set([None])

    def _workers_hooks(self):
        """Return a list of callbacks to be triggered before workers task processing."""
        return list()

    def _assign_tickets(self, workers, launchable):
        """Assign available tickets in **launchable** instructions."""
        assigned_tickets = set([w.scheduler_ticket for w in workers.values()])
        possible_tickets = sorted(self._all_tickets() - assigned_tickets)
        for instructions in launchable:
            possible_tickets.append(None)
            instructions.update(
                scheduler_ticket = possible_tickets.pop(0),
                scheduler_hooks  = self._workers_hooks(),
            )
        return launchable


class LaxistScheduler(BaseScheduler):
    """No sorting is done !"""

    _footprint = dict(
        attr = dict(
            nosort = dict(
                alias  = ('laxist', 'unsorted'),
                values = (True,),
                type   = bool,
            ),
        )
    )

    def launchable(self, pending_instructions, workers, report):
        """Very crude strategy: any pending instruction could be triggered."""
        launchable = self._assign_tickets(workers, pending_instructions)
        return (launchable, list())


class LimitedScheduler(BaseScheduler):
    """
    A scheduler that dequeue the pending list as long as a maximum number
    of simultaneous tasks (*max_threads*) is not reached.
    """

    _abstract = True,
    _footprint = dict(
        attr = dict(
            limit = dict(
                values = ['threads', 'memory', 'mem'],
                remap  = dict(mem = 'memory'),
            ),
        )
    )


class MaxThreadsScheduler(LimitedScheduler):
    """
    A basic scheduler that dequeue the pending list as long as a maximum number
    of simultaneous tasks (*max_threads*) is not reached.
    """

    _footprint = dict(
        attr = dict(
            limit = dict(
                values = ['threads', 'processes'],
                remap  = dict(processes = 'threads'),
            ),
            max_threads = dict(
                alias  = ('maxpc', 'maxthreads'),
                remap  = {0: multiprocessing.cpu_count()/2},
                type   = int,
            ),
        )
    )

    def _all_tickets(self):
        """The actual range of available tickets is limited by a maximum number of threads."""
        return set(range(0, self.max_threads))

    def launchable(self, pending_instructions, workers, report):
        """Limit strategy: only max_threads processes could run simultaneously."""
        available_threads = self.max_threads - len(workers)
        launchable = pending_instructions[0:max(available_threads, 0)]
        not_yet_launchable = pending_instructions[max(available_threads, 0):]
        launchable = self._assign_tickets(workers, launchable)
        return (launchable, not_yet_launchable)


class BindedScheduler(object):
    """
    Extension for binding processes to logical cpus.
    """

    def set_affinity(self, worker):
        cpusinfo = cpus.LinuxCpusInfo()
        cpuslist = list(cpusinfo.socketpacked_cpulist())
        binded_cpu = cpuslist[worker.scheduler_ticket % cpusinfo.nvirtual_cores]
        cpus.set_affinity(binded_cpu, str(os.getpid()))

    def _workers_hooks(self):
        return [self.set_affinity]


class BindedMaxThreadsScheduler(BindedScheduler, MaxThreadsScheduler):
    """
    A max threads scheduler that binds workers to specific cpus.
    """

    _footprint = dict(
        attr = dict(
            binded = dict(
                values = (True,),
                type   = bool,
            ),
        )
    )


class MaxMemoryScheduler(LimitedScheduler):
    """
    A basic scheduler that dequeue the pending list as long as a critical memory
    level (according to 'memory' element of workers instructions (in MB) and
    total system memory) is not reached.
    """

    _footprint = dict(
        attr = dict(
            limit = dict(
                values = ['memory', 'mem'],
                remap  = dict(mem = 'memory'),
            ),
            max_memory = dict(
                optional = True,
                default  = None,
                type     = float,
                access   = 'rwx',
            ),
            memory_per_task = dict(
                optional = True,
                default  = 2.,
                type     = float,
            ),
            memory_max_percentage = dict(
                optional = True,
                default  = 0.75,
                type     = float,
            ),
            memory_total_size = dict(
                optional = True,
                default  = os.sysconf(str('SC_PAGE_SIZE')) * os.sysconf(str('SC_PHYS_PAGES')) / (1024 ** 3.),
                type     = float,
            ),
        )
    )

    def __init__(self, *args, **kw):
        """
        *memory_max_percentage*: max memory level as a percentage of the total system memory.
        *memory_total_size*: total system memory in GB.
        """
        super(MaxMemoryScheduler, self).__init__(*args, **kw)
        if self.max_memory is None:
            self.max_memory = self.memory_max_percentage * self.memory_total_size

    def launchable(self, pending_instructions, workers, report):
        """Limit strategy: only processes that fit in a given amount of memory could run."""
        used_memory = sum([w.memory or self.memory_per_task for w in workers.values()])
        launchable = list()
        not_yet_launchable = list()
        for instructions in pending_instructions:
            actual_memory = instructions.get('memory', self.memory_per_task)
            if used_memory + actual_memory < self.max_memory:
                launchable.append(instructions)
                used_memory += actual_memory
            else:
                not_yet_launchable.append(instructions)
        launchable = self._assign_tickets(workers, launchable)
        return (launchable, not_yet_launchable)


class BindedMaxMemoryScheduler(BindedScheduler, MaxMemoryScheduler):
    """
    A max memory scheduler that binds workers to specific cpus.
    """

    _footprint = dict(
        attr = dict(
            binded = dict(
                values = (True,),
                type   = bool,
            ),
        )
    )

    def _all_tickets(self):
        return set(range(cpus.LinuxCpusInfo().nphysical_cores))


class SingleOpenFileScheduler(MaxThreadsScheduler):
    """
    Ensure that files will not be open 2 times simultaneously by 2 workers.
    And with a maximum threads number.
    """

    _footprint = dict(
        attr = dict(
            singlefile = dict(
                values = (True,),
                type   = bool,
            ),
        )
    )

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
        launchable = self._assign_tickets(workers, launchable)
        return (launchable, not_yet_launchable)
