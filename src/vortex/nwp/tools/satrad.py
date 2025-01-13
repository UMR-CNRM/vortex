"""
Common interest classes to help setup the RTTOV/IFS environment.
"""

import re

from bronx.fancies import loggers

from vortex.algo.components import AlgoComponentDecoMixin, AlgoComponentError
from vortex.algo.components import algo_component_deco_mixin_autodoc

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


@algo_component_deco_mixin_autodoc
class SatRadDecoMixin(AlgoComponentDecoMixin):
    """RTTOV settings + Satellites related stuffs.

    This mixin class is intended to be used with AlgoComponent classes. It will
    automatically set up the path to RTTOV coefficient files
    (:meth:`_satrad_coeffdir_setup`).

    In addition it provides the :meth:`setchannels` utility method (that have to
    be called manually if needed).
    """

    def _satrad_coeffdir_setup(self, rh, opts):  # @UnusedVariable
        """Look for RTTOV coefficient files and act on it."""
        rtcoefs = self.context.sequence.effective_inputs(
            role="RtCoef", kind="rtcoef"
        )
        if rtcoefs:
            sh = self.system
            rtpaths = {
                sh.path.dirname(
                    sh.path.realpath(rtcoef.rh.container.localpath())
                )
                for rtcoef in rtcoefs
            }
            if len(rtpaths) != 1:
                raise AlgoComponentError(
                    "The Radiative Transfer Coefficients are scattered in"
                    + "several directories: {!s}".format(rtpaths)
                )
            rtpath = rtpaths.pop()
            logger.info("Setting %s = %s", "RTTOV_COEFDIR", rtpath)
            self.env["RTTOV_COEFDIR"] = rtpath

    _MIXIN_PREPARE_HOOKS = (_satrad_coeffdir_setup,)

    def setchannels(self):
        """Look up for channels namelists in effective inputs."""
        namchan = [
            x.rh
            for x in self.context.sequence.effective_inputs(kind="namelist")
            if "channel" in x.rh.options
        ]
        for thisnam in namchan:
            thisloc = (
                re.sub(r"\d+$", "", thisnam.options["channel"]) + "channels"
            )
            if thisloc != thisnam.container.localpath():
                logger.info(
                    "Linking < %s > to < %s >",
                    thisnam.container.localpath(),
                    thisloc,
                )
                self.system.softlink(thisnam.container.localpath(), thisloc)
