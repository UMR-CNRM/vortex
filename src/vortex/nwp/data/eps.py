"""
Resources needed to build the Ensemble Prediction System.
"""

import copy

from bronx.fancies import loggers
import footprints

from bronx.stdtypes.date import Date, Time
from bronx.syntax.decorators import secure_getattr
from vortex.data.flow import FlowResource
from vortex.data.contents import JsonDictContent, TextContent
from vortex.syntax.stdattrs import number_deco
from vortex.syntax.stddeco import namebuilding_delete, namebuilding_insert
from .logs import use_flow_logs_stack
from .modelstates import Historic

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


@namebuilding_insert(
    "radical",
    lambda s: {"unit": "u", "normed": "n"}.get(s.processing, "") + s.realkind,
)
class PerturbedState(Historic):
    """
    Class for numbered historic resources, for example perturbations or perturbed states of the EPS.
    """

    _footprint = [
        number_deco,
        dict(
            info="Perturbation or perturbed state",
            attr=dict(
                kind=dict(
                    values=[
                        "perturbation",
                        "perturbed_historic",
                        "perturbed_state",
                        "pert",
                    ],
                    remap=dict(autoremap="first"),
                ),
                term=dict(optional=True, default=Time(0)),
                processing=dict(
                    values=["unit", "normed"],
                    optional=True,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "pert"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        raise NotImplementedError(
            "Perturbations were previously tar files, not supported yet."
        )

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        raise NotImplementedError(
            "Perturbations were previously tar files, not supported yet."
        )


@namebuilding_insert("radical", lambda s: s.realkind + "-" + s.zone)
class SingularVector(Historic):
    """
    Generic class for resources internal to singular vectors.
    """

    _footprint = [
        number_deco,
        dict(
            info="Singular vector",
            attr=dict(
                kind=dict(
                    values=["svector"],
                ),
                zone=dict(
                    values=[
                        "ateur",
                        "hnc",
                        "hs",
                        "pno",
                        "oise",
                        "an",
                        "pne",
                        "oiso",
                        "ps",
                        "oin",
                        "trop1",
                        "trop2",
                        "trop3",
                        "trop4",
                    ],
                ),
                term=dict(optional=True, default=Time(0)),
                optime=dict(
                    type=Time,
                    optional=True,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "svector"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "SVARPE" + "{:03d}".format(self.number) + "+0000"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "SVARPE" + "{:03d}".format(self.number) + "+0000"


@use_flow_logs_stack
class NormCoeff(FlowResource):
    """
    Coefficient used to normalize the singular vectors or the bred modes.
    """

    _footprint = dict(
        info="Perturbations coefficient",
        attr=dict(
            kind=dict(
                values=["coeffnorm", "coeffpert"],
                remap=dict(autoremap="first"),
            ),
            clscontents=dict(
                default=JsonDictContent,
            ),
            nativefmt=dict(
                values=["json"],
                default="json",
            ),
            pertkind=dict(
                values=["sv", "bd"],
                optional=True,
                default="sv",
            ),
        ),
    )

    @property
    def realkind(self):
        return "coeff" + self.pertkind


class SampleContent(JsonDictContent):
    """Specialisation of the JSONDictContent to deal with drawing lots."""

    def drawing(self, g, x):
        """Return the number of a sampled element according to the local number."""
        n = g.get("number", x.get("number", None))
        virgin = g.get(
            "untouched",
            x.get(
                "untouched",
                [
                    0,
                ],
            ),
        )
        if n is None:
            return None
        else:
            try:
                if not isinstance(virgin, list):
                    virgin = [int(virgin)]
                else:
                    virgin = map(int, virgin)
                n = int(n)
            except TypeError:
                return None
            if n in virgin:
                return n
            else:
                try:
                    return self.data["drawing"][n - 1]
                except KeyError:
                    return None

    @secure_getattr
    def __getattr__(self, attr):
        # Return an access function that corresponds to the key in "drawing"
        drawing_keys = {
            item
            for d in self.data.get("drawing", [])
            if isinstance(d, dict)
            for item in d.keys()
        }
        if attr in drawing_keys:

            def _attr_access(g, x):
                elt = self.drawing(g, x)
                # drawing may returns
                # * None (if the 'number' attribute is incorrect or missing)
                # * An integer if 'number' is in the 'untouched' list
                # * A dictionary
                if elt is None:
                    choices = {d[attr] for d in self.data["drawing"]}
                    return None if len(choices) > 1 else choices.pop()
                else:
                    return elt[attr] if isinstance(elt, dict) else None

            return _attr_access
        # Return an access function that corresponds to the key in "population"
        population_keys = {
            item
            for d in self.data.get("population", [])
            if isinstance(d, dict)
            for item in d.keys()
        }
        if attr in population_keys:

            def _attr_access(g, x):
                n = g.get("number", x.get("number", None))
                if n is None:
                    return None
                else:
                    return self.data["population"][n - 1][attr]

            return _attr_access
        # Returns the list of drawn keys
        listing_keys = {
            item + "s"
            for d in self.data.get("drawing", [])
            if isinstance(d, dict)
            for item in d.keys()
        }
        if attr in listing_keys:
            return [d[attr[:-1]] for d in self.data["drawing"]]
        # Return the list of available keys
        listing_keys = {
            item + "s"
            for d in self.data["population"]
            if isinstance(d, dict)
            for item in d.keys()
        }
        if attr in listing_keys:
            return [d[attr[:-1]] for d in self.data["population"]]
        raise AttributeError()

    def targetdate(self, g, x):
        targetdate = g.get("targetdate", x.get("targetdate", None))
        if targetdate is None:
            raise ValueError(
                "A targetdate attribute must be present if targetdate is used"
            )
        return Date(targetdate)

    def targetterm(self, g, x):
        targetterm = g.get("targetterm", x.get("targetterm", None))
        if targetterm is None:
            raise ValueError(
                "A targetterm attribute must be present if targetterm is used"
            )
        return Time(targetterm)

    def timedelta(self, g, x):
        """Find the time difference between the resource's date and the targetdate."""
        targetterm = Time(g.get("targetterm", x.get("targetterm", 0)))
        thedate = Date(self.date(g, x))
        period = (self.targetdate(g, x) + targetterm) - thedate
        return period.time()

    def _actual_diff(self, ref):
        me = copy.copy(self.data)
        other = copy.copy(ref.data)
        me.pop(
            "experiment", None
        )  # Do not compare the experiment ID (if present)
        other.pop("experiment", None)
        return me == other


@use_flow_logs_stack
@namebuilding_delete("src")
class PopulationList(FlowResource):
    """
    Description of available data
    """

    _abstract = True
    _footprint = dict(
        info="A Population List",
        attr=dict(
            clscontents=dict(
                default=SampleContent,
            ),
            nativefmt=dict(
                values=["json"],
                default="json",
            ),
            nbsample=dict(
                optional=True,
                type=int,
            ),
            checkrole=dict(optional=True),
        ),
    )


class MembersPopulation(PopulationList):
    _footprint = dict(
        info="Members population",
        attr=dict(
            kind=dict(
                values=[
                    "mbpopulation",
                ],
            ),
        ),
    )

    @property
    def realkind(self):
        return "mbpopulation"


@namebuilding_insert(
    "radical", lambda s: "{:s}of{:d}".format(s.realkind, s.nbsample)
)
class Sample(PopulationList):
    """
    Lot drawn out of a set.
    """

    _abstract = (True,)
    _footprint = dict(
        info="Sample",
        attr=dict(
            nbsample=dict(
                optional=False,
            ),
            population=dict(type=footprints.stdtypes.FPList, optional=True),
        ),
    )


class MembersSample(Sample):
    """
    List of members selected among a set.
    """

    _footprint = dict(
        info="Members sample",
        attr=dict(
            kind=dict(
                values=["mbsample", "mbselect", "mbdrawing", "members_select"],
                remap=dict(autoremap="first"),
            ),
        ),
    )

    @property
    def realkind(self):
        return "mbsample"


class MultiphysicsSample(Sample):
    """
    List of physical packages selected among a set.
    """

    _footprint = dict(
        info="Physical packages sample",
        attr=dict(
            kind=dict(
                values=["physample", "physelect", "phydrawing"],
                remap=dict(autoremap="first"),
            ),
        ),
    )

    @property
    def realkind(self):
        return "physample"


class ClustContent(TextContent):
    """Specialisation of the TextContent to deal with clustering outputs."""

    def getNumber(self, idx):
        return self.data[idx - 1]


@use_flow_logs_stack
@namebuilding_delete("src")
class GeneralCluster(FlowResource):
    """
    Files produced by the clustering step of the LAM PE.
    """

    _footprint = dict(
        info="Clustering stuff",
        attr=dict(
            kind=dict(
                values=["clustering", "clust", "members_select"],
                remap=dict(autoremap="first"),
            ),
            clscontents=dict(
                default=ClustContent,
            ),
            nativefmt=dict(
                values=["ascii", "txt"],
                default="txt",
                remap=dict(ascii="txt"),
            ),
            filling=dict(
                values=["population", "pop", "members", "full"],
                remap=dict(population="pop"),
                default="",
            ),
        ),
    )

    @property
    def realkind(self):
        return "clustering" + "_" + self.filling
