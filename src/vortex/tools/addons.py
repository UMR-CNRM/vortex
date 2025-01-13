"""
Abstract classes for System addons.
"""

from collections import defaultdict

from bronx.fancies import loggers
from bronx.syntax.decorators import nicedeco
import footprints

from vortex.config import get_from_config_w_default
from vortex.layout import contexts
from vortex.tools.env import Environment
from vortex.tools.systems import OSExtended

logger = loggers.getLogger(__name__)

#: No automatic export
__all__ = []


class Addon(footprints.FootprintBase):
    """Root class for any :class:`Addon` system subclasses."""

    _abstract = True
    _collector = ("addon",)
    _footprint = dict(
        info="Default add-on",
        attr=dict(
            kind=dict(),
            sh=dict(
                type=OSExtended,
                alias=("shell",),
                access="rwx-weak",
            ),
            env=dict(
                type=Environment,
                optional=True,
                default=None,
                access="rwx",
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
            cfginfo=dict(
                optional=True,
                default="[kind]",
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
            cmd=dict(
                optional=True,
                default=None,
                access="rwx",
            ),
            path=dict(
                optional=True,
                default=None,
                access="rwx",
            ),
            cycle=dict(
                optional=True,
                default=None,
                access="rwx",
            ),
            toolkind=dict(optional=True, default=None),
        ),
    )

    def __init__(self, *args, **kw):
        """Abstract Addon initialisation."""
        logger.debug("Abstract Addon init %s", self.__class__)
        super().__init__(*args, **kw)
        self.sh.extend(self)
        self._context_cache = defaultdict(dict)
        self._cmd_xperms_cache = set()
        if self.env is None:
            self.env = Environment(active=False, clear=True)
        clsenv = self.__class__.__dict__
        for k in [x for x in clsenv.keys() if x.isupper()]:
            self.env[k] = clsenv[k]
        if self.path is None:
            self.path = get_from_config_w_default(
                section="nwp-tools",
                key=self.kind,
                default=None,
            )

    @classmethod
    def in_shell(cls, shell):
        """Grep any active instance of that class in the specified shell."""
        lx = [x for x in shell.search if isinstance(x, cls)]
        return lx[0] if lx else None

    def _query_context(self):
        """Return the path and cmd for the current context.

        Results are cached so that the context's localtracker is explored only once.

        .. note:: We use the localtracker instead of the sequence because, in
            multistep jobs, the localtracker is preserved between steps. It's
            less elegant but it plays nice with MTOOL.
        """
        ctxtag = contexts.Context.tag_focus()
        if ctxtag not in self._context_cache and self.toolkind is not None:
            ltrack = contexts.current().localtracker
            # NB: 'str' is important because local might be in unicode...
            candidates = [
                str(self.sh.path.realpath(local))
                for local, entry in ltrack.items()
                if (
                    entry.latest_rhdict("get")
                    .get("resource", dict())
                    .get("kind", "")
                    == self.toolkind
                )
            ]
            if candidates:
                realpath = candidates.pop()
                self._context_cache[ctxtag] = dict(
                    path=self.sh.path.dirname(realpath),
                    cmd=self.sh.path.basename(realpath),
                )
        return self._context_cache[ctxtag]

    @property
    def actual_path(self):
        """The path that should be used in the current context."""
        infos = self._query_context()
        ctxpath = infos.get("path", None)
        return self.path if ctxpath is None else ctxpath

    @property
    def actual_cmd(self):
        """The cmd that should be used in the current context."""
        infos = self._query_context()
        ctxcmd = infos.get("cmd", None)
        return self.cmd if ctxcmd is None else ctxcmd

    def _spawn_commons(self, cmd, **kw):
        """Internal method setting local environment and calling standard shell spawn."""

        # Is there a need for an interpreter ?
        if "interpreter" in kw:
            cmd.insert(0, kw.pop("interpreter"))
        else:
            # The first element of the command line needs to be executable
            if cmd[0] not in self._cmd_xperms_cache:
                self._cmd_xperms_cache.add(cmd[0])
                self.sh.xperm(cmd[0], force=True)

        # Overwrite global module env values with specific ones
        with self.sh.env.clone() as localenv:
            localenv.verbose(True, self.sh)
            localenv.update(self.env)

            # Check if a pipe is requested
            inpipe = kw.pop("inpipe", False)

            # Ask the attached shell to run the addon command
            if inpipe:
                kw.setdefault("stdout", True)
                rc = self.sh.popen(cmd, **kw)
            else:
                rc = self.sh.spawn(cmd, **kw)

        return rc

    def _spawn(self, cmd, **kw):
        """Internal method setting local environment and calling standard shell spawn."""

        # Insert the actual tool command as first argument
        cmd.insert(0, self.actual_cmd)
        if self.actual_path is not None:
            cmd[0] = self.actual_path + "/" + cmd[0]

        return self._spawn_commons(cmd, **kw)

    def _spawn_wrap(self, cmd, **kw):
        """Internal method setting local environment and calling standard shell spawn."""

        # Insert the tool path before the first argument
        if self.actual_path is not None:
            cmd[0] = self.actual_path + "/" + cmd[0]

        return self._spawn_commons(cmd, **kw)


class FtrawEnableAddon(Addon):
    """Root class for any :class:`Addon` system subclasses that needs to override rawftput."""

    _abstract = True
    _footprint = dict(
        info="Default add-on with rawftput support.",
        attr=dict(
            rawftshell=dict(
                info="Path to ftserv's concatenation shell",
                optional=True,
                default=None,
                access="rwx",
                doc_visibility=footprints.doc.visibility.GURU,
            ),
        ),
    )

    def __init__(self, *args, **kw):
        """Abstract Addon initialisation."""
        logger.debug("Abstract Addon init %s", self.__class__)
        super().__init__(*args, **kw)
        # If needed, look in the config file for the rawftshell
        if self.rawftshell is None:
            self.rawftshell = get_from_config_w_default(
                section="rawftshell",
                key=self.kind,
                default=None,
            )


class AddonGroup(footprints.FootprintBase):
    """Root class for any :class:`AddonGroup` system subclasses.

    An AddonGroup is not really an Addon... it just loads a bunch of other
    Addons or AddonGroups into the current shell.
    """

    _abstract = True
    _collector = ("addon",)
    _footprint = dict(
        info="Default add-on group",
        attr=dict(
            kind=dict(),
            sh=dict(
                type=OSExtended,
                alias=("shell",),
            ),
            env=dict(
                type=Environment,
                optional=True,
                default=None,
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
            cycle=dict(
                optional=True,
                default=None,
            ),
            verboseload=dict(
                optional=True,
                default=True,
                type=bool,
            ),
        ),
    )

    _addonslist = None

    def __init__(self, *args, **kw):
        """Abstract Addon initialisation."""
        logger.debug("Abstract Addon init %s", self.__class__)
        super().__init__(*args, **kw)
        self._addons_load()

    def _addons_load(self):
        if self._addonslist is None:
            raise RuntimeError(
                "the _addonslist classe variable must be overriden."
            )
        self._load_addons_from_list(self._addonslist)

    def _load_addons_from_list(self, addons):
        if self.verboseload:
            logger.info("Loading the %s Addons group.", self.kind)
        for addon in addons:
            _shadd = footprints.proxy.addon(
                kind=addon,
                sh=self.sh,
                env=self.env,
                cycle=self.cycle,
                verboseload=self.verboseload,
            )
            if self.verboseload:
                logger.info("%s Addon is: %s", addon, repr(_shadd))


def require_external_addon(*addons):
    """
    A method decorator usable in addons, that will check if addons listed in
    **addons** are properly loaded in the parent System object.

    If not, a :class:`RuntimeError` exception will be raised.
    """

    @nicedeco
    def r_addon_decorator(method):
        def decorated(self, *kargs, **kwargs):
            # Create a cache in self... ugly but efficient !
            if not hasattr(self, "_require_external_addon_check_cache"):
                setattr(self, "_require_external_addon_check_cache", set())
            ko_addons = set()
            loaded_addons = None
            for addon in addons:
                if addon in self._require_external_addon_check_cache:
                    continue
                if loaded_addons is None:
                    loaded_addons = self.sh.loaded_addons()
                if addon in loaded_addons:
                    self._require_external_addon_check_cache.add(addon)
                else:
                    ko_addons.add(addon)
            if ko_addons:
                raise RuntimeError(
                    "The following addons are needed to use the {:s} method: {:s}".format(
                        method.__name__, ", ".join(ko_addons)
                    )
                )
            return method(self, *kargs, **kwargs)

        return decorated

    return r_addon_decorator
