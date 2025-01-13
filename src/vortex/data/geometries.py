"""
This module contains the definition of all the Geometry objects widely in
Vortex's resources description. Geometry objects rely on the
:class:`bronx.patterns.getbytag.GetByTag` class.

When this module is first imported, pre-defined geometries are automatically
created using:

    * The ``geometries.ini`` file from the Vortex's distribution ``conf`` directory
    * The ``geometries.ini`` file located in the user's configuration directory
      (usually ``$HOME/.vortexrc``). (This file may be missing)

Additional Geometry objects can be manually created by the user provided that
the ``new=True`` argument is given to the desired class constructor (otherwise
an exception will be raised).

To retrieve and browse an already defined geometry, please use the module's
interface methods, :func:`get`, :func:`keys`, :func:`values` and :func:`items`::

    >>> from vortex.data import geometries
    >>> print(geometries.get(tag="global798"))
    <vortex.data.geometries.GaussGeometry | tag='global798' id='ARPEGE TL798 stretched-rotated geometry' tl=798 c=2.4>

It is also possible to retrieve an existing geometry using the :class:`Geometry`
class constructor::

    >>> print(geometries.Geometry("global798"))
    <vortex.data.geometries.GaussGeometry | tag='global798' id='ARPEGE TL798 stretched-rotated geometry' tl=798 c=2.4>

To build a new geometry, you need to pick the concrete geometry class that fits
your needs. Currently available concrete geometries are:

    * :class:`GaussGeometry` (Global gaussian grid)
    * :class:`ProjectedGeometry` (Any grid defined by a geographical projection, e.g. lambert, ...)
    * :class:`LonlatGeometry` (That's pretty obvious)
    * :class:`CurvlinearGeometry` (Curvlinear grid)

For example, let's build a new gaussian grid::

    >>> geometries.GaussGeometry(tag='global2198',  # The geometry's nickname #doctest: +ELLIPSIS
    ...                          info='My own gaussian geometry',
    ...                          truncation=2198,  # The linear truncation
    ...                          stretching=2.1, area='France',  # 2.1 stretching over France
    ...                          new=True)  # Mandatory to create new geometries
    <vortex.data.geometries.GaussGeometry (tag='global2198') object at 0x...>
    >>> print(geometries.Geometry("global2198"))
    <vortex.data.geometries.GaussGeometry | tag='global2198' id='My own gaussian geometry' tl=2198 c=2.1>

(From that moment on, the new geometry is available globally in Vortex)

Each geometry has its own attributes: please refers to each of the concrete
class documentation for more details.
"""

import configparser
import importlib.resources
import re

from bronx.fancies import loggers
import bronx.patterns.getbytag

import footprints

from vortex.syntax.stddeco import namebuilding_insert, generic_pathname_insert

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


# Module Interface


def get(**kw):
    """Return actual geometry object matching description.

    :param str tag: The name of the wanted geometry
    """
    return Geometry(**kw)


def keys():
    """Return the list of current names of geometries collected."""
    return Geometry.tag_keys()


def values():
    """Return the list of current values of geometries collected."""
    return Geometry.tag_values()


def items():
    """Return the items of the geometries table."""
    return Geometry.tag_items()


def grep(**kw):
    """Grep items that match the set of attributes given as named arguments."""
    okmatch = list()
    for item in Geometry.tag_values():
        ok = True
        for k, v in kw.items():
            if not hasattr(item, k) or getattr(item, k) != v:
                ok = False
                break
        if ok:
            okmatch.append(item)
    return okmatch


# Abstract geometry classes


class Geometry(bronx.patterns.getbytag.GetByTag):
    """Abstract geometry."""

    _tag_implicit_new = False

    def __init__(self, **kw):
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
            the first positional attribute is considered to be the tag name)
        :param str info: A free description of the geometry

        .. note:: This is an abstract class, do not instantiate.
        """
        self.info = "anonymous"
        self.inifile = None
        self.__dict__.update(kw)
        self.kind = "abstract"
        self._init_attributes = {k: v for k, v in kw.items() if v is not None}
        logger.debug("Abstract Geometry init kw=%s", str(kw))

    @classmethod
    def _tag_implicit_new_error(cls, tag):
        """Called whenever a tag does not exists and _tag_implicit_new = False."""
        raise RuntimeError(
            'The "{:s}" {:s} object does not exist yet...'.format(
                tag, cls.__name__
            )
        )

    @classmethod
    def tag_clean(self, tag):
        """Geometries id tags are lower case."""
        return tag.lower()

    def __repr__(self):
        """Nicer represenation for geometries."""
        return "<{:s}.{:s} (tag='{:s}') object at {:#x}>".format(
            self.__module__, self.__class__.__name__, self.tag, id(self)
        )

    def export_dict(self):
        return self.tag

    def doc_export(self):
        """Relevant informations to print in the documentation."""
        return "kind={:s}".format(self.kind)

    def to_inifile(self):
        """Format geometry to put in the inifile."""
        self._init_attributes.update(kind=self.kind)
        s = "[{}]\n".format(self.tag)
        for k in sorted(self._init_attributes.keys()):
            s += "{:10s} = {}\n".format(k, self._init_attributes[k])
        return s


class VerticalGeometry(Geometry):
    """Handle vertical geometry description (not used at the present time)."""

    _tag_topcls = False

    def __init__(self, **kw):
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
            the first positional attribute is considered to be the tag name)
        :param str info: A free description of the geometry

        .. note:: This is an abstract class, do not instantiate.
        """
        super().__init__(**kw)
        self.kind = "vertical"
        logger.debug(
            "Abstract Vertical Geometry init %s %s", str(self), str(kw)
        )


class HorizontalGeometry(Geometry):
    """Handle abstract horizontal geometry description."""

    _tag_topcls = False

    def __init__(self, **kw):
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
            the first positional attribute is considered to be the tag name)
        :param str info: A free description of the geometry
        :param bool lam: Is it a limited area geometry (as opposed to global)

        .. note:: This is an abstract class, do not instantiate.
        """
        desc = dict(
            info="anonymous",
            gridtype=None,
            area=None,
            nlon=None,
            nlonmax=None,
            nlat=None,
            ni=None,
            nj=None,
            resolution=0.0,
            expected_resolution=0.0,
            runit=None,
            truncation=None,
            truncationtype=None,
            stretching=None,
            nmassif=None,
            nposts=None,
            lam=True,
            lonmin=None,
            latmin=None,
        )
        desc.update(kw)
        super().__init__(**desc)
        for k, v in self.__dict__.items():
            if isinstance(v, str) and re.match("none", v, re.IGNORECASE):
                self.__dict__[k] = None
            if isinstance(v, str) and re.match("true", v, re.IGNORECASE):
                self.__dict__[k] = True
            if isinstance(v, str) and re.match("false", v, re.IGNORECASE):
                self.__dict__[k] = False
        for item in (
            "nlon",
            "nlat",
            "ni",
            "nj",
            "nmassif",
            "nposts",
            "truncation",
        ):
            cv = getattr(self, item)
            if cv is not None:
                setattr(self, item, int(cv))
        for item in ("stretching", "resolution", "lonmin", "latmin"):
            cv = getattr(self, item)
            if cv is not None:
                setattr(self, item, float(cv))
        self._check_attributes()
        logger.debug("Abstract Horizontal Geometry init %s", str(self))

    def _check_attributes(self):
        if self.lam and (self.area is None):
            raise AttributeError("Some mandatory arguments are missing")

    @property
    def gam(self):
        """Is it a global geometry ?"""
        return not self.lam

    @property
    def rnice(self):
        """Returns a string with a nice representation of the resolution (if sensible)."""
        if self.runit is not None:
            if self.runit == "km":
                res = "{:05.2f}".format(self.resolution)
            elif self.runit in ("s", "min"):
                res = "{:04.1f}".format(self.resolution)
            else:
                res = "{:06.3f}".format(self.resolution)
            return re.sub(r"\.", self.runit, res, 1)
        else:
            return "Unknown Resolution"

    @property
    def rnice_u(self):
        return self.rnice.upper()

    @property
    def gco_grid_def(self):
        return (
            "{0.area}" + ("_{0.rnice}" if self.runit is not None else "")
        ).format(self)

    def anonymous_info(self, *args):  # @UnusedVariable
        """Try to build a meaningful information from an anonymous geometry."""
        return "{!s}, {:s}".format(self.area, self.rnice)

    def __str__(self):
        """Very short presentation."""
        if self.info == "anonymous":
            return "{:s}({:s})".format(
                self.__class__.__name__, self.anonymous_info()
            )
        else:
            return self.info

    def idcard(self, indent=2):
        """
        Returns a multilines documentation string with a summary
        of the valuable information contained by this geometry.
        """
        indent = " " * indent
        # Basics...
        card = "\n".join(
            (
                "{0}Geometry {1!r}",
                "{0}{0}Info       : {2:s}",
                "{0}{0}LAM        : {3!s}",
            )
        ).format(indent, self, self.info, self.lam)
        # Optional infos
        for attr in [
            k
            for k in (
                "area",
                "resolution",
                "truncation",
                "stretching",
                "nlon",
                "nlat",
                "ni",
                "nj",
                "nmassif",
                "nposts",
            )
            if getattr(self, k, False)
        ]:
            card += "\n{0}{0}{1:10s} : {2!s}".format(
                indent, attr.title(), getattr(self, attr)
            )
        return card

    def strheader(self):
        """Return the beginning of the formatted print representation."""
        header = "{:s}.{:s} | tag='{}' id='{:s}'".format(
            self.__module__,
            self.__class__.__name__,
            self.tag,
            self.info,
        )
        if self.lam:
            header += " area='{:s}'".format(self.area)
        return header

    @property
    def coordinates(self):
        if any(
            [
                getattr(self, x) is None
                for x in ("lonmin", "latmin", "nlat", "nlon", "resolution")
            ]
        ):
            return dict()
        coordinates = dict(lonmin=self.lonmin, latmin=self.latmin)
        coordinates["latmax"] = self.latmin + self.resolution * (self.nlat - 1)
        coordinates["lonmax"] = self.lonmin + self.resolution * (self.nlon - 1)
        return coordinates


class SpectralAwareHorizontalGeometry(HorizontalGeometry):
    """Additional check and support for the **truncationtype** attribute."""

    _tag_topcls = False

    def _check_attributes(self):
        super()._check_attributes()
        if self.truncationtype is None:
            self.truncationtype = "linear"
        if self.truncationtype not in ("linear", "quadratic", "cubic"):
            raise ValueError(
                "Improper value {:s} for *truncationtype*".format(
                    self.truncationtype
                )
            )

    @property
    def short_truncationtype(self):
        return self.truncationtype[0]

    @property
    def xtruncationtype(self):
        return dict(quadratic="quad").get(
            self.truncationtype, self.truncationtype
        )


# Combined geometry (not used at the present time)


class CombinedGeometry(Geometry):
    """Combine horizontal and vertical geometry (not used at the present time)."""

    _tag_topcls = False

    def __init__(self, **kw):
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
            the first positional attribute is considered to be the tag name)
        :param str info: A free description of the geometry
        :param HorizontalGeometry hgeo: An horizontal geometry
        :param VerticalGeometry vgeo: A vertical geometry
        """
        self.hgeo = None
        self.vgeo = None
        super().__init__(**kw)
        self.kind = "combined"
        logger.debug("Combined Geometry init %s %s", str(self), str(kw))


# Concrete geometry classes


class GaussGeometry(SpectralAwareHorizontalGeometry):
    """
    Gaussian grid (stretched or not, rotated or not) associated with a spectral
    represention.
    """

    _tag_topcls = False

    def __init__(self, **kw):
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
            the first positional attribute is considered to be the tag name)
        :param str info: A free description of the geometry
        :param int truncation: The linear truncation
        :param float stretching: The stretching factor (1. for an unstretched grid)
        :param str truncationtype: The method used to compute the spectral representation
            (linear, quadratic or cubic).
        :param str gridtype: The type of the gaussian grid (rgrid: the default
            method used at Meteo-France until now, octahedral)
        :param str area: The location of the pole of interest (when stretching > 1.)

        .. note:: Gaussian grids are always global grids.
        """
        super().__init__(**kw)
        self.kind = "gauss"
        logger.debug("Gauss Geometry init %s", str(self))

    def _check_attributes(self):
        self.lam = False  # Always false for gaussian grid
        super()._check_attributes()
        if self.truncation is None or self.stretching is None:
            raise AttributeError("Some mandatory arguments are missing")
        if self.gridtype is None:
            self.gridtype = "rgrid"
        if self.gridtype not in ("rgrid", "octahedral"):
            raise ValueError(
                "Improper value {:s} for *gridtype*".format(self.gridtype)
            )

    @property
    def short_gridtype(self):
        return self.gridtype[0] if self.gridtype != "rgrid" else ""

    @property
    def gco_grid_def(self):
        geotag_f = "t"
        if self.truncationtype != "linear" or self.gridtype != "rgrid":
            geotag_f += "{0.short_truncationtype}"
        geotag_f += "{0.short_gridtype}{0.truncation:d}"
        return geotag_f.format(self)

    def __str__(self):
        """Standard formatted print representation."""
        return "<{:s} t{:s}{:s}={:d} c={:g}>".format(
            self.strheader(),
            self.short_truncationtype,
            self.short_gridtype,
            self.truncation,
            self.stretching,
        )

    def doc_export(self):
        """Relevant informations to print in the documentation."""
        if self.stretching > 1:
            fmts = "kind={0:s}, t{1:s}{2:s}={3:d}, c={4:g} (pole of interest over {5!s})"
        else:
            fmts = "kind={0:s}, t{1:s}{2:s}={3:d}, c={4:g}"
        return fmts.format(
            self.kind,
            self.short_truncationtype,
            self.short_gridtype,
            self.truncation,
            self.stretching,
            self.area,
        )


class ProjectedGeometry(SpectralAwareHorizontalGeometry):
    """Geometry defined by a geographical projection on a plane."""

    _tag_topcls = False

    def __init__(self, **kw):
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
            the first positional attribute is considered to be the tag name)
        :param str info: A free description of the geometry
        :param bool lam: Is it a limited area grid (*True* by default)
        :param int|float resolution: The grid's resolution
        :param str runit: The unit of the resolution (km, ...) (km by default)
        :param str area: The grid location (needed if **lam** is *True*)
        """
        kw.setdefault("runit", "km")
        super().__init__(**kw)
        self.kind = "projected"
        logger.debug("Projected Geometry init %s", str(self))

    def _check_attributes(self):
        super()._check_attributes()
        if self.resolution is None:
            raise AttributeError("Some mandatory arguments are missing")

    @property
    def gco_grid_def(self):
        geotag_f = (
            "{0.area}_{0.rnice}"
            if self.truncationtype == "linear"
            else "{0.area}_{0.xtruncationtype}_{0.rnice}"
        )
        return geotag_f.format(self)

    def __str__(self):
        """Standard formatted print representation."""
        return "<{:s} r='{:s}' {:s}>".format(
            self.strheader(), self.rnice, self.truncationtype
        )

    def doc_export(self):
        """Relevant informations to print in the documentation."""
        if self.lam:
            fmts = (
                "kind={0:s}, r={1:s}, truncationtype={2:s}, limited-area={3:s}"
            )
        else:
            fmts = "kind={0:s}, r={1:s}, truncationtype={2:s}, global"
        return fmts.format(
            self.kind, self.rnice, self.truncationtype, self.area
        )


class LonlatGeometry(HorizontalGeometry):
    """Geometry defined by a geographical projection on plane."""

    _tag_topcls = False

    def __init__(self, **kw):
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
            the first positional attribute is considered to be the tag name)
        :param str info: A free description of the geometry
        :param bool lam: Is it a limited area grid (*True* by default)
        :param int|float resolution: The grid's resolution
        :param str runit: The unit of the resolution (deg, ...) (deg by default)
        :param int nlon: The number of longitude points in the grid
        :param int nlat: The number of latitude points in the grid
        :param str area: The grid location (needed if **lam** is *True*)
        """
        kw.setdefault("runit", "dg")
        super().__init__(**kw)
        self.kind = "lonlat"
        # TODO: coherence entre les coordonnees et nlon/nlat/resolution
        logger.debug("Lon/Lat Geometry init %s", str(self))

    def __str__(self):
        """Standard formatted print representation."""
        return "<{:s} r='{:s}'>".format(self.strheader(), self.rnice)

    def doc_export(self):
        """Relevant informations to print in the documentation."""
        if self.lam:
            fmts = "kind={0:s}, r={1:s}, limited-area={2:s}, nlon={3!s}, nlat={4!s}"
        else:
            fmts = "kind={0:s}, r={1:s}, global, nlon={3!s}, nlat={4!s}"
        return fmts.format(
            self.kind, self.rnice, self.area, self.nlon, self.nlat
        )


class UnstructuredGeometry(HorizontalGeometry):
    """Unstructured grid (curvlinear, finite-elements, ...)."""

    _tag_topcls = False

    def __init__(self, *args, **kw):  # @UnusedVariable
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
            the first positional attribute is considered to be the tag name)
        :param str info: A free description of the geometry
        :param bool lam: Is it a limited area geometry (as opposed to global)

        .. note:: This is an abstract class, do not instantiate.
        """
        super().__init__(**kw)
        self.kind = "unstructured"
        logger.debug("Unstructured Geometry init %s", str(self))

    def __str__(self):
        """Standard formatted print representation."""
        return "<{:s}>".format(self.strheader())

    def doc_export(self):
        """Relevant informations to print in the documentation."""
        if self.area:
            fmts = "kind={0:s}, area={1:s}"
        else:
            fmts = "kind={0:s}"
        return fmts.format(self.kind, self.area)


class CurvlinearGeometry(UnstructuredGeometry):
    """Curvlinear grid."""

    _tag_topcls = False

    def __init__(self, *args, **kw):  # @UnusedVariable
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
            the first positional attribute is considered to be the tag name)
        :param str info: A free description of the geometry
        :param bool lam: Is it a limited area grid (*True* by default)
        :param int ni: The number of longitude points in the grid
        :param int nj: The number of latitude points in the grid
        :param str area: The grid location (needed if **lam** is *True*)
        """
        super().__init__(**kw)
        self.kind = "curvlinear"

    def _check_attributes(self):
        super()._check_attributes()
        if self.ni is None or self.nj is None:
            raise AttributeError("Some mandatory arguments are missing")

    def doc_export(self):
        """Relevant informations to print in the documentation."""
        if self.lam:
            fmts = (
                "kind={0:s}, r={1:s}, limited-area={2:s}, ni={3!s}, nj={4!s}"
            )
        else:
            fmts = "kind={0:s}, r={1:s}, global, ni={3!s}, nj={4!s}"
        return fmts.format(
            self.kind, self.rnice, self.area, self.nlon, self.nlat
        )


class RedgridGeometry(HorizontalGeometry):
    """Spherical or LAM reduced grid (the number of longitude decreases toward the pole)."""

    _tag_topcls = False

    def __init__(self, **kw):
        """
        :param str tag: The geometry's name (if no **tag** attributes is provided,
                        the first positional attribute is considered to be the tag
                        name)
        :param str info: A free description of the geometry
        :param int nlonmax: Maximum number of longitude points in the grid
        :param int nlat: Number of latitude points in the grid
        :param int expected_resolution: the real resolution for
                                        ``longitudes = expected_resolution * cos(lat)``
        :param str area: The grid location (needed if **lam** is *True*)
        """
        kw.setdefault("runit", "dg")
        kw.setdefault("lam", False)
        super().__init__(**kw)
        self.kind = "redgrid"

    def _check_attributes(self):
        if (
            self.nlonmax is None
            or self.nlat is None
            or self.resolution is None
        ):
            raise AttributeError("Some mandatory arguments are missing")
        super()._check_attributes()
        if self.lam is False:
            self.area = "global"

    def __str__(self):
        """Standard formatted print representation."""
        return "<{:s} area='{:s}' r='{:s}'>".format(
            self.strheader(), self.area, self.rnice
        )

    def doc_export(self):
        """Relevant informations to print in the documentation."""
        fmts = "kind={0:s}, r={1:s}, area={2:s}, nlonmax={3!s}, nlat={4!s}"
        return fmts.format(
            self.kind, self.rnice, self.area, self.nlonmax, self.nlat
        )


# Pre-defined footprint attribute for any HorizontalGeometry

#: Usual definition of the ``geometry`` attribute.
a_hgeometry = dict(
    info="The resource's horizontal geometry.",
    type=HorizontalGeometry,
)


def _add_geo2basename_info(cls):
    """Decorator that adds a _geo2basename_info to a class."""

    def _geo2basename_info(self, add_stretching=True):
        """Return an array describing the geometry for the Vortex's name builder."""
        if isinstance(self.geometry, GaussGeometry):
            lgeo = [
                {
                    "truncation": (
                        self.geometry.truncation,
                        self.geometry.short_truncationtype,
                        self.geometry.short_gridtype,
                    )
                },
            ]
            if add_stretching:
                lgeo.append({"stretching": self.geometry.stretching})
        elif isinstance(self.geometry, (ProjectedGeometry, RedgridGeometry)):
            lgeo = [self.geometry.area, self.geometry.rnice]
            if (
                self.geometry.truncationtype is not None
                and self.geometry.truncationtype != "linear"
            ):
                lgeo.append(self.geometry.xtruncationtype)
        else:
            lgeo = self.geometry.area  # Default: always defined
        return lgeo

    if not hasattr(cls, "_geo2basename_info"):
        cls._geo2basename_info = _geo2basename_info
    return cls


#: Abstract footprint definition of the ``geometry`` attribute.
hgeometry = footprints.Footprint(
    info="Abstract Horizontal Geometry", attr=dict(geometry=a_hgeometry)
)

#: Abstract footprint definition of the ``geometry`` attribute with decorators
#: that alter the ``namebuilding_info`` method
hgeometry_deco = footprints.DecorativeFootprint(
    hgeometry,
    decorator=[
        _add_geo2basename_info,
        namebuilding_insert("geo", lambda self: self._geo2basename_info()),
        generic_pathname_insert(
            "geometry", lambda self: self.geometry, setdefault=True
        ),
    ],
)


# Load default geometries when the module is first imported


def load(inifile="@geometries.ini", refresh=False, verbose=True):
    """Load a set of pre-defined geometries from a configuration file.

    The class that will be instantiated depends on the "kind" keyword..
    """
    iniconf = configparser.ConfigParser()
    with importlib.resources.open_text(
        "vortex.data",
        "geometries.ini",
    ) as fh:
        iniconf.read_file(fh)
    for item in iniconf.sections():
        gdesc = dict(iniconf.items(item))
        gkind = gdesc.get("kind")
        try:
            thisclass = [
                x
                for x in Geometry.tag_classes()
                if x.__name__.lower().startswith(gkind.lower())
            ].pop()
        except IndexError:
            raise AttributeError(
                "Kind={:s} is unknown (for geometry [{:s}])".format(
                    gkind, item
                )
            )
        if verbose:
            print("+ Load", item.ljust(16), "as", thisclass)
        if refresh:
            # Always recreate the Geometry...
            thisclass(tag=item, new=True, **gdesc)
        else:
            # Only create new geometries
            if item not in Geometry.tag_keys():
                thisclass(tag=item, new=True, **gdesc)


load(verbose=False)
