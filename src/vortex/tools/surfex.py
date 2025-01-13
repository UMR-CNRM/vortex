"""
A system addon to support the "sfxtools" utility program.
"""

from bronx.fancies import loggers
import footprints

from . import addons

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def use_in_shell(sh, **kw):
    """Extend current shell with the sfxtools interface defined by optional arguments."""
    kw["shell"] = sh
    return footprints.proxy.addon(**kw)


class SFX_Tool(addons.Addon):
    """
    Interface to the sfxtools command.
    """

    LFI_HNDL_SPEC = ":1"
    DR_HOOK_SILENT = 1
    DR_HOOK_NOT_MPI = 1
    OMP_STACKSIZE = "32M"
    KMP_STACKSIZE = "32M"
    KMP_MONITOR_STACKSIZE = "32M"

    _footprint = dict(
        info="Default SFXTools interface",
        attr=dict(
            kind=dict(
                values=["sfx", "surfex"],
            ),
            cmd=dict(
                alias=("sfxcmd",),
                default="sfxtools",
            ),
            path=dict(
                alias=("sfxpath",),
            ),
            toolkind=dict(
                default="sfxtools",
            ),
        ),
    )

    def sfx_fa2lfi(self, fafile, lfifile):
        return self._spawn(
            ["sfxfa2lfi", "--sfx-fa--file", fafile, "--sfx-lfi-file", lfifile]
        )

    def sfx_lfi2fa(self, lfifile, fafile):
        return self._spawn(
            ["sfxlfi2fa", "--sfx-fa--file", fafile, "--sfx-lfi-file", lfifile]
        )
