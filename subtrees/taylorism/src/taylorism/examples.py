"""
Basic examples of how to use the module.

A more advanced example of use can be found in ``epygram``'s epy_conv.py tool.
"""

import time

from footprints import proxy as fpx

from taylorism import Worker, run_as_server
from .util import SharedNumpyArray


class Sleeper(Worker):
    """
    Sample worker for tutorial or debugging purpose, that sleeps a given time.

    The over-loading of __init__() is not mandatory, but a possibility.
    """

    _footprint = dict(
        info="Sleeps.",
        attr=dict(
            sleeping_time=dict(
                info="Sleeping time in s.",
                values=[0.001, 0.01, 0.1] + list(range(10)) + list(range(10, 65, 5)),
                type=float,
            ),
            wakeup_sentence=dict(
                info="What to say after sleep.",
                optional=True,
                access='rwx',
                default='Hello !',
            ),
        )
    )

    def _task(self):
        """
        Actual task of the Sleeper is implemented therein.
        Return the report to be sent back to the Boss.
        """
        time.sleep(self.sleeping_time)
        return ' '.join([self.wakeup_sentence, 'Woke up after',
                         str(self.sleeping_time), "s sleep on cpu", str(self.binding())])


class Logarithmer(Worker):
    """
    Computes the logarithm of an array.

    OK, this would be much more efficient with numpy.log(array), but it is just
    an example of using shared numpy arrays among workers.
    """
    _footprint = dict(
        attr=dict(
            row=dict(
                info="Index of the row of the array on which the Worker is supposed to work.",
                type=int),
            array=dict(
                info="The shared-memory array on which to work on.",
                type=SharedNumpyArray,
                access='rwx')
        )
    )

    def _task(self):
        import numpy
        for j in range(self.array.shape[1]):
            self.array[self.row, j] = numpy.log(self.array[self.row, j])


class Summer(Worker):
    """
    Computes a Sum, each Worker adding its value to a SharedNumpyArray.

    This needs and illustrates process-safetiness.
    """
    _footprint = dict(
        attr=dict(
            value=dict(
                info="Value to be added by the worker.",
                type=int),
            shared_sum=dict(
                info="The shared-memory array on which to sum.",
                type=SharedNumpyArray,
                access='rwx'),
            use_lock=dict(
                info="Whether to use the lock (thread-safe) or not (may lead to a wrong result !).",
                type=bool)
        )
    )

    def _task(self):
        if self.use_lock:
            # acquire the lock, to be sure no other process is accessing the data meanwhile
            self.shared_sum.acquire()
        self.shared_sum[0] += self.value
        if self.use_lock:
            self.shared_sum.release()  # release the lock


class MatrixProducter(Worker):
    """
    Computes a Matrix Product C = A x B by hand, but parallel by blocks,
    using 3 SharedNumpyArray, each Worker being responsible for a [i1:i2, j1:j2]
    block of the resulting C matrix.

    Again, numpy matrix products may probably be more efficient...
    """
    _footprint = dict(
        attr=dict(
            A=dict(
                info="The A shared-memory array matrix.",
                type=SharedNumpyArray,
                access='rwx'),
            B=dict(
                info="The B shared-memory array matrix.",
                type=SharedNumpyArray,
                access='rwx'),
            C=dict(
                info="The C shared-memory array matrix.",
                type=SharedNumpyArray,
                access='rwx'),
            i1=dict(
                info="The first index i of the the Worker is responsible for.",
                type=int),
            i2=dict(
                info="The last index i of the the Worker is responsible for.",
                type=int),
            j1=dict(
                info="The first index j of the the Worker is responsible for.",
                type=int),
            j2=dict(
                info="The first index j of the the Worker is responsible for.",
                type=int),
        )
    )

    def _task(self):
        for i in range(self.i1, self.i2 + 1):
            for j in range(self.j1, self.j2 + 1):
                self.C[i, j] = sum([self.A[i, k] * self.B[k, j] for k in range(self.A.shape[1])])


def sleepers_generic_program(verbose=True, scheduler=None):
    """Generic example: how to run and control the Boss."""
    boss = run_as_server(
        common_instructions=dict(wakeup_sentence='Hello Dolly !'),
        individual_instructions=dict(sleeping_time=[4, 9, 2, 1]),
        scheduler=scheduler,
        verbose=verbose,
    )
    time.sleep(5)
    print('Intermediate report:', boss.get_report())
    boss.set_instructions(dict(), individual_instructions=dict(sleeping_time=[3, ]))
    boss.wait_till_finished()
    report = boss.get_report()
    for r in report['workers_report']:
        print(r)


def sleepers_example_laxist(verbose=True):
    """Example: assuming no selection of strategy for scheduling."""
    sleepers_generic_program(
        verbose=verbose,
        scheduler=fpx.scheduler(nosort=True),
    )


def sleepers_example_threads(verbose=True):
    """Example: scheduling is driven by number of threads."""
    sleepers_generic_program(
        verbose=verbose,
        scheduler=fpx.scheduler(limit='threads', max_threads=3),
    )


def sleepers_example_bindedthreads(verbose=True):
    """Example: scheduling is driven by number of threads and processes are binded."""
    sleepers_generic_program(
        verbose=verbose,
        scheduler=fpx.scheduler(limit='threads', max_threads=3, binded=True),
    )


def sleepers_example_memory(verbose=True):
    """Example: scheduling is driven by memory consumption."""
    sleepers_generic_program(
        verbose=verbose,
        scheduler=fpx.scheduler(limit='memory', memory_per_task=1.8),
    )


def sleepers_example_bindedmemory(verbose=True):
    """Example: scheduling is driven by memory consumption and processes are binded."""
    sleepers_generic_program(
        verbose=verbose,
        scheduler=fpx.scheduler(limit='memory', binded=True),
    )


def logarithmer_example(verbose=True):
    """Example: how to use a numpy array, shared among workers."""
    import numpy
    # sample initialization of the SharedNumpyArray
    nrows = 2
    ncols = 3
    a = SharedNumpyArray(numpy.ones((nrows, ncols)))
    for i in range(a.shape[0]):
        for j in range(a.shape[1]):
            a[i, j] = i + j
    print(a[...])
    # run workers, each one dedicated to a row
    boss = run_as_server(common_instructions={},
                         individual_instructions=dict(row=list(range(nrows))),
                         scheduler=fpx.scheduler(limit='threads', max_threads=nrows),
                         verbose=verbose,
                         sharedmemory_common_instructions=dict(array=a))
    boss.wait_till_finished()
    print(a[...])


def summer_example(verbose=True, use_lock=True):
    """Example: how to use a process-safe numpy array, shared among workers."""
    import numpy
    # sample initialization of the SharedNumpyArray
    n = 10
    s = SharedNumpyArray(numpy.zeros((1,), dtype=int))
    # run workers, each one dedicated to a value
    boss = run_as_server(common_instructions=dict(use_lock=use_lock),
                         individual_instructions=dict(value=list(range(n))),
                         # maximize the number of simultaneous threads to test the importance of the lock
                         scheduler=fpx.scheduler(limit='threads', max_threads=n),
                         verbose=verbose,
                         sharedmemory_common_instructions=dict(shared_sum=s))
    boss.wait_till_finished()
    print(str(s[0]) + '==' + str(sum(range(n))))


def matrixproduct_example(A_shape=(6, 7), B_shape=(7, 8),
                          iblocks=2, jblocks=4,
                          verbose=True):
    """
    Example: how to use several numpy array shared among workers.

    :param A_shape: size of the A matrix
    :param B_shape: size of the B matrix
    :param iblocks: number of blocks in direction i of result matrix;
                    must divide A_shape[0]
    :param jblocks: number of blocks in direction j of result matrix;
                    must divide B_shape[1]
    """
    import numpy
    assert A_shape[1] == B_shape[0]
    assert A_shape[0] % iblocks == 0 and B_shape[1] % jblocks == 0
    iblocksize = A_shape[0] // iblocks
    jblocksize = B_shape[1] // jblocks
    # sample initialization of the SharedNumpyArray
    A = SharedNumpyArray(numpy.random.random(A_shape))
    B = SharedNumpyArray(numpy.random.random(B_shape))
    C = SharedNumpyArray(numpy.zeros((A.shape[0], B.shape[1])))
    # build blocks indices, other cuts could be possible of course...
    i1 = list(range(0, C.shape[0], iblocksize))
    i2 = list(i1[1:] + [C.shape[0] - 1])
    j1 = list(range(0, C.shape[1], jblocksize))
    j2 = list(j1[1:] + [C.shape[1] - 1])
    t0 = time.time()
    # constitute each workers instructions
    indexes = dict(i1=[], i2=[], j1=[], j2=[])
    for i in range(len(i1)):
        for j in range(len(j1)):
            indexes['i1'].append(i1[i])
            indexes['i2'].append(i2[i])
            indexes['j1'].append(j1[j])
            indexes['j2'].append(j2[j])
    # run workers, each one dedicated to a block
    boss = run_as_server(common_instructions=dict(),
                         individual_instructions=indexes,
                         scheduler=fpx.scheduler(limit='threads', max_threads=4),
                         verbose=verbose,
                         sharedmemory_common_instructions=dict(A=A, B=B, C=C))
    boss.wait_till_finished()
    print('Exec in:', time.time() - t0)
    print(C[:, :])
