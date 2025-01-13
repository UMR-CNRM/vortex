"""
Common Providers.

For now, only the BDPE access is available here (Base de Donnée des Produits Élaborés).
This provider should work both on Soprano servers and on HPC, be it experimentally for
certain parameters combinations.
"""

from bronx.fancies import loggers
from bronx.stdtypes.date import Time
from vortex.data.providers import Provider
from vortex.syntax.stdattrs import DelayedEnvValue, Namespace, namespacefp
from vortex.util.config import GenericConfigParser

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class BdpeError(Exception):
    """Base for Bdpe errors."""

    pass


class BdpeConfigurationError(BdpeError):
    """Missing BDPE product description."""

    pass


class BdpeMismatchError(BdpeError):
    """BDPE product description does not match ressource description."""

    pass


class BdpeProvider(Provider):
    """
    Provider to resources stored in the BDPE database.

    The BDPE only knows about product ids, base datetime, and terms.
    A dedicated ini file describes the relationship between such ids and
    Vortex resources. This link could be used to deduce the BDPE id from
    the resource (a la footprints). For now, it is only checked that the
    resource attributes are compatible with the product description.

    Canvas of a complete uri:
        bdpe://bdpe.archive.fr/EXPE/date/BDPE_num+term

    The EXPE part is built from the footprint attributes that correspond
    to env variables used by the underlying tool we use: preferred_target,
    forbidden_target, aso., so that the BDPE store can retrieve them from
    the uri (See :class:`BdpeStore`).

    When a resource has no ``date`` attribute, the most recent data is
    extracted from the BDPE (this feature may be used for Alert Models).
    """

    _footprint = [
        namespacefp,
        dict(
            info="BDPE provider",
            attr=dict(
                namespace=dict(
                    default=Namespace("bdpe.archive.fr"),
                    values=["bdpe.archive.fr"],
                ),
                bdpeid=dict(),
                preferred_target=dict(
                    info="The database we'd like to get the data from - See the BDPE documentation.",
                    optional=True,
                    default=DelayedEnvValue("BDPE_CIBLE_PREFEREE", "SEC"),
                    values=[
                        "OPER",
                        "INT",
                        "SEC",
                        "oper",
                        "int",
                        "sec",
                    ],
                ),
                forbidden_target=dict(
                    info="The database we don't want to access - See the BDPE documentation.",
                    optional=True,
                    default=DelayedEnvValue("BDPE_CIBLE_INTERDITE", "OPER"),
                    values=[
                        "OPER",
                        "INT",
                        "SEC",
                        "oper",
                        "int",
                        "sec",
                    ],
                ),
                soprano_domain=dict(
                    info="Databases priorities profile - See the BDPE documentation.",
                    optional=True,
                    default=DelayedEnvValue("DOMAINE_SOPRA", "dev"),
                    values=["oper", "int", "dev"],
                ),
                allow_archive=dict(
                    info="Allow the use of the archive version of the BDPE databases.",
                    optional=True,
                    type=bool,
                    default=False,
                ),
                bdpe_timeout=dict(
                    info="Seconds before abandoning a request.",
                    optional=True,
                    type=int,
                    default=10,
                ),
                bdpe_retries=dict(
                    info="Number of retries when a request fails.",
                    optional=True,
                    type=int,
                    default=3,
                ),
                config=dict(
                    info="A ready to use configuration file object for this storage place.",
                    type=GenericConfigParser,
                    optional=True,
                    default=None,
                ),
                inifile=dict(
                    info=(
                        "The name of the configuration file that will be used (if "
                        + "**config** is not provided."
                    ),
                    optional=True,
                    default="@bdpe-map-resources.ini",
                ),
            ),
            fastkeys={"bdpeid"},
        ),
    ]

    def __init__(self, *args, **kw):
        logger.debug("BDPE provider init %s", self.__class__)
        super().__init__(*args, **kw)
        self._actual_config = self.config
        if self._actual_config is None:
            self._actual_config = GenericConfigParser(inifile=self.inifile)

    @property
    def realkind(self):
        return "bdpe"

    def scheme(self, resource):
        """A dedicated scheme."""
        return "bdpe"

    def netloc(self, resource):
        """The actual netloc is the ``namespace`` attribute of the current provider."""
        return self.namespace.netloc

    def basename(self, resource):
        """Something like 'BDPE_num+term'."""
        myterm = getattr(resource, "term", Time(0))
        if int(myterm) < 0:
            myterm = Time(9000) - myterm
        return "BDPE_{}+{!s}".format(self.bdpeid, myterm)

    def pathname(self, resource):
        """Something like 'PREFERRED_FORBIDDEN_DOMAIN_ARCHIVE_TIMEOUT_RETRIES/date/'."""
        try:
            requested_date = resource.date.vortex()
        except AttributeError:
            requested_date = "most_recent"
        return "{}_{}_{}_{}_{}_{}/{}".format(
            self.preferred_target,
            self.forbidden_target,
            self.soprano_domain,
            self.allow_archive,
            self.bdpe_timeout,
            self.bdpe_retries,
            requested_date,
        )

    def uri(self, resource):
        """
        Overridden to check the resource attributes against
        the BDPE product description from the .ini file.
        """
        # check that the product is described in the configuration file
        if not self._actual_config.has_section(self.bdpeid):
            fmt = 'Missing product n°{} in BDPE configuration file\n"{}"'
            raise BdpeConfigurationError(
                fmt.format(self.bdpeid, self.config.file)
            )

        # resource description: rely on the footprint_export (also used to JSONise resources).
        rsrcdict = {k: str(v) for k, v in resource.footprint_export().items()}

        # check the BDPE pairs against the resource's
        for k, v in self._actual_config.items(self.bdpeid):
            if k not in rsrcdict:
                raise BdpeMismatchError(
                    'Missing key "{}" in resource'.format(k)
                )
            if rsrcdict[k] != v:
                fmt = 'Bad value for key "{}": rsrc="{}" bdpe="{}"'
                raise BdpeMismatchError(fmt.format(k, rsrcdict[k], v))

        return super().uri(resource)
