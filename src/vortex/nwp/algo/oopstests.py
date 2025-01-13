"""
AlgoComponents for OOPS elementary tests.
"""

import json

import footprints

from vortex.algo.components import (
    AlgoComponentDecoMixin,
    algo_component_deco_mixin_autodoc,
)
from ..syntax.stdattrs import oops_test_type, oops_expected_target
from .oopsroot import (
    OOPSParallel,
    OOPSODB,
    OOPSMembersTermsDecoMixin,
    OOPSMembersTermsDetectDecoMixin,
)

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


@algo_component_deco_mixin_autodoc
class _OOPSTestDecoMixin(AlgoComponentDecoMixin):
    """Extend OOPSParallel Algo Components with OOPS Tests features.

    This mixin class is intended to be used with AlgoComponent classes. It will
    automatically add the ``test_type`` footprints' attribute and extend the
    the dictionary that is used to build the binary' command line.
    """

    _MIXIN_EXTRA_FOOTPRINTS = (oops_test_type,)

    def _ooptest_cli_opts_extend(self, prev):
        """Prepare options for the resource's command line."""
        prev["test_type"] = self.test_type
        return prev

    _MIXIN_CLI_OPTS_EXTEND = (_ooptest_cli_opts_extend,)


@algo_component_deco_mixin_autodoc
class _OOPSTestExpTargetDecoMixin(AlgoComponentDecoMixin):
    """Extend OOPSParallel Algo Components with OOPS Tests verification features.

    This mixin class is intended to be used with AlgoComponent classes. It will
    automatically add the ``expected_target`` footprints' attribute and use it
    to setup the associated environment variable
    (see :meth:`set_expected_target`).
    """

    _MIXIN_EXTRA_FOOTPRINTS = (oops_expected_target,)

    def set_expected_target(self):
        """Set env variable EXPECTED_CONFIG.

        It will create it using a JSON "dump" of either:

            * The Algo Component's attribute ``expected_target``;
            * if attribute ``expected_target`` == {'from':'reference_summary'},
              the oops:self.test_type 'as EXPECTED_RESULT' key of the JSON resource
              of role "Reference Summary".
            * a default value, enabling to pass test
        """
        # if attribute 'expected_target' is attribute and given to the algo, use it
        target = self._set_expected_target_from_attribute()
        # else, go find Reference summary in effective inputs
        if target is not None and target.get("from") == "reference_summary":
            target = self._set_expected_target_from_reference_summary()
        # Else, default to be sure to pass any in-binary-test
        if target is None:
            target = (
                self._set_expected_target_default()
            )  # CLEANME: to be removed after CY47 ?
        # Then in the end, export variable
        target = json.dumps(target)
        logger.info("Expected Target for Test: " + target)
        self.env.update(EXPECTED_RESULT=target)

    def _set_expected_target_from_attribute(self):
        """Read target in Algo attribute."""
        if hasattr(self, "expected_target"):
            if self.expected_target is not None:
                target = self.expected_target
                logger.info("Set EXPECTED_RESULT from Attribute")
                return target

    def _set_expected_target_from_reference_summary(self):
        """Read target in ReferenceSummary effective input"""
        target = None
        ref_summary = [
            s
            for s in self.context.sequence.effective_inputs(
                role=("Reference",)
            )
            if s.rh.resource.kind == "taskinfo"
        ]
        if len(ref_summary) > 0:
            ref_summary = ref_summary[0].rh.contents.data
            target = ref_summary.get("oops:" + self.test_type, {}).get(
                "as EXPECTED_RESULT", None
            )
        if target is not None:
            logger.info("Set EXPECTED_RESULT from Reference summary")
        return target

    def _set_expected_target_default(
        self,
    ):  # CLEANME: to be removed after CY47 ?
        """Set default, for binary not to crash before CY47."""
        target = {
            "significant_digits": "-9",
            "expected_Jo": "9999",
            "expected_variances": "9999",
            "expected_diff": "9999",
        }
        logger.info("Set default EXPECTED_RESULT")
        return target

    def _ooptest_exptarget_prepare_hook(self, rh, opts):
        """Call set_expected_target juste after prepare."""
        self.set_expected_target()

    _MIXIN_PREPARE_HOOKS = (_ooptest_exptarget_prepare_hook,)


class OOPSTest(
    OOPSParallel,
    _OOPSTestDecoMixin,
    _OOPSTestExpTargetDecoMixin,
    OOPSMembersTermsDetectDecoMixin,
):
    """OOPS Tests without ODB."""

    _footprint = dict(
        info="OOPS Test run.",
        attr=dict(
            kind=dict(
                values=["ootest"],
            ),
            test_type=dict(
                outcast=[
                    "ensemble/build",
                ]
            ),
        ),
    )


class OOPSTestEnsBuild(
    OOPSParallel, _OOPSTestDecoMixin, OOPSMembersTermsDecoMixin
):
    """OOPS Tests without ODB: ensemble/build specific case"""

    _footprint = dict(
        info="OOPS Test run.",
        attr=dict(
            kind=dict(
                values=["ootest"],
            ),
            test_type=dict(
                values=[
                    "ensemble/build",
                ]
            ),
        ),
    )


class OOPSObsOpTest(
    OOPSODB,
    _OOPSTestDecoMixin,
    _OOPSTestExpTargetDecoMixin,
    OOPSMembersTermsDetectDecoMixin,
):
    """OOPS Obs Operators Tests."""

    _footprint = dict(
        info="OOPS Obs Operators Tests.",
        attr=dict(
            kind=dict(
                values=["ootestobs"],
            ),
            virtualdb=dict(
                default="ccma",
            ),
        ),
    )


class OOPSecma2ccma(OOPSODB, _OOPSTestDecoMixin):
    """OOPS Test ECMA 2 CCMA completer."""

    _footprint = dict(
        info="OOPS ECMA 2 CCMA completer.",
        attr=dict(
            kind=dict(
                values=["ootest2ccma"],
            ),
            virtualdb=dict(
                values=["ecma"],
            ),
        ),
    )

    def postfix(self, rh, opts):
        """Rename the ECMA database once OOPS has run."""
        super().postfix(rh, opts)
        self._mv_ecma2ccma()

    def _mv_ecma2ccma(self):
        """Make the appropriate renaming of files in ECMA to CCMA."""
        for e in self.lookupodb():
            edir = e.rh.container.localpath()
            self.odb.change_layout("ECMA", "CCMA", edir)
            self.system.mv(edir, edir.replace("ECMA", "CCMA"))
