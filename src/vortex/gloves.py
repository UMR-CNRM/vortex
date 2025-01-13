"""
GLObal Versatile Environment classes are responsible for session-wide
configuration (username, emil adress, ...)
"""

from bronx.fancies import loggers
import footprints

from vortex.tools.env import Environment

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class Glove(footprints.FootprintBase):
    """Base class for GLObal Versatile Environment."""

    _abstract = True
    _collector = ("glove",)
    _footprint = dict(
        info="Abstract glove",
        attr=dict(
            email=dict(
                alias=["address"],
                optional=True,
                default=Environment(active=False)["email"],
                access="rwx",
            ),
            vapp=dict(
                optional=True,
                default="play",
                access="rwx",
            ),
            vconf=dict(
                optional=True,
                default="sandbox",
                access="rwx",
            ),
            tag=dict(
                optional=True,
                default="default",
            ),
            user=dict(
                alias=("logname", "username"),
                optional=True,
                default=Environment(active=False)["logname"],
            ),
            profile=dict(
                alias=("kind", "membership"),
                values=["oper", "dble", "test", "research", "tourist"],
                remap=dict(tourist="research"),
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug("Glove abstract %s init", self.__class__)
        super().__init__(*args, **kw)
        self._rmdepthmin = 3
        self._siteroot = None
        self._siteconf = None
        self._sitedoc = None
        self._sitesrc = None
        self._ftdhost = None
        self._ftduser = None
        self._ftusers = dict()

    @property
    def realkind(self):
        """Returns the litteral string identity of the current glove."""
        return "glove"

    @property
    def configrc(self):
        """Returns the path of the default directory where ``.ini`` files are stored."""
        return Environment(active=False).HOME + "/.vortexrc"

    @property
    def siteroot(self):
        """Returns the path of the vortex install directory."""
        if not self._siteroot:
            self._siteroot = "/".join(__file__.split("/")[0:-3])
        return self._siteroot

    @property
    def siteconf(self):
        """Returns the path of the default directory where ``.ini`` files are stored."""
        if not self._siteconf:
            self._siteconf = "/".join((self.siteroot, "conf"))
        return self._siteconf

    @property
    def sitedoc(self):
        """Returns the path of the default directory where ``.ini`` files are stored."""
        if not self._sitedoc:
            self._sitedoc = "/".join((self.siteroot, "sphinx"))
        return self._sitedoc

    @property
    def sitesrc(self):
        """Returns the path of the default directory where ``.ini`` files are stored."""
        if not self._sitesrc:
            self._sitesrc = (
                "/".join((self.siteroot, "site")),
                "/".join((self.siteroot, "src")),
            )
        return self._sitesrc

    def setenv(self, app=None, conf=None):
        """Change ``vapp`` or/and ``vconf`` in one call."""
        if app is not None:
            self.vapp = app
        if conf is not None:
            self.vconf = conf
        return (self.vapp, self.vconf)

    def setmail(self, domain=None):
        """Refresh actual email with current username and provided ``domain``."""
        if domain is None:
            from vortex import sessions

            domain = sessions.system().getfqdn()
        return "@".join((self.user, domain))

    @property
    def xmail(self):
        if self.email is None:
            return self.setmail()
        else:
            return self.email

    def safedirs(self):
        """Protected paths as a list a tuples (path, depth)."""
        e = Environment(active=False)
        return [(e.HOME, 2), (e.TMPDIR, 1)]

    def setftuser(self, user, hostname=None):
        """Register a default username for *hostname*.

        If *hostname* is omitted the default username is set.
        """
        if hostname is None:
            self._ftduser = user
        else:
            if not user:
                del self._ftusers[hostname]
            else:
                self._ftusers[hostname] = user

    def getftuser(self, hostname, defaults_to_user=True):
        """Get the default username for a given *hostname*."""
        if self._ftusers.get(hostname, None):
            return self._ftusers[hostname]
        else:
            if self._ftduser:
                return self._ftduser
            else:
                return Environment.current().get(
                    "VORTEX_ARCHIVE_USER",
                    self.user if defaults_to_user else None,
                )

    def _get_default_fthost(self):
        if self._ftdhost:
            return self._ftdhost
        else:
            return Environment.current().get("VORTEX_ARCHIVE_HOST", None)

    def _set_default_fthost(self, value):
        self._ftdhost = value

    def _del_default_fthost(self):
        self._ftdhost = None

    default_fthost = property(
        _get_default_fthost, _set_default_fthost, _del_default_fthost
    )

    def describeftsettings(self, indent="+ "):
        """Returns a printable description of default file transfert usernames."""
        card = "\n".join(
            [
                "{0}{3:48s} = {4:s}",
            ]
            + [
                "{0}{1:48s} = {2:s}",
            ]
            + (
                [
                    "{0}Host specific FT users:",
                ]
                if self._ftusers
                else []
            )
            + [
                "{0}" + "  {:46s} = {:s}".format(k, v)
                for k, v in self._ftusers.items()
                if v
            ]
        ).format(
            indent,
            "Default FT User",
            str(self._ftduser),
            "Default FT Host",
            str(self._ftdhost),
        )
        return card

    def idcard(self, indent="+ "):
        """Returns a printable description of the current glove."""
        card = "\n".join(
            (
                "{0}User     = {1:s}",
                "{0}Profile  = {2!s}",
                "{0}Vapp     = {3:s}",
                "{0}Vconf    = {4:s}",
                "{0}Configrc = {5:s}",
            )
        ).format(
            indent,
            self.user,
            self.profile,
            self.vapp,
            self.vconf,
            self.configrc,
        )
        return card


class ResearchGlove(Glove):
    """
    The default glove as long as you do not need operational privileges.
    Optional arguments are:

    * mail
    * profile (default is research)
    """

    _explicit = False
    _footprint = dict(
        info="Research glove",
        attr=dict(
            profile=dict(
                optional=True,
                values=["research", "tourist"],
                default="research",
            )
        ),
    )

    @property
    def realkind(self):
        return "research"


class OperGlove(Glove):
    """
    The default glove if you need operational privileges.
    Mandatory arguments are:

    * user
    * profile
    """

    _footprint = dict(
        info="Operational glove",
        attr=dict(
            user=dict(values=["mxpt001"]),
            profile=dict(
                optional=False,
                values=["oper", "dble", "test", "miroir"],
            ),
        ),
    )

    @property
    def realkind(self):
        return "opuser"


class UnitTestGlove(ResearchGlove):
    """A very special glove for unit-tests."""

    _footprint = dict(
        info="Unit-Test Glove",
        attr=dict(
            profile=dict(
                optional=False,
                values=["utest"],
            ),
            test_configrc=dict(
                optional=False,
            ),
            test_siteroot=dict(
                optional=False,
            ),
        ),
    )

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self._siteroot = self.test_siteroot

    @property
    def configrc(self):
        """Returns the path of the default directory where ``.ini`` files are stored."""
        return self.test_configrc
