"""
Various Resources for executables used by the OOPS software.
"""

from vortex.data.executables import NWPModel
from ..syntax.stdattrs import gvar, arpifs_cycle, executable_flavour_deco
from ..syntax.stdattrs import oops_run, known_oops_testcomponent_runs
from vortex.syntax.stddeco import namebuilding_append

#: No automatic export
__all__ = []


@namebuilding_append("src", lambda self: self.run)
class OOPSBinary(NWPModel):
    """Yet an other OOPS Binary."""

    _footprint = [
        arpifs_cycle,
        gvar,
        oops_run,
        executable_flavour_deco,
        dict(
            info="OOPS Binary: an OOPS binary, dedicated to a task (a run in OOPS namespace).",
            attr=dict(
                kind=dict(
                    values=[
                        "oopsbinary",
                    ],
                ),
                gvar=dict(
                    default="master_[run]",
                ),
                run=dict(
                    outcast=known_oops_testcomponent_runs,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "oopsbinary"

    def command_line(self, configfile):
        """
        Build command line for execution as a single string.
        """
        cmdline = "{}".format(configfile)
        return cmdline


class OOPSTestComponent(OOPSBinary):
    """Binary for OOPS Tests of components."""

    _footprint = dict(
        info="OOPS Component Test: can run a sub-test or a family of sub-tests",
        attr=dict(
            run=dict(
                values=known_oops_testcomponent_runs,
                outcast=[],
            ),
        ),
    )

    def command_line(self, configfile, test_type=None):
        """
        Build command line for execution as a single string.
        """
        cmdline = ""
        if test_type is not None:
            cmdline += "-t {} ".format(test_type)
        cmdline += super().command_line(configfile)
        return cmdline
