"""
Module needed to work with ARM tools such as Forge.
"""

from bronx.fancies import loggers

from vortex.util.config import load_template

#: No automatic export
__all__ = ["ArmForgeTool"]

logger = loggers.getLogger(__name__)


class ArmForgeTool:
    """Work with the ARM tools such as DDT & MAP."""

    def __init__(self, ticket):
        """
        :param ticket: The current Vortex' session ticket.
        """
        self._t = ticket
        self._sh = self._t.sh
        self._config = self._sh.default_target.items("armtools")
        self._ddtpath = self._sh.env.get("VORTEX_ARM_DDT_PATH", None)
        self._mappath = self._sh.env.get("VORTEX_ARM_MAP_PATH", None)
        self._forgedir = self._sh.env.get(
            "VORTEX_ARM_FORGE_DIR", self.config.get("forgedir", None)
        )
        self._forgeversion = self._sh.env.get(
            "VORTEX_ARM_FORGE_VERSION", self.config.get("forgeversion", 999999)
        )
        self._forgeversion = int(self._forgeversion)
        if self._forgedir and self._ddtpath is None:
            self._ddtpath = self._sh.path.join(self._forgedir, "bin", "ddt")
        if self._forgedir and self._mappath is None:
            self._mappath = self._sh.path.join(self._forgedir, "bin", "map")

    @property
    def config(self):
        """The configuration dictionary."""
        return self._config

    @property
    def ddtpath(self):
        """The path to the DDT debuger executable."""
        if self._ddtpath is None:
            raise RuntimeError(
                "DDT requested but the DDT path is not configured."
            )
        return self._ddtpath

    @property
    def mappath(self):
        """The path to the MAP profiler executable."""
        if self._mappath is None:
            raise RuntimeError(
                "MAP requested but the MAP path is not configured."
            )
        return self._mappath

    def _dump_forge_session(self, sources=(), workdir=None):
        """Create the ARM Forge's session file to list source directories."""
        targetfile = "armforge-vortex-session-file.ddt"
        if workdir:
            targetfile = self._sh.path.join(workdir, targetfile)
        tpl = load_template(
            self._t,
            "@armforge-session-conf.tpl",
            encoding="utf-8",
            version=self._forgeversion,
        )
        sconf = tpl.substitute(
            sourcedirs="\n".join(
                [
                    "        <directory>{:s}</directory>".format(d)
                    for d in sources
                ]
            )
        )
        with open(targetfile, "w") as fhs:
            fhs.write(sconf)
        return targetfile

    def ddt_prefix_cmd(self, sources=(), workdir=None):
        """Generate the prefix command required to start DDT."""
        if sources:
            return [
                self.ddtpath,
                "--session={:s}".format(
                    self._dump_forge_session(sources, workdir=workdir)
                ),
                "--connect",
            ]
        else:
            return [self.ddtpath, "--connect"]
