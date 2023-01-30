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

Starting from version 1.0.7, schedulers should be created using the footprints
package::

    import footprints as fp
    # In order to create a NewMaxThreadsScheduler scheduler:
    mt_sched = fp.proxy.scheduler(limit='threads', max_threads=2)

Compatibility classes are still provided (see :class:`LaxistScheduler`,
:class:`MaxThreadsScheduler`, :class:`MaxMemoryScheduler` and
:class:`SingleOpenFileScheduler`) but they should not be used anymore.

Dependencies
------------

:mod:`footprints` (MF package)
"""

import footprints
from footprints import FootprintBase
from bronx.fancies import loggers
from bronx.system import cpus, memory
from bronx.syntax.decorators import secure_getattr

import multiprocessing

logger = loggers.getLogger(__name__)

MAX_NUMBER_PROCESSES = 512


class BaseScheduler(FootprintBase):
    """Abstract base class for schedulers."""

    _abstract = True
    _collector = ('scheduler',)
    _footprint = dict(
        attr=dict(
            identity=dict(
                info="Scheduler identity.",
                optional=True,
                default='anonymous',
            ),
        )
    )

    def launchable(self, pending_instructions, workers, report):
        """
        Split *pending_instructions* into "launchable" and "not_yet_launchable"
        instructions according to the scheduler own rules.

        For that purpose and in a generic manner, the scheduler may need:

        - *pending_instructions*: todo
        - *workers*: being done
        - *report*: done.
        """
        raise NotImplementedError('launchable() method must be implemented in \
                                   inheritant classes. (BaseScheduler is abstract).')

    def _all_tickets(self):
        return {None}

    def _workers_hooks(self):
        """Return a list of callbacks to be triggered before workers task processing."""
        return list()

    def _assign_tickets(self, workers, launchable):
        """Assign available tickets in **launchable** instructions."""
        assigned_tickets = {w.scheduler_ticket for w in workers.values()}
        possible_tickets = sorted(self._all_tickets() - assigned_tickets)
        for instructions in launchable:
            possible_tickets.append(None)
            instructions.update(
                scheduler_ticket=possible_tickets.pop(0),
                scheduler_hooks=self._workers_hooks(),
            )
        return launchable


class NewLaxistScheduler(BaseScheduler):
    """No sorting is done !"""

    _footprint = dict(
        attr=dict(
            nosort=dict(
                alias=('laxist', 'unsorted'),
                values=(True,),
                type=bool,
            ),
        )
    )

    def launchable(self, pending_instructions, workers, report):
        """Very crude strategy: any pending instruction could be triggered."""
        launchable = self._assign_tickets(workers, pending_instructions)
        return launchable, list()


class NewLimitedScheduler(BaseScheduler):
    """
    A scheduler that dequeue the pending list as long as a maximum number
    of simultaneous tasks (*max_threads*) is not reached.
    """

    _abstract = True,
    _footprint = dict(
        attr=dict(
            limit=dict(
                values=['threads', 'memory', 'mem', 'threads+memory'],
                remap=dict(mem='memory'),
            ),
        )
    )


#: Abstract footprint attribute for binding aware schedulers
_binded_fpattr = footprints.Footprint(info='Abstract binded attribute',
                                      attr=dict(binded=dict(type=bool,
                                                            info="Binds the process to a single cpu.",
                                                            default=False,
                                                            optional=True)))


def binding_setup(worker):
    """Bind a *worker* to its *scheduler_ticket* compute core."""
    cpusinfo = cpus.LinuxCpusInfo()
    cpuslist = list(cpusinfo.socketpacked_cpulist())
    binded_cpu = cpuslist[worker.scheduler_ticket % cpusinfo.nvirtual_cores]
    cpus.set_affinity(binded_cpu)


def BindingAwareScheduler(cls):
    """
    A class decorator that wraps the original _workers_hooks method to add
    binding's setup method to the list Worker's hooks.

    NB: The class' footprint should include a 'binded' attribute.
    """
    # Wrap _workers_hooks
    original_hooks = getattr(cls, '_workers_hooks')

    def new_hooks(self):
        hookslist = original_hooks(self)
        if getattr(self, 'binded', False):
            hookslist.append(binding_setup)
        return hookslist

    cls._workers_hooks = new_hooks
    return cls


@BindingAwareScheduler
class NewMaxThreadsScheduler(NewLimitedScheduler):
    """
    A basic scheduler that dequeue the pending list as long as a maximum number
    of simultaneous tasks (*max_threads*) is not reached.
    """

    _footprint = [
        _binded_fpattr,
        dict(
            attr=dict(
                limit=dict(
                    values=['threads', 'processes'],
                    remap=dict(processes='threads'),
                ),
                max_threads=dict(
                    alias=('maxpc', 'maxthreads'),
                    remap={0: multiprocessing.cpu_count() / 2},
                    type=int,
                ),
            )
        )
    ]

    def _all_tickets(self):
        """The actual range of available tickets is limited by a maximum number of threads."""
        return set(range(0, self.max_threads))

    def launchable(self, pending_instructions, workers, report):
        """Limit strategy: only max_threads processes could run simultaneously."""
        available_threads = self.max_threads - len(workers)
        launchable = pending_instructions[0:max(available_threads, 0)]
        not_yet_launchable = pending_instructions[max(available_threads, 0):]
        launchable = self._assign_tickets(workers, launchable)
        return launchable, not_yet_launchable


@BindingAwareScheduler
class NewMaxMemoryScheduler(NewLimitedScheduler):
    """
    A basic scheduler that dequeue the pending list as long as a critical memory
    level (according to 'memory' element of workers instructions (in MB) and
    total system memory) is not reached.
    """

    _footprint = [
        _binded_fpattr,
        dict(
            attr=dict(
                limit=dict(
                    values=['memory', 'mem'],
                    remap=dict(mem='memory'),
                ),
                max_memory=dict(
                    info="Amount of usable memroy (in MiB)",
                    optional=True,
                    type=float,
                    access='rwx',
                ),
                memory_per_task=dict(
                    info=("If a worker do not provide any information on memory, " +
                          "request at least *memory_per_task* MiB of memory."),
                    optional=True,
                    default=2048.,
                    type=float,
                ),
                memory_max_percentage=dict(
                    info=("Max memory level as a fraction of the total" +
                          "system memory (used only if max_memroy is not provided)."),
                    optional=True,
                    default=0.75,
                    type=float,
                ),
            )
        )
    ]

    def __init__(self, *args, **kw):
        """Setup the maximum available memory."""
        super().__init__(*args, **kw)
        if self.max_memory is None:
            # memory tools are all but generic, they might fail !
            try:
                system_mem = memory.LinuxMemInfo().system_RAM('MiB')
            except OSError:
                raise OSError("Unable to determine the total system's memory size.")
            self.max_memory = self.memory_max_percentage * system_mem

    def _all_tickets(self):
        """The actual range of available tickets is limited by a maximum number of threads."""
        return set(range(0, MAX_NUMBER_PROCESSES))

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
        return launchable, not_yet_launchable


class LongerFirstScheduler(NewMaxMemoryScheduler):
    """
    A scheduler based on the NewMaxMemory Scheduler. It aims at launching as soon
    as possible the workers that are expected to have the longest run-time (whilst
    there is enough available memory).

    Workers needs to have 2 attributes:

        * expected_time representing the expected run time
        * memory representing the expected memory consumed

    This scheduler is typically used with Bateur workers, in vortex's
    src/common/algo/odbtools.py (for parallel BATOR run).
    """

    _footprint = dict(
        attr=dict(
            limit=dict(
                values=['threads+memory'],
            ),
            max_threads=dict(
                alias=('maxpc', 'maxthreads'),
                remap={0: multiprocessing.cpu_count() / 2},
                type=int,
            ),
        )
    )

    def _all_tickets(self):
        """The actual range of available tickets is limited by a maximum number of threads."""
        return set(range(0, self.max_threads))

    def launchable(self, pending_instructions, workers, report):
        """Limit strategy: only processes that fit in a given amount of memory could run."""
        available_threads = self.max_threads - len(workers)
        used_memory = sum([w.memory or self.memory_per_task for w in workers.values()])
        available_memory = self.max_memory - used_memory
        launchable = []
        not_yet_launchable = []
        # sort by decreasing time
        pending_instructions.sort(key=lambda tup: tup.get('expected_time', 0), reverse=True)
        for instructions in pending_instructions:
            actual_memory = instructions.get('memory', self.memory_per_task)
            if (actual_memory <= available_memory) and (available_threads > 0):
                launchable.append(instructions)
                available_memory -= actual_memory
                available_threads -= 1
            else:
                not_yet_launchable.append(instructions)

        launchable = self._assign_tickets(workers, launchable)
        return launchable, not_yet_launchable


class NewSingleOpenFileScheduler(NewMaxThreadsScheduler):
    """
    Ensure that files will not be open 2 times simultaneously by 2 workers.
    And with a maximum threads number.
    """

    _footprint = dict(
        attr=dict(
            singlefile=dict(
                values=(True,),
                type=bool,
            ),
        )
    )

    def launchable(self, pending_instructions, workers, report):
        """Limit strategy: deal with what looks like a file locking."""
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
        (launchable, nyl) = super().launchable(launchable, workers, report)
        not_yet_launchable.extend(nyl)
        launchable = self._assign_tickets(workers, launchable)
        return launchable, not_yet_launchable


# ------------------------------------------------------------------------------
# The following classes are kept for backward compatibility. From now and on, one
# should abstain to use them.


class _AbstractOldSchedulerProxy:
    """the abstract class of deprecated scheduler objects."""

    _TARGET_CLASS = None

    def __init__(self, *kargs, **kwargs):
        if self._TARGET_CLASS is None:
            raise RuntimeError('_TARGET_CLASS needs to be defined')
        logger.warning('The %s class is deprecated. ' +
                       'Instead, use the footprint mechanism to create schedulers.',
                       self.__class__.__name__)
        self.__target_scheduler = self._TARGET_CLASS(*kargs, **kwargs)
        super().__init__()

    @secure_getattr
    def __getattr__(self, name):
        return getattr(self.__target_scheduler, name)


class LaxistScheduler(_AbstractOldSchedulerProxy):
    """Deprecated class: should not be used from now and on."""

    _TARGET_CLASS = NewLaxistScheduler

    def __init__(self):
        super().__init__(nosort=True)


class MaxThreadsScheduler(_AbstractOldSchedulerProxy):
    """Deprecated class: should not be used from now and on."""

    _TARGET_CLASS = NewMaxThreadsScheduler

    def __init__(self, max_threads=0):
        super().__init__(limit='threads', max_threads=max_threads)


class MaxMemoryScheduler(_AbstractOldSchedulerProxy):
    """Deprecated class: should not be used from now and on."""

    _TARGET_CLASS = NewMaxMemoryScheduler

    def __init__(self, max_memory_percentage=0.75, total_system_memory=None):
        """
        :param float max_memory_percentage: Max memory level as a fraction of the total system memory
        :param float total_system_memory: Memory available on this system (in MiB)
        """
        if total_system_memory is not None:
            max_memory = total_system_memory * max_memory_percentage
        else:
            max_memory = None
        super().__init__(limit='memory',
                         max_memory=max_memory,
                         memory_max_percentage=max_memory_percentage)


class SingleOpenFileScheduler(_AbstractOldSchedulerProxy):
    """Deprecated class: should not be used from now and on."""

    _TARGET_CLASS = NewSingleOpenFileScheduler

    def __init__(self, max_threads=0):
        super().__init__(limit='threads', max_threads=max_threads, singlefile=True)
