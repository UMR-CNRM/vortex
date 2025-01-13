"""
Abstract for any "Resource" class that deal with some kind of :class:`Script` or
:class:`Binary` executable.

Mode specialised version are also provided for various physical models:

    * :class:`NWPModel`;
    * :class:`OceanographicModel`;
    * :class:`SurfaceModel`;
    * :class:`ChemistryModel`.

"""

from bronx.syntax import mktuple
import footprints

from .resources import Resource
from vortex.syntax.stdattrs import model_deco
from vortex.util.config import JacketConfigParser

#: No automatic export
__all__ = []


class Jacket:
    """The class definition of in and out resources from a given executable."""

    def __init__(self, afile=None):
        if afile:
            self.config = JacketConfigParser(afile)
            self.virtual = False
        else:
            self.virtual = True
        self._initfile = afile

    def as_dump(self):
        return "file={!r}".format(self._initfile)

    def export_dict(self):
        return self._initfile


class Executable(Resource):
    """Abstract class for resources that could be executed."""

    _abstract = True
    _footprint = dict(
        info="Miscellaneaous executable resource",
        attr=dict(
            cycle=dict(
                info="Any kind of cycle name",
                optional=True,
                default=None,
                access="rwx",
            ),
            kind=dict(
                info="The resource's kind.",
                doc_zorder=90,
            ),
            nativefmt=dict(
                doc_visibility=footprints.doc.visibility.GURU,
            ),
            clscontents=dict(
                doc_visibility=footprints.doc.visibility.GURU,
            ),
        ),
    )

    def stdin_text(self, **opts):
        """Abstract method."""
        return None


class Script(Executable):
    """Basic interpreted executable associated to a specific language."""

    _footprint = dict(
        attr=dict(
            rawopts=dict(
                info="Options that will be passed directly to the script",
                optional=True,
                default="",
            ),
            language=dict(
                info="The programming language",
                values=["perl", "python", "ksh", "bash", "sh", "awk"],
            ),
            kind=dict(
                optional=True,
                default="script",
                values=["script"],
            ),
        ),
        fastkeys={"language"},
    )

    @property
    def realkind(self):
        return "script"

    def command_line(self, **opts):
        """Returns optional attribute :attr:`rawopts`."""
        if self.rawopts is None:
            return ""
        else:
            return self.rawopts


class GnuScript(Executable):
    """Basic interpreted executable with standard command line arguments."""

    _footprint = dict(
        attr=dict(
            language=dict(
                info="The programming language",
                values=["perl", "python", "ksh", "bash", "sh", "awk"],
            ),
            kind=dict(
                default="gnuscript",
                values=["gnuscript", "argscript"],
            ),
        ),
        fastkeys={"kind", "language"},
    )

    @property
    def realkind(self):
        return "script"

    def command_line(self, **opts):
        """Returns a blank separated list of options."""
        return " ".join(
            [
                "--" + k + " " + " ".join([str(x) for x in mktuple(v)])
                for k, v in opts.items()
            ]
        )


class Binary(Executable):
    """Basic compiled executable."""

    _abstract = True
    _footprint = dict(
        attr=dict(
            static=dict(
                info="Statically linked binary.",
                type=bool,
                optional=True,
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
            jacket=dict(
                type=Jacket,
                optional=True,
                default=Jacket(),
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
        )
    )

    @property
    def realkind(self):
        return "binary"

    def guess_binary_sources(self, provider):  # @UnusedVariable
        """A list of path that contains source files (for debugging purposes)."""
        return []


class BlackBox(Binary):
    """Binary resource with explicit command line options."""

    _footprint = dict(
        attr=dict(
            binopts=dict(
                info="Options that will be passed directly to the binary",
                optional=True,
                default="",
            ),
            kind=dict(
                values=["binbox", "blackbox"],
                remap=dict(binbox="blackbox"),
            ),
        )
    )

    def command_line(self, **opts):
        """Returns current attribute :attr:`binopts`."""
        return self.binopts


class NWPModel(Binary):
    """Base class for any Numerical Weather Prediction Model."""

    _abstract = True
    _footprint = [
        model_deco,
        dict(info="NWP Model", attr=dict(kind=dict(values=["nwpmodel"]))),
    ]

    @property
    def realkind(self):
        return "nwpmodel"

    def command_line(self, **opts):
        """Abstract method."""
        return ""


class OceanographicModel(Binary):
    """Base class for any Oceanographic Model."""

    _abstract = True
    _footprint = [
        model_deco,
        dict(
            info="Oceanographic Model",
            attr=dict(kind=dict(values=["oceanmodel"])),
        ),
    ]

    @property
    def realkind(self):
        return "oceanmodel"

    def command_line(self, **opts):
        """Abstract method."""
        return ""


class SurfaceModel(Binary):
    _abstract = True
    _footprint = [
        model_deco,
        dict(
            info="Model used for the Safran-Surfex-Mepra chain.",
            attr=dict(
                kind=dict(
                    values=["surfacemodel", "snowmodel"],
                    remap=dict(autoremap="first"),
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "surfacemodel"

    def command_line(self, **opts):
        """Abstract method."""
        return ""


class ChemistryModel(Binary):
    _abstract = True
    _footprint = [
        model_deco,
        dict(
            info="Base class for Chemistry models.",
            attr=dict(
                kind=dict(
                    values=["chemistrymodel"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "chemistrymodel"

    def command_line(self, **opts):
        """Abstract method."""
        return ""
