"""
Common interest classes to help setup the DrHook library environment.
"""

import footprints
from bronx.fancies import loggers

from vortex.algo.components import (
    AlgoComponentDecoMixin,
    Parallel,
    algo_component_deco_mixin_autodoc,
)

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


@algo_component_deco_mixin_autodoc
class DrHookDecoMixin(AlgoComponentDecoMixin):
    """Handle DrHook settings in AlgoComponents.

    This mixin class is intended to be used with AlgoComponent classes. It will
    automatically add footprints' arguments related to DrHook (namely the
    drhookprof boolean attribute that is optional and False by default),
    and set up DrHook environment variables (:meth:`_drhook_varexport`) depending
    on the context (MPI run or not).
    """

    _MIXIN_EXTRA_FOOTPRINTS = [
        footprints.Footprint(
            attr=dict(
                drhookprof=dict(
                    info="Activate the DrHook profiling.",
                    optional=True,
                    type=bool,
                    default=False,
                    doc_zorder=-50,
                ),
            ),
        )
    ]

    def _drhook_varexport(self, rh, opts):  # @UnusedVariable
        """Export proper DrHook variables"""
        drhook_vars = (
            [
                ("DR_HOOK", "1"),
                ("DR_HOOK_OPT", "prof"),
                ("DR_HOOK_IGNORE_SIGNALS", "-1"),
            ]
            if self.drhookprof
            else [("DR_HOOK", "0"), ("DR_HOOK_IGNORE_SIGNALS", "-1")]
        )
        if not isinstance(self, Parallel):
            drhook_vars += [
                ("DR_HOOK_SILENT", "1"),
                ("DR_HOOK_NOT_MPI", "1"),
                ("DR_HOOK_ASSERT_MPI_INITIALIZED", "0"),
            ]
        for k, v in drhook_vars:
            logger.info("Setting DRHOOK env %s = %s", k, v)
            self.env[k] = v

    _MIXIN_PREPARE_HOOKS = (_drhook_varexport,)
