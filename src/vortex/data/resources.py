"""
Abstract class for any "Resource". "Resource" objects describe what is in this
or that data.

:seealso: The :mod:`~vortex.data.flow`, :mod:`~vortex.data.outflow`,
          :mod:`~vortex.data.executables` or  :mod:`~gco.data.resources` for more
          specialised versions that may better fit your needs.
"""

from bronx.fancies import loggers
from bronx.stdtypes.dictionaries import LowerCaseDict

import footprints

from vortex.syntax.stdattrs import nativefmt_deco, notinrepr, term_deco
from .contents import DataContent, UnknownContent, FormatAdapter

#: Export Resource and associated Catalog classes.
__all__ = [
    "Resource",
]

logger = loggers.getLogger(__name__)


class Resource(footprints.FootprintBase):
    """Abstract class for any Resource."""

    _abstract = True
    _collector = ("resource",)
    _footprint = [
        nativefmt_deco,
        dict(
            info="Abstract Resource",
            attr=dict(
                clscontents=dict(
                    info="The class instantiated to read the container's content",
                    type=DataContent,
                    isclass=True,
                    optional=True,
                    default=UnknownContent,
                    doc_visibility=footprints.doc.visibility.ADVANCED,
                )
            ),
            fastkeys={"kind", "nativefmt"},
        ),
    ]

    def __init__(self, *args, **kw):
        logger.debug("Resource init %s", self.__class__)
        super().__init__(*args, **kw)
        self._mailbox = LowerCaseDict()

    @property
    def realkind(self):
        return "resource"

    def _str_more(self):
        """Return a string representation of meaningful attributes for formatted output."""
        d = self.footprint_as_shallow_dict()
        for xdel in [x for x in notinrepr if x in d]:
            del d[xdel]
        return " ".join(["{:s}='{!s}'".format(k, v) for k, v in d.items()])

    @property
    def mailbox(self):
        """A nice cocoon to store miscellaneous information."""
        return self._mailbox

    def generic_pathinfo(self):
        """
        Returns anonymous dict with suitable informations from vortex point of view.
        Doomed to be overwritten.
        """
        return dict()

    def pathinfo(self, provider):
        """Proxy to the appropriate method prefixed by provider name."""
        actualpathinfo = getattr(
            self, provider + "_pathinfo", self.generic_pathinfo
        )
        return actualpathinfo()

    def generic_basename(self):
        """Abstract method."""
        pass

    def basename(self, provider):
        """Proxy to the appropriate method prefixed by provider name."""
        actualbasename = getattr(
            self, provider + "_basename", self.generic_basename
        )
        return actualbasename()

    def namebuilding_info(self):
        """
        Returns anonymous dict with suitable informations from vortex point of view.
        In real world, probably doomed to return an empty dict.
        """
        return {"radical": self.realkind}

    def vortex_urlquery(self):
        """Query to be binded to the resource's location in vortex space."""
        return None

    def urlquery(self, provider):
        """Proxy to the appropriate method prefixed by provider name."""
        actualurlquery = getattr(
            self, provider + "_urlquery", self.vortex_urlquery
        )
        return actualurlquery()

    def gget_basename(self):
        """Duck typing: return an empty string by default."""
        return dict()

    def uget_basename(self):
        """Proxy to :meth:`gget_basename`."""
        return self.gget_basename()

    def genv_basename(self):
        """Just retrieve a potential gvar attribute."""
        return getattr(self, "gvar", "")

    def uenv_basename(self):
        """Proxy to :meth:`genv_basename`."""
        return self.genv_basename()

    def gget_urlquery(self):
        """Duck typing: return an empty string by default."""
        return ""

    def uget_urlquery(self):
        """Proxy to :meth:`gget_urlquery`."""
        return self.gget_urlquery()

    def genv_urlquery(self):
        """Proxy to :meth:`gget_urlquery`."""
        return self.gget_urlquery()

    def uenv_urlquery(self):
        """Proxy to :meth:`gget_urlquery`."""
        return self.gget_urlquery()

    def contents_args(self):
        """Returns default arguments value to class content constructor."""
        return dict()

    def contents_handler(self, **kw):
        """Returns class content handler according to attribute ``clscontents``."""
        this_args = self.contents_args()
        this_args.update(kw)
        return self.clscontents(**this_args)

    def stackedstorage_resource(self):
        """
        If the present resource supports stacked storage (note: this feature is
        only available in the Vortex store), return the corresponding resource
        plus a boolean indicating if data from different members are kept
        separate.
        """
        return None, True


class Unknown(Resource):
    _footprint = [
        dict(
            info="Unknown assumed NWP Resource (development only !)",
            attr=dict(
                unknown=dict(info="Activate the unknown resource.", type=bool),
                nickname=dict(
                    info="The string that serves the purpose of Vortex's basename radical",
                    optional=True,
                    default="unknown",
                ),
                clscontents=dict(
                    default=FormatAdapter,
                ),
            ),
            fastkeys={"unknown"},
        )
    ]

    def namebuilding_info(self):
        """Keep the Unknown resource unknown."""
        bdict = super().namebuilding_info()
        bdict.update(
            radical=self.nickname,
        )
        if self.nativefmt in ("auto", "autoconfig", "foo", "unknown"):
            del bdict["fmt"]
        return bdict


class UnknownWithTerm(Unknown):
    _footprint = [
        term_deco,
        dict(
            info="Unknown assumed NWP Resource but with term (development only !)",
        ),
    ]


# Activate the footprint's fasttrack on the resources collector
fcollect = footprints.collectors.get(tag="resource")
fcollect.fasttrack = ("kind",)
del fcollect
