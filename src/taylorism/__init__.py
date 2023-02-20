"""
Framework for parallelisation of tasks.
"""

import multiprocessing as mpc
import queue
import uuid
import sys
import traceback
import copy
import os
from pickle import PickleError

from footprints import FootprintBase, FPList, proxy as fpx
from bronx.fancies import loggers
from bronx.system import interrupt, cpus  # because subprocesses must be killable properly

from .schedulers import BaseScheduler
from .schedulers import MaxThreadsScheduler, binding_setup  # For compatibility

assert BaseScheduler
assert MaxThreadsScheduler

taylorism_log = loggers.getLogger(__name__)

# : timeout when polling for a Queue/Pipe communication
communications_timeout = 0.01


# FUNCTIONS
###########

def run_as_server(common_instructions=dict(),
                  individual_instructions=dict(),
                  scheduler=None,
                  verbose=False,
                  maxlenreport=1024,
                  sharedmemory_common_instructions=dict()):
    """
    Build a Boss instance, make him hire workers,
    run the workers, and returns the Boss instance.

    Be aware that the Boss MUST be told when no more instructions will be
    appended, or the subprocess will continue to live alone (until
    destruction of the Boss instance).

    :param dict common_instructions: to be passed to the workers
    :param dict individual_instructions: to be passed to the workers
    :param scheduler: scheduler to rule scheduling of workers/threads
    :param bool verbose: is the Boss verbose or not.
    :param int maxlenreport: the maximum number of lines for the report (when
        running in verbose mode)
    :param dict sharedmemory_common_instructions: special "instructions", whose
        memory allocation is shared among workers and from main process.
        Warning: these objects must inherit in some way from
        multiprocessing.Array or sharedctypes. For n-dimensional arrays,
        it is advised to be instances of the here-defined :class:`SharedNumpyArray`.
    """
    if scheduler is None:
        scheduler = fpx.scheduler(limit='threads', max_threads=0)
    boss = Boss(verbose=verbose, scheduler=scheduler, maxlenreport=maxlenreport,
                sharedmemory_common_instructions=sharedmemory_common_instructions)
    boss.set_instructions(common_instructions, individual_instructions)
    boss.make_them_work()
    return boss


def batch_main(common_instructions=dict(),
               individual_instructions=dict(),
               scheduler=None,
               verbose=False,
               maxlenreport=1024,
               print_report=print,
               sharedmemory_common_instructions=dict()):
    """
    Run execution of the instructions as a batch process, waiting for all
    instructions are finished and finally printing report.

    Args and kwargs are those of run_as_server() function.
    """
    if scheduler is None:
        scheduler = fpx.scheduler(limit='threads', max_threads=0)
    boss = run_as_server(common_instructions,
                         individual_instructions,
                         scheduler=scheduler,
                         verbose=verbose,
                         maxlenreport=maxlenreport,
                         sharedmemory_common_instructions=sharedmemory_common_instructions)

    with interrupt.SignalInterruptHandler(emitlogs=False):
        try:
            boss.wait_till_finished()
            report = boss.get_report()
        except (Exception, KeyboardInterrupt, interrupt.SignalInterruptError):
            boss.stop_them_working()
            boss.wait_till_finished()
            raise
        else:
            for r in report['workers_report']:
                taskheader = 'WORKER NAME: ' + r['name']
                print('=' * len(taskheader))
                print(taskheader)
                print('-' * len(taskheader))
                print_report(r['report'])
            return report


# MAIN CLASSES
##############
class Worker(FootprintBase):
    """
    Template for workers.
    A Worker is an object supposed to do a task, according to instructions.
    The instructions has to be added to footprint attributes in actual classes.
    """

    _abstract = True
    _collector = ('worker',)
    _footprint = dict(
        attr=dict(
            name=dict(
                info='Name of the worker.',
                optional=True,
                default=None,
                access='rwx',
            ),
            memory=dict(
                info='Memory that should be used by the worker (in MiB).',
                optional=True,
                default=0.,
                type=float,
            ),
            expected_time=dict(
                info='How long the worker is expected to run (in s).',
                optional=True,
                default=0.,
                type=float,
            ),
            scheduler_ticket=dict(
                info='The slot number given by the scheduler (optional).',
                optional=True,
                default=None,
                type=int,
            ),
            scheduler_hooks=dict(
                info='List of callbacks before starting effective task work.',
                optional=True,
                default=FPList(),
                type=FPList,
            ),
        )
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.name is None:
            self.name = str(uuid.uuid4())
            taylorism_log.debug("Worker's name auto-assigned: %s", self.name)
        self._parent_pid = os.getpid()
        self._process = mpc.Process(target=self._work_and_communicate)
        self._terminating = False
        self._messenger = None

    def __del__(self):
        if (hasattr(self, '_process') and self._process.pid and
                # A subprocess should never call join on itself...
                self._parent_pid == os.getpid()):
            self._process.join(0.1)
            if self._process.is_alive():
                self._process.terminate()
                taylorism_log.debug('Worker process terminate issued (in __del__): pid=%s. name=%s',
                                    self._process.pid, self.name)

    def _get_messenger(self):
        """Return actual messenger for communication with the boss."""
        return self._messenger

    def _set_messenger(self, messenger):
        """Connect to some Queue."""
        assert callable(messenger.put)
        self._messenger = messenger

    messenger = property(_get_messenger, _set_messenger)

    def binding(self):
        """Return the actual physical binding of the current process to a cpu if available.

        The :class:`cpus.CpusToolUnavailableError` may be raised depending
        on the system.
        """
        cpuloc = cpus.get_affinity()
        if cpuloc == set(cpus.LinuxCpusInfo().raw_cpulist()):
            cpuloc = [None]
        return list(cpuloc)

    def work(self):
        """Send the Worker to his job."""
        if not self._terminating:
            self._process.start()
            taylorism_log.debug('Worker process started: pid=%s. name=%s',
                                self._process.pid, self.name)
        else:
            taylorism_log.debug('Worker process cannot be started while terminating. name=%s.',
                                self.name)

    def bye(self):
        """
        Block the Boss until the worker has finished his job.
        THIS METHOD SHOULD NEVER BE CALLED BY THE OBJECT HIMSELF !
        (WOULD CAUSE A DEADLOCK if called from inside the worker's subprocess)
        """
        if self._process.pid:
            self._process.join()
            taylorism_log.debug('Worker process joined: pid=%s. name=%s',
                                self._process.pid, self.name)
        else:
            taylorism_log.debug('Worker process not yet started. Nothing to do. name=%s.',
                                self.name)

    def stop_working(self):
        """Make the worker stop working.

        Since the worker process sets up a Signal handler, it should not stop
        abruptly when this method is called for the first time...
        """
        if not self._terminating:
            if self._process.pid:
                self._process.terminate()
                taylorism_log.debug('Worker process terminated (#1): pid=%s. name=%s',
                                    self._process.pid, self.name)
            else:
                taylorism_log.debug('Worker process not yet started. Nothing to do. name=%s.',
                                    self.name)
            self._terminating = True
        else:
            if self._process.pid:
                self._process.join(0.1)
                taylorism_log.debug('Worker process joined: pid=%s. name=%s',
                                    self._process.pid, self.name)
                if self._process.is_alive():
                    self._process.terminate()
                    taylorism_log.debug('Worker process terminated (#2): pid=%s. name=%s',
                                        self._process.pid, self.name)

    def _work_and_communicate(self):
        """
        Send the Worker to his task, making sure he communicates with
        its boss.

        From within this method down, everything is done in the subprocess
        world !
        """
        with interrupt.SignalInterruptHandler(emitlogs=False):
            fast_exit = False
            to_be_sent_back = dict(name=self.name, report=None)
            try:
                for callback in self.scheduler_hooks:
                    callback(self)
                self._work_and_communicate_prehook()
                to_be_sent_back.update(report=self._task())
            except Exception as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb = traceback.format_exception(exc_type,
                                                exc_value,
                                                exc_traceback)
                to_be_sent_back.update(report=e, traceback=tb)
            except (KeyboardInterrupt, interrupt.SignalInterruptError):
                fast_exit = True
            finally:
                if not fast_exit:
                    try:
                        self.messenger.put(to_be_sent_back)
                    except (ValueError, PickleError) as e:
                        # ValueError = to_be_sent_back too big.
                        # PickleError = to_be_sent_back unpickelable.
                        sys.stderr.write("The to_be_sent_back variable was:\n")
                        sys.stderr.write(str(to_be_sent_back))
                        to_be_sent_back.update(report=e, traceback='Traceback missing')
                        self.messenger.put(to_be_sent_back)
                self.messenger.close()

    def _work_and_communicate_prehook(self):
        """
        Some stuff executed before the "real" work_end_communicate takes place.
        """
        pass

    def _task(self, **kwargs):
        """
        Actual task of the Worker to be implemented therein.
        Return the report to be sent back to the Boss.
        """
        raise RuntimeError("this method must be implemented in Worker's inheritant class !")


class BindedWorker(Worker):
    """Workers binded to a cpu core (Linux only).

    This class is deprecated. Instead, inherit from :class:`Worker` and create
    a scheduler with binded=True.
    """

    _abstract = True

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        taylorism_log.warning('The %s class is deprecated. Please use "Worker" instead.',
                              self.__class__.__name__)

    def _work_and_communicate_prehook(self):
        """Bind the process to a cpu"""
        if self.scheduler_ticket is not None:
            binding_setup(self)


class Boss:
    """
    Template for bosses.
    A Boss is an object supposed to order tasks to a series of workers.

    Optionally can be attributed to the Boss a *name* and a *verbose*-ity
    (to report in log, the workers reports).

    Also, a *scheduler* can be assigned, to rule the ordering of tasks to
    workers.
    Custom schedulers can be used, they only need to inherit from
    .schedulers.BaseScheduler and implemented launchable() method.
    """

    control_signals = {'HALT': 'Suspend ordering workers to work until RESUME.',
                       'RESUME': 'Resume loop on pending_instructions/workers.',
                       'SEND_REPORT': 'Send interim report (and continue normally).',
                       'END': 'Terminate all pending work, then Stop listening.\
                               No new instructions from control will be listened,\
                               except a STOP*.',
                       'STOP': 'Halt pending work, but let workers finish their\
                                current work, and then stop listening.',
                       'STOP_LISTENING': 'Stop listening, while workers continue\
                                          their current job.',
                       'STOP_RIGHTNOW': 'Stop workers immediately and stop\
                                         listening.'}

    def __init__(self, scheduler=None, name=None, verbose=False,
                 maxlenreport=1024, sharedmemory_common_instructions=dict()):
        if scheduler is None:
            scheduler = fpx.scheduler(limit='threads', max_threads=0)
        # Duck typing check...
        assert hasattr(scheduler, 'launchable')
        assert callable(scheduler.launchable)
        self.scheduler = scheduler
        self.name = name
        self.verbose = verbose
        self.maxlenreport = int(maxlenreport)
        self._sharedmemory_common_instructions = sharedmemory_common_instructions

        self.workers_messenger = mpc.Queue()
        (self.control_messenger_in,
         self.control_messenger_out) = mpc.Pipe()  # in = inside subprocess, out = main
        self.control_messenger_out.send(self.control_signals['HALT'])

        self._parent_pid = os.getpid()
        self._process = mpc.Process(target=self._listen_and_communicate)
        self._process.start()
        taylorism_log.debug('Boss process started: pid=%s. name=%s',
                            self._process.pid, str(self.name))

        self._finalreport = None

    def __del__(self):
        if (hasattr(self, '_process') and self._process.pid and
                # A subprocess should never call join on itself...
                self._parent_pid == os.getpid() and
                self._process.is_alive()):
            self._process.join(0.1)
            taylorism_log.debug('Boss process joined (in __del__): pid=%s. name=%s',
                                self._process.pid, str(self.name))
            if self._process.is_alive():
                self._process.terminate()
                taylorism_log.debug('Boss process terminated (in __del__): pid=%s. name=%s',
                                    self._process.pid, str(self.name))
        self.control_messenger_in.close()
        self.control_messenger_out.close()
        self.workers_messenger.close()

    def set_instructions(self,
                         common_instructions=dict(),
                         individual_instructions=dict(),
                         fatal=True):
        """
        Set instructions to be distributed to workers.

        :param dict common_instructions: are a series of arguments shared by
                                         each worker, to be passed to the Worker
                                         factory.
        :param dict individual_instructions: are a series of arguments proper to
                                             each worker, hence all individual
                                             instructions must have the same
                                             length
        :param bool fatal: if True, an error in parsing instructions will stop
                           the workers already running and the boss internal
                           subprocess
        """
        # parse instructions
        individual_instructions = copy.deepcopy(individual_instructions)
        instructions_sets = []
        if len(individual_instructions) > 0:
            # check their length is homogeneous
            _i0 = sorted(individual_instructions.keys())[0]
            indiv_instr_num = len(individual_instructions[_i0])  # length of first instruction
            if not all([len(instr) == indiv_instr_num
                        for instr in individual_instructions.values()]):
                if fatal:
                    self.stop_them_working()
                raise AssertionError("all *individual_instructions* must have the same length.")
            # gather common and individual
            for _ in range(indiv_instr_num):
                instructions = copy.copy(common_instructions)
                for k, v in individual_instructions.items():
                    instructions.update({k: v.pop(0)})
                instructions_sets.append(instructions)

        # send instructions to control
        if self._process.is_alive():
            try:
                self.control_messenger_out.send(instructions_sets)
            except (ValueError, PickleError):
                # ValueError = instructions_sets too big.
                # PickleError = instructions_sets unpickelable.
                sys.stderr.write("The instructions_sets variable was:\n")
                sys.stderr.write(str(instructions_sets))
                taylorism_log.error("Impossible to send data through the pipe")
                self.stop_them_working()
                raise
        else:
            self.get_report(interim=True)

    def make_them_work(self, terminate=False, stop_listening=False):
        """
        Order the workers to work.

        :param bool terminate: if True, no other instructions could be appended
                               later.
        :param bool stop_listening: if True, alive workers go on their jobs,
                                    but they are not listened to anymore;
                                    this is a bit tricky but might be useful ?
        """
        self.control_messenger_out.send(self.control_signals['RESUME'])
        if stop_listening:
            self.control_messenger_out.send(self.control_signals['STOP_LISTENING'])
        if terminate:
            self.end()

    def stop_them_working(self):
        """Stop the workers."""
        self.control_messenger_out.send(self.control_signals['STOP_RIGHTNOW'])

    def get_report(self, interim=True):
        """
        Get report of the work executed.

        If *interim*, ask for an interim report if no report is available,
        i.e. containing the work done by the time of calling.
        """
        return self._internal_get_report(interim=interim)

    def _internal_get_report(self, interim=True, final=False):
        """
        Get report of the work executed.

        :param bool interim: if True, ask for an interim report if no report is
                             available, i.e. containing the work done by the
                             time of calling.
        :param bool final: if True, the report is saved in an internal variable
                           and the saved report will be returned whenever
                           get_report is called.
        """
        received_a_report = self.control_messenger_out.poll

        def _getreport():
            if final or received_a_report():
                received = self._recv_report(splitmode=True)
                if final:
                    self._finalreport = received
                    self._process.join()
                    taylorism_log.debug('Boss process joined: pid=%s. name=%s',
                                        self._process.pid, str(self.name))
                if isinstance(received['workers_report'],
                              (Exception, KeyboardInterrupt, interrupt.SignalInterruptError)):
                    taylorism_log.error("Error was caught in subprocesses with traceback:")
                    sys.stderr.writelines(received['traceback'])
                    raise received['workers_report']
            else:
                received = None
            return received

        # first try to get report
        if self._finalreport is None:
            report = _getreport()
        else:
            report = self._finalreport

        if report is None and not final and interim:
            self.control_messenger_out.send(self.control_signals['SEND_REPORT'])
            while report is None:
                report = _getreport()
                if not self._process.is_alive():
                    break

        return report

    def end(self):
        """
        Ends the listening process once instructions are treated.
        MUST BE CALLED (or wait_till_finished) for each Boss to avoid zombies
        processes.
        """
        self.control_messenger_out.send(self.control_signals['END'])

    def wait_till_finished(self):
        """Block the calling tree until all instructions have been executed."""
        self.end()
        taylorism_log.debug('Boss process waiting for pending work: pid=%s. name=%s',
                            self._process.pid, str(self.name))
        self._internal_get_report(final=True)

# boss subprocess internal methods
##################################

    def _send_report(self, report, splitmode=True):
        """Report must have keys 'workers_report', 'status' and optionally others."""
        if not splitmode:
            self.control_messenger_in.send(report)
        else:
            rkeys = list(report.keys())
            rkeys.pop(rkeys.index('workers_report'))
            rkeys.pop(rkeys.index('status'))
            for k in rkeys:
                self.control_messenger_in.send((k, report[k]))
            if not isinstance(report['workers_report'],
                              (Exception, KeyboardInterrupt, interrupt.SignalInterruptError)):
                for wr in report['workers_report']:
                    self.control_messenger_in.send(wr)
            else:
                self.control_messenger_in.send(report['workers_report'])
            self.control_messenger_in.send(('status', report['status']))

    def _recv_report(self, splitmode=True):
        """Report must have keys 'workers_report', 'status' and optionally others."""
        if not splitmode:
            report = self.control_messenger_out.recv()
        else:
            report = {'workers_report': []}
            while True:
                r = self.control_messenger_out.recv()
                if isinstance(r, tuple):
                    report[r[0]] = r[1]
                    if r[0] == 'status':
                        break
                elif isinstance(r, dict):
                    report['workers_report'].append(r)
                elif isinstance(r, (Exception, KeyboardInterrupt, interrupt.SignalInterruptError)):
                    report['workers_report'] = r
        return report

    def _listen_and_communicate(self):
        """Interface routine, to catch exceptions and communicate.

        From within this method down, everything is done in the subprocess
        world !
        """
        with interrupt.SignalInterruptHandler(emitlogs=False):
            try:
                (workers_report, pending_instructions) = self._listen()
                if len(pending_instructions) == 0:
                    report = {'workers_report': workers_report,
                              'status': 'finished'}
                else:
                    report = {'workers_report': workers_report,
                              'status': 'pending',
                              'pending': pending_instructions}
            except (Exception, KeyboardInterrupt, interrupt.SignalInterruptError) as e:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                tb = traceback.format_exception(exc_type,
                                                exc_value,
                                                exc_traceback)
                report = {'workers_report': e,
                          'status': 'workers exception',
                          'traceback': tb}
            finally:
                try:
                    self._send_report(report, splitmode=True)
                except (ValueError, OSError) as e:
                    # ValueError = to_be_sent_back too big.
                    # We are sure that a PickleError won't occur since data were
                    # already pickled once (by the workers)
                    taylorism_log.error("The report is too big to be sent back :-(")
                    report = {'workers_report': e,
                              'status': 'transmission exception',
                              'traceback': 'Traceback missing'}
                    self._send_report(report, splitmode=True)

    def _stop_them_working(self, workers):
        # Issue the terminate signal (SIGTERM)
        for wname in list(workers.keys()):
            workers[wname].stop_working()
        # Empty the message queue (but do not process messages) because some
        # of the workers may have completed there work in the meantime...
        empty = False
        while not empty:
            try:
                self.workers_messenger.get(timeout=communications_timeout)
            except queue.Empty:
                empty = True
        # Try to join everybody
        for wname in list(workers.keys()):
            workers.pop(wname).stop_working()

    def _hire_worker(self, workers, instructions):
        w = fpx.worker(**instructions)
        if w is None:
            raise AttributeError("no adequate Worker was found with these instructions: " +
                                 str(instructions))
        w.messenger = self.workers_messenger
        if w.name not in workers.keys():
            workers[w.name] = w
        else:
            raise ValueError('several workers wear the same name: ' + w.name)
        return w

    def _listen(self):
        """
        Actual listening method, i.e. running subprocess at interface between
        main and workers.

        Infinite loop:
          - A. listen to control, for appending new instructions or control signals
          - B. listen to workers, to collect their reports and/or errors
          - C. assign work to workers
          - D. exit loop if any reason for
        """
        workers = {}
        pending_instructions = []
        report = []

        halt = False
        end = False
        stop = False
        try:
            while True:
                # A. listen to control
                if self.control_messenger_in.poll(communications_timeout):
                    control = self.control_messenger_in.recv()
                    if control in self.control_signals.values():
                        # received a control signal
                        if control == self.control_signals['SEND_REPORT']:
                            try:
                                self._send_report(
                                    {'workers_report': report, 'status': 'interim'},
                                    splitmode=True
                                )
                            except ValueError:
                                # ValueError = report too big.
                                # We are sure that a PickleError won't occur
                                # since data were already pickled once (by the
                                # workers)
                                taylorism_log.error("The report is too big to be sent back :-(")
                                raise
                        elif control == self.control_signals['HALT']:
                            halt = True
                        elif control == self.control_signals['RESUME']:
                            halt = False
                        elif (control in [self.control_signals[k]
                                          for k in self.control_signals.keys()
                                          if 'STOP' in k] or
                              control == self.control_signals['END']):
                            end = True
                            if control == self.control_signals['STOP_LISTENING']:
                                break  # leave out the infinite loop
                            elif control in (self.control_signals['STOP'],
                                             self.control_signals['STOP_RIGHTNOW']):
                                stop = True
                                if control == self.control_signals['STOP_RIGHTNOW']:
                                    self._stop_them_working(workers)

                    else:
                        # received new instructions
                        if not end:
                            # if an END or STOP signal has been received,
                            # new instructions are not listened to
                            if isinstance(control, list):
                                pending_instructions.extend(control)
                            elif isinstance(control, dict):
                                pending_instructions.append(control)
                # B. listen to workers
                try:
                    reported = self.workers_messenger.get(timeout=communications_timeout)
                except queue.Empty:
                    pass
                else:
                    # got a new message from workers !
                    report.append(reported)
                    if isinstance(
                        reported['report'],
                        (Exception, KeyboardInterrupt, interrupt.SignalInterruptError)
                    ):
                        # worker got an exception
                        taylorism_log.error("error encountered with worker " +
                                            reported['name'] +
                                            " with traceback:")
                        sys.stderr.writelines(reported['traceback'])
                        sys.stderr.write("Instructions of guilty worker:\n")
                        w = [repr(a) + '\n'
                             for a in sorted(workers[reported['name']].footprint_as_dict().items())
                             if a]
                        sys.stderr.writelines(w)
                        if isinstance(reported['report'], Exception):
                            # The  KeyboardInterrupt/interrupt.SignalInterruptError case
                            # is handled latter on in the overall try/except
                            self._stop_them_working(workers)
                        raise reported['report']
                    else:
                        # worker has finished
                        if self.verbose:
                            msglog = str(reported['report'])
                            if len(msglog) > self.maxlenreport:
                                msglog = msglog[:self.maxlenreport] + ' ...'
                            taylorism_log.info(msglog)
                    workers.pop(reported['name']).bye()
                # C. there is work to do and no STOP signal has been received: re-launch
                if len(pending_instructions) > 0 and not stop and not halt:
                    (launchable, not_yet_launchable) = self.scheduler.launchable(
                        pending_instructions,
                        workers=workers,
                        report=report
                    )
                    for instructions in launchable:
                        instructions_and_shared_memory = instructions.copy()
                        instructions_and_shared_memory.update(self._sharedmemory_common_instructions)
                        try:
                            w = self._hire_worker(workers, instructions_and_shared_memory)
                        except (AttributeError, ValueError):
                            self._stop_them_working(workers)
                            raise
                        w.work()
                        if self.verbose:
                            taylorism_log.info(' '.join(['Worker',
                                                         w.name,
                                                         'started.']))
                    pending_instructions = not_yet_launchable
                # D. should we stop now ?
                if end and (len(workers) == len(pending_instructions) == 0):
                    # a STOP signal has been received, all workers are done and
                    # no more pending instructions remain:
                    # we can leave out infinite loop
                    stop = True
                if stop:
                    break
        except (interrupt.SignalInterruptError, KeyboardInterrupt):
            self._stop_them_working(workers)
            raise

        return report, pending_instructions
