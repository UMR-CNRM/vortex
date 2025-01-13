"""
A collection of Tasks decorators (to add usual inputs/outputs to existing classes).
"""

from bronx.fancies import loggers

from vortex import toolbox

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def process_needs_lfi_stuff(*kargs, **kwargs):
    """
    Decorator that update the tasks's ``process`` method in order to retrieve the
    things needed with the FA/LFI file format.

    Example (the self.conf.cycle Genv/Uenv cycle will be used)::

        @process_needs_lfi_stuff
        class MyTask(Task):

            def process(self)
                pass

    Example (the self.conf.arpege_cycle Genv/Uenv cycle will be used)::

        @process_needs_lfi_stuff(cyclekey='arpege_cycle')
        class MyOtherTask(Task):

            def process(self)
                pass

    """
    cyclekey = kwargs.pop("cyclekey", "cycle")

    def decorate_process(cls):
        """Decorator for Task: get LFI stuff before calling process."""
        original_process = getattr(cls, "process", None)
        if original_process is not None:

            def process(self, *args, **kwargs):
                _get_lfi_stuff(self, cyclekey)
                original_process(self, *args, **kwargs)

            process.__doc__ = original_process.__doc__
            cls.process = process
        return cls

    if kargs:
        return decorate_process(kargs[0])
    else:
        return decorate_process


def _get_lfi_stuff(self, cyclekey):
    """Get LFI stuff method (called from process)."""
    if "early-fetch" in self.steps or "fetch" in self.steps:
        actualcycle = getattr(self.conf, cyclekey)

        self.sh.title("Toolbox input tblfiscripts")
        toolbox.input(
            role="LFIScripts",
            genv=actualcycle,
            kind="lfiscripts",
            local="usualtools/tools.lfi.tgz",
        )
        self.sh.title("Toolbox input tbiopoll")
        toolbox.input(
            role="IOPoll",
            format="unknown",
            genv=actualcycle,
            kind="iopoll",
            language="perl",
            local="usualtools/io_poll",
        )
        self.sh.title("Toolbox input tblfitools")
        toolbox.input(
            role="LFITOOLS",
            genv=actualcycle,
            kind="lfitools",
            local="usualtools/lfitools",
        )
