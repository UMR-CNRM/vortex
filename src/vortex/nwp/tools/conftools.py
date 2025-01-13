"""
Conftools are small objects that can be instantiated from an application's
configuration file.

They might be used when some complex calculations are needed to establish the
tasks configuration.
"""

import collections
import collections.abc
import functools
import math
import re

from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Time, Period, Month, timeintrangex
from bronx.syntax.decorators import secure_getattr
from footprints.stdtypes import FPDict, FPList
from footprints.util import rangex
import footprints

from ..tools.odb import TimeSlots

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class ConfTool(footprints.FootprintBase):
    """Abstract class for conftools objects."""

    _abstract = True
    _collector = ("conftool",)
    _footprint = dict(
        info="Abstract Conf/Weird Tool",
        attr=dict(
            kind=dict(),
        ),
    )


class AbstractObjectProxyConfTool(ConfTool):
    """Allow transparent access to any Vortex object."""

    _abstract = True
    _footprint = dict(
        info="Conf tool that find the appropriate begin/end date for an input resource.",
        attr=dict(
            kind=dict(
                values=[
                    "objproxy",
                ],
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._proxied_obj = self._create_proxied_obj()

    def _create_proxied_obj(self):
        """Initialise the object that will be proxied."""
        raise NotImplementedError()

    @secure_getattr
    def __getattr__(self, item):
        """Pass all requests to the proxied object."""
        target = getattr(self._proxied_obj, item, None)
        if target is None:
            raise AttributeError('Attribute "{:s}" was not found'.format(item))
        else:
            return target


#: Holds coupling's data for a particular cutoff/hour
CouplingInfos = collections.namedtuple(
    "CouplingInfos",
    ("base", "dayoff", "cutoff", "vapp", "vconf", "xpid", "model", "steps"),
)


class CouplingOffsetConfError(Exception):
    """Abstract exception raise by :class:`CouplingOffsetConfTool` objects."""

    pass


class CouplingOffsetConfPrepareError(CouplingOffsetConfError):
    """Exception raised when an error occurs during coupling data calculations."""

    def __init__(self, fmtk):
        msg = "It is useless to compute coupling for: {}.".format(fmtk)
        super().__init__(msg)


class CouplingOffsetConfRefillError(CouplingOffsetConfError):
    """Exception raised when an orror occurs during refill."""

    def __init__(self, fmtk, hh=None):
        msg = "It is useless to compute a refill for: {}".format(fmtk)
        if hh is None:
            msg += "."
        else:
            msg += " at HH={!s}.".format(hh)
        super().__init__(msg)


class CouplingOffsetConfTool(ConfTool):
    """Conf tool that do all sorts of computations for coupling."""

    _footprint = dict(
        info="Conf tool that do all sorts of computations for coupling",
        attr=dict(
            kind=dict(
                values=[
                    "couplingoffset",
                ],
            ),
            cplhhlist=dict(
                info=(
                    "The list of cutoff and hours for this application. "
                    "If omitted, all entries of the **cplhhbase** attribute are used. "
                    + "(e.g ``{'assim':[0, 6, 12, 18], 'production':[0, ]}``)"
                ),
                type=FPDict,
                optional=True,
            ),
            cplhhbase=dict(
                info=(
                    "For a given cutoff and hour, gives the base hour to couple to. "
                    + "(e.g ``{'assim':{0:0, 6:6, 12:12, 18:18}, 'production':{0:18}}``)."
                ),
                type=FPDict,
            ),
            cpldayoff=dict(
                info=(
                    "For a given cutoff and hour, gives an offset in days. 0 by default. "
                    + "(e.g ``{'assim':{'default':0}, 'production':{'default':1}}``)."
                ),
                type=FPDict,
                optional=True,
            ),
            cplcutoff=dict(
                info="For a given cutoff and hour, gives the base cutoff to couple to.",
                type=FPDict,
            ),
            cplvapp=dict(
                info="For a given cutoff and hour, gives the base vapp to couple to.",
                type=FPDict,
            ),
            cplvconf=dict(
                info="For a given cutoff and hour, gives the base vconf to couple to.",
                type=FPDict,
            ),
            cplxpid=dict(
                info="For a given cutoff and hour, gives the experiment ID to couple to.",
                type=FPDict,
                optional=True,
            ),
            cplmodel=dict(
                info="For a given cutoff and hour, gives the base model to couple to.",
                type=FPDict,
                optional=True,
            ),
            cplsteps=dict(
                info="For a given cutoff and hour, gives then list of requested terms.",
                type=FPDict,
            ),
            finalterm=dict(
                info='For a given cutoff and hour, the final term (for "finalterm" token substitution)',
                type=FPDict,
                optional=True,
            ),
            refill_cutoff=dict(
                values=["assim", "production", "all"],
                info="By default, what is the cutoff name of the refill task.",
                optional=True,
                default="assim",
            ),
            compute_on_refill=dict(
                info="Is it necessary to compute coupling files for the refilling cutoff ?",
                optional=True,
                default=True,
                type=bool,
            ),
            isolated_refill=dict(
                info="Are the refill tasks exclusive with prepare tasks ?",
                optional=True,
                default=True,
                type=bool,
            ),
            verbose=dict(
                info="When the object is created, print a summary.",
                type=bool,
                optional=True,
                default=True,
            ),
        ),
    )

    _DFLT_KEY = "default"

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)

        # A dictionary summarising the base HH supported by this configuration tool
        # ex: dict(assim=set([0, 1 , 2, ...]), production=set([0, 6,...])
        self._target_hhs = collections.defaultdict(set)
        if self.cplhhlist is None:
            t_hhbase = collections.defaultdict(dict)
            for c, cv in self.cplhhbase.items():
                for h, v in [(Time(lh), Time(lv)) for lh, lv in cv.items()]:
                    t_hhbase[c][h] = v
                    self._target_hhs[c].add(h)
        else:
            for c, clist in self.cplhhlist.items():
                if not isinstance(clist, (tuple, list)):
                    clist = [
                        clist,
                    ]
                self._target_hhs[c].update([Time(h) for h in clist])
            t_hhbase = self._reshape_inputs(self.cplhhbase, value_reclass=Time)

        # Consistency checks and array reshaping
        t_dayoff = self._reshape_inputs(self.cpldayoff, class_default=0)
        t_cutoff = self._reshape_inputs(self.cplcutoff)
        t_vapp = self._reshape_inputs(self.cplvapp)
        t_vconf = self._reshape_inputs(self.cplvconf)
        t_steps = self._reshape_inputs(self.cplsteps)
        if self.cplmodel is None:
            t_model = t_vapp
        else:
            t_model = self._reshape_inputs(self.cplmodel)
        t_xpid = self._reshape_inputs(self.cplxpid, class_default="")

        # If relevent, do "finalterm" token substitution
        if self.finalterm is not None:
            t_finalterm = self._reshape_inputs(
                self.finalterm, value_reclass=str
            )
            for c, cv in t_hhbase.items():
                for hh in cv.keys():
                    if isinstance(t_steps[c][hh], str):
                        t_steps[c][hh] = t_steps[c][hh].replace(
                            "finalterm", t_finalterm[c][hh]
                        )

        # Build the dictionary of CouplingInfos objects
        self._cpl_data = collections.defaultdict(dict)
        for c, cv in t_hhbase.items():
            self._cpl_data[c] = {
                hh: CouplingInfos(
                    cv[hh],
                    int(t_dayoff[c][hh]),
                    t_cutoff[c][hh],
                    t_vapp[c][hh],
                    t_vconf[c][hh],
                    t_xpid[c][hh],
                    t_model[c][hh],
                    rangex(t_steps[c][hh]),
                )
                for hh in cv.keys()
            }

        # Pre-compute the prepare terms
        self._prepare_terms_map = self._compute_prepare_terms()
        if self.verbose:
            print()
            print("#### Coupling configuration tool initialised ####")
            print("**** Coupling tasks terms map:")
            print(
                "{:s}  :  {:s}".format(
                    self._cpl_fmtkey(
                        ("HH", "VAPP", "VCONF", "XPID", "MODEL", "CUTOFF")
                    ),
                    "Computed Terms",
                )
            )
            for k in sorted(self._prepare_terms_map.keys()):
                print(
                    "{:s}  :  {:s}".format(
                        self._cpl_fmtkey(k),
                        " ".join(
                            [str(t.hour) for t in self._prepare_terms_map[k]]
                        ),
                    )
                )

        # Pre-compute the default refill_map
        self._refill_terms_map = dict()
        self._refill_terms_map[self.refill_cutoff] = (
            self._compute_refill_terms(
                self.refill_cutoff,
                self.compute_on_refill,
                self.isolated_refill,
            )
        )
        if self.verbose:
            print(
                "**** Refill tasks activation map (default refill_cutoff is: {:s}):".format(
                    self.refill_cutoff
                )
            )
            print(
                "{:s}  :  {:s}".format(
                    self._rtask_fmtkey(
                        ("VAPP", "VCONF", "XPID", "MODEL", "CUTOFF")
                    ),
                    "Active hours",
                )
            )
            for k in sorted(self._refill_terms_map[self.refill_cutoff].keys()):
                vdict = self._refill_terms_map[self.refill_cutoff][k]
                print(
                    "{:s}  :  {:s}".format(
                        self._rtask_fmtkey(k),
                        " ".join([str(t.hour) for t in sorted(vdict.keys())]),
                    )
                )
            print()

    @property
    def target_hhs(self):
        return self._target_hhs

    def _reshape_inputs(
        self, input_dict, class_default=None, value_reclass=lambda x: x
    ):
        """Deal with default values, check dictionaries and convert keys to Time objects."""
        # Convert keys to time objects
        r_dict = dict()
        if input_dict is not None:
            for c, cv in input_dict.items():
                if isinstance(cv, dict):
                    r_dict[c] = dict()
                    for h, v in cv.items():
                        if h != self._DFLT_KEY:
                            r_dict[c][Time(h)] = value_reclass(v)
                        else:
                            r_dict[c][h] = value_reclass(v)
                else:
                    r_dict[c] = cv

        # Is there a generic default ?
        defined_topdefault = self._DFLT_KEY in r_dict
        top_default = r_dict.pop(self._DFLT_KEY, class_default)

        # Check consistency and replace missing values with defaults
        for c in self.target_hhs:
            myv = r_dict.setdefault(c, dict())
            # Is there a cutoff specific default ?
            defined_cutdefault = defined_topdefault or self._DFLT_KEY in myv
            last_default = myv.pop(self._DFLT_KEY, top_default)
            my_c_hhs = set(myv.keys())
            if defined_cutdefault or (class_default is not None):
                missinghh = self.target_hhs[c] - my_c_hhs
                for h in missinghh:
                    myv[h] = last_default
            else:
                if not my_c_hhs >= self.target_hhs[c]:
                    logger.error(
                        "Inconsistent input arrays while processing: \n%s",
                        str(input_dict),
                    )
                    logger.error(
                        "Cutoff %s, expecting the following HH: \n%s",
                        c,
                        str(self.target_hhs[c]),
                    )
                    raise ValueError("Inconsistent input array.")

        # Filter values according to _target_hhs
        for c in list(r_dict.keys()):
            if c not in self.target_hhs:
                del r_dict[c]
        for c in self.target_hhs:
            my_c_hhs = set(r_dict[c].keys())
            extra = my_c_hhs - self.target_hhs[c]
            for hh in extra:
                del r_dict[c][hh]

        return r_dict

    @staticmethod
    def _cpl_key(hh, cutoff, vapp, vconf, xpid, model):
        return (str(hh), vapp, vconf, xpid, model, cutoff)

    @staticmethod
    def _cpl_fmtkey(k):
        cutoff_map = dict(production="prod")
        return "{:5s} {:6s}  {:24s} {:s} ({:s})".format(
            k[0], cutoff_map.get(k[5], k[5]), k[1] + "/" + k[2], k[3], k[4]
        )

    @staticmethod
    def _rtask_key(cutoff, vapp, vconf, xpid, model):
        return (vapp, vconf, xpid, model, cutoff)

    @staticmethod
    def _rtask_fmtkey(k):
        cutoff_map = dict(production="prod")
        return "{:6s}  {:24s} {:s} ({:s})".format(
            cutoff_map.get(k[4], k[4]), k[0] + "/" + k[1], k[2], k[3]
        )

    @staticmethod
    def _process_date(date):
        mydate = Date(date)
        myhh = Time("{0.hour:d}:{0.minute:02d}".format(mydate))
        return mydate, myhh

    @staticmethod
    def _hh_offset(hh, hhbase, dayoff):
        offset = hh - hhbase
        if offset < 0:
            offset += Time(24)
        return offset + Period(days=dayoff)

    def _compute_prepare_terms(self):
        terms_map = collections.defaultdict(set)
        for _, cv in self._cpl_data.items():
            for h, infos in cv.items():
                key = self._cpl_key(
                    infos.base,
                    infos.cutoff,
                    infos.vapp,
                    infos.vconf,
                    infos.xpid,
                    infos.model,
                )
                targetoffset = self._hh_offset(h, infos.base, infos.dayoff)
                terms_map[key].update([s + targetoffset for s in infos.steps])
        terms_map = {k: sorted(terms) for k, terms in terms_map.items()}
        return terms_map

    def _compute_refill_terms(
        self, refill_cutoff, compute_on_refill, isolated_refill
    ):
        finaldates = collections.defaultdict(
            functools.partial(
                collections.defaultdict,
                functools.partial(collections.defaultdict, set),
            )
        )
        if refill_cutoff == "all":
            possiblehours = sorted(
                functools.reduce(
                    lambda x, y: x | y,
                    [set(l) for l in self.target_hhs.values()],
                )
            )
        else:
            possiblehours = self.target_hhs[refill_cutoff]

        # Look 24hr ahead
        for c, cv in self._cpl_data.items():
            for h, infos in cv.items():
                key = self._rtask_key(
                    infos.cutoff,
                    infos.vapp,
                    infos.vconf,
                    infos.xpid,
                    infos.model,
                )
                offset = self._hh_offset(h, infos.base, infos.dayoff)
                for possibleh in possiblehours:
                    roffset = self._hh_offset(h, possibleh, 0)
                    if (
                        roffset > 0
                        or (
                            compute_on_refill
                            and roffset == 0
                            and (refill_cutoff == "all" or refill_cutoff == c)
                        )
                    ) and (
                        roffset < offset
                        or (isolated_refill and roffset == offset)
                    ):
                        finaldates[key][possibleh][offset - roffset].update(
                            [s + offset for s in infos.steps]
                        )

        for key, vdict in finaldates.items():
            for possibleh in vdict.keys():
                vdict[possibleh] = {
                    off: sorted(terms)
                    for off, terms in vdict[possibleh].items()
                }

        return finaldates

    def compatible_with(self, other):
        if isinstance(other, self.__class__):
            return (
                self.target_hhs == other.target_hhs
                and self.refill_cutoff == other.refill_cutoff
            )
        else:
            return False

    def prepare_terms(self, date, cutoff, vapp, vconf, model=None, xpid=""):
        """
        For a task computing coupling files (at **date** and **cutoff**,
        for a specific **vapp** and **vconf**), lists the terms that should be
        computed.
        """
        _, myhh = self._process_date(date)
        if model is None:
            model = vapp
        key = self._cpl_key(myhh, cutoff, vapp, vconf, xpid, model)
        try:
            return self._prepare_terms_map[key]
        except KeyError:
            raise CouplingOffsetConfPrepareError(self._cpl_fmtkey(key))

    def coupling_offset(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        time delta with the coupling model/file base date.
        """
        _, myhh = self._process_date(date)
        return self._hh_offset(
            myhh,
            self._cpl_data[cutoff][myhh].base,
            self._cpl_data[cutoff][myhh].dayoff,
        )

    def coupling_date(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        base date of the coupling model/file.
        """
        mydate, myhh = self._process_date(date)
        return mydate - self._hh_offset(
            myhh,
            self._cpl_data[cutoff][myhh].base,
            self._cpl_data[cutoff][myhh].dayoff,
        )

    def coupling_terms(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        list of terms that should be fetched from the coupling model/file.
        """
        _, myhh = self._process_date(date)
        offset = self._hh_offset(
            myhh,
            self._cpl_data[cutoff][myhh].base,
            self._cpl_data[cutoff][myhh].dayoff,
        )
        return [s + offset for s in self._cpl_data[cutoff][myhh].steps]

    def _coupling_stuff(self, date, cutoff, stuff):
        _, myhh = self._process_date(date)
        return getattr(self._cpl_data[cutoff][myhh], stuff)

    def coupling_steps(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        prescribed steps.
        """
        return self._coupling_stuff(date, cutoff, "steps")

    def coupling_cutoff(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        cutoff of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, "cutoff")

    def coupling_vapp(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        vapp of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, "vapp")

    def coupling_vconf(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        vconf of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, "vconf")

    def coupling_xpid(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        experiment ID of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, "xpid")

    def coupling_model(self, date, cutoff):
        """
        For a task needing coupling (at **date** and **cutoff**), return the
        vconf of the coupling model/file.
        """
        return self._coupling_stuff(date, cutoff, "model")

    def refill_terms(
        self,
        date,
        cutoff,
        vapp,
        vconf,
        model=None,
        refill_cutoff=None,
        xpid="",
    ):
        """The terms that should be computed for a given refill task."""
        refill_cutoff = (
            self.refill_cutoff if refill_cutoff is None else refill_cutoff
        )
        if refill_cutoff not in self._refill_terms_map:
            self._refill_terms_map[refill_cutoff] = self._compute_refill_terms(
                refill_cutoff, self.compute_on_refill, self.isolated_refill
            )
        if model is None:
            model = vapp
        mydate, myhh = self._process_date(date)
        key = self._rtask_key(cutoff, vapp, vconf, xpid, model)
        finaldates = dict()
        if (
            key not in self._refill_terms_map[refill_cutoff]
            or myhh not in self._refill_terms_map[refill_cutoff][key]
        ):
            raise CouplingOffsetConfRefillError(self._rtask_fmtkey(key))
        for off, terms in self._refill_terms_map[refill_cutoff][key][
            myhh
        ].items():
            finaldates[str(mydate - off)] = terms
        return {"date": finaldates}

    def refill_dates(
        self,
        date,
        cutoff,
        vapp,
        vconf,
        model=None,
        refill_cutoff=None,
        xpid="",
    ):
        """The dates that should be processed in a given refill task."""
        return list(
            self.refill_terms(
                date,
                cutoff,
                vapp,
                vconf,
                model=model,
                refill_cutoff=refill_cutoff,
                xpid=xpid,
            )["date"].keys()
        )

    def refill_months(
        self,
        date,
        cutoff,
        vapp,
        vconf,
        model=None,
        refill_cutoff=None,
        xpid="",
    ):
        """The months that should be processed in a given refill task."""
        mindate = min(
            self.refill_dates(
                date,
                cutoff,
                vapp,
                vconf,
                model=model,
                refill_cutoff=refill_cutoff,
                xpid=xpid,
            )
        )
        minmonth = Month(mindate)
        return [minmonth, minmonth + 1]


class AggregatedCouplingOffsetConfTool(ConfTool):
    _footprint = dict(
        info="Aggregate several CouplingOffsetConfTool objects into one",
        attr=dict(
            kind=dict(
                values=[
                    "aggcouplingoffset",
                ],
            ),
            nominal=dict(
                info="A list of couplingoffset objects used in nominal cases",
                type=FPList,
            ),
            alternate=dict(
                info="A list of couplingoffset objects used in rescue modes",
                type=FPList,
                optional=True,
            ),
            use_alternates=dict(
                info="Actually use rescue mode ?",
                optional=True,
                default=True,
                type=bool,
            ),
            verbose=dict(
                info="When the object is created, print a summary.",
                type=bool,
                optional=True,
                default=True,
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._toolslist = list(self.nominal)
        if self.alternate and self.use_alternates:
            self._toolslist.extend(self.alternate)
        # At least one object is needed:
        if not len(self._toolslist):
            raise CouplingOffsetConfError("At least one sub-object is needed")
        # Check consistency
        for num, toolobj in enumerate(self._toolslist[1:]):
            if not self._toolslist[0].compatible_with(toolobj):
                print("\n", "*" * 50)
                print(
                    "self._toolslist[0] =",
                    self._toolslist[0],
                    "\n",
                    " target_hhs    =",
                    self._toolslist[0].target_hhs,
                    " refill_cutoff =",
                    self._toolslist[0].refill_cutoff,
                )
                print(
                    "is not consistent with object num",
                    num,
                    ":",
                    toolobj,
                    "\n",
                    " target_hhs    =",
                    toolobj.target_hhs,
                    " refill_cutoff =",
                    toolobj.refill_cutoff,
                )
                raise CouplingOffsetConfError("Inconsistent sub-objects")

        if self.verbose:
            print()
            print(
                "#### Aggregated Coupling configuration tool initialised ####"
            )
            print(
                "It is made of {:d} nominal configuration tool(s)".format(
                    len(self.nominal)
                )
            )
            if self.alternate and self.use_alternates:
                print(
                    "+ {:d} rescue-mode configuration tool(s)".format(
                        len(self.alternate)
                    )
                )
            else:
                print(
                    "No rescue-mode configuration tool is considered (deactivated)"
                )
            print()

    def prepare_terms(self, date, cutoff, vapp, vconf, model=None, xpid=""):
        """
        For a task computing coupling files (at **date** and **cutoff**,
        for a specific **vapp** and **vconf**), lists the terms that should be
        computed.
        """
        terms = set()
        for toolobj in self._toolslist:
            try:
                terms.update(
                    toolobj.prepare_terms(
                        date, cutoff, vapp, vconf, model=model, xpid=xpid
                    )
                )
            except CouplingOffsetConfPrepareError as e:
                lateste = e
        if not terms:
            raise lateste
        else:
            return sorted(terms)

    def refill_terms(
        self,
        date,
        cutoff,
        vapp,
        vconf,
        model=None,
        refill_cutoff=None,
        xpid="",
    ):
        """The terms that should be computed for a given refill task."""
        finaldates = collections.defaultdict(set)
        for toolobj in self._toolslist:
            try:
                rt = toolobj.refill_terms(
                    date,
                    cutoff,
                    vapp,
                    vconf,
                    model=model,
                    refill_cutoff=refill_cutoff,
                    xpid=xpid,
                )
                for k, v in rt["date"].items():
                    finaldates[k].update(v)
            except CouplingOffsetConfRefillError as e:
                lateste = e
        if not finaldates:
            raise lateste
        else:
            for k, v in finaldates.items():
                finaldates[k] = sorted(v)
            return {"date": finaldates}

    def refill_dates(
        self,
        date,
        cutoff,
        vapp,
        vconf,
        model=None,
        refill_cutoff=None,
        xpid="",
    ):
        """The dates that should be processed in a given refill task."""
        return list(
            self.refill_terms(
                date,
                cutoff,
                vapp,
                vconf,
                model=model,
                refill_cutoff=refill_cutoff,
                xpid=xpid,
            )["date"].keys()
        )

    def refill_months(
        self,
        date,
        cutoff,
        vapp,
        vconf,
        model=None,
        refill_cutoff=None,
        xpid="",
    ):
        """The months that should be processed in a given refill task."""
        mindate = min(
            self.refill_dates(
                date,
                cutoff,
                vapp,
                vconf,
                model=model,
                refill_cutoff=refill_cutoff,
                xpid=xpid,
            )
        )
        minmonth = Month(mindate)
        return [minmonth, minmonth + 1]


class TimeSerieInputFinderError(Exception):
    """Any exception raise by :class:`TimeSerieInputFinderConfTool` objects."""

    pass


class TimeSerieInputFinderConfTool(ConfTool):
    """
    A conf tool that find the appropriate begin/end date for an input resource
    to be taken in a timeserie.

    Let's consider a serie of 3 consecutive Surfex forcing files:

      * The first file start on 2018/01/01 00UTC
      * Each file covers a two days period

    The conf tool will look like::

      >>> ct = TimeSerieInputFinderConfTool(kind="timeserie",
      ...                                   timeserie_begin="2018010100",
      ...                                   timeserie_step="P2D")

    To find the date/term of the forcing file encompassing a 6 hours forecast
    starting on 2018/01/04 12UTC, use::

      >>> ct.begindate('2018010412', 'PT6H')
      Date(2018, 1, 3, 0, 0)
      >>> ct.term('2018010312', '06:00')
      Time(48, 0)

    """

    _footprint = dict(
        info="Conf tool that find the appropriate begin/end date for an input resource.",
        attr=dict(
            kind=dict(
                values=[
                    "timeserie",
                ],
            ),
            timeserie_begin=dict(
                info="The date when the time serie starts", type=Date
            ),
            timeserie_step=dict(
                info="The step between files of the time serie.", type=Period
            ),
            upperbound_included=dict(type=bool, optional=True, default=True),
            singlefile=dict(
                info="The period requested by a user should be contained in a single file.",
                type=bool,
                optional=True,
                default=False,
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._begincache = dict()
        self._steplength = self.timeserie_step.length

    def _begin_lookup(self, begindate):
        """Find the appropriate tiem serie's file date just before **begindate**."""
        if begindate not in self._begincache:
            if begindate < self.timeserie_begin:
                raise TimeSerieInputFinderError(
                    "Request begin date is too soon !"
                )
            dt = begindate - self.timeserie_begin
            nsteps = int(math.floor(dt.length / self._steplength))
            self._begincache[begindate] = (
                self.timeserie_begin + nsteps * self.timeserie_step
            )
        return self._begincache[begindate]

    def _begindates_expansion(self, tdate, tlength):
        """Generate a begin date or a list of begin dates."""
        xperiods = tlength / self._steplength
        nfiles = int(math.ceil(xperiods))
        if xperiods == int(xperiods) and not self.upperbound_included:
            nfiles += 1
        if nfiles > 1:
            if self.singlefile:
                raise TimeSerieInputFinderError(
                    "Multiple files requested but singlefile=.T."
                )
            return [tdate + i * self.timeserie_step for i in range(0, nfiles)]
        else:
            return tdate

    def _enddates_expansion(self, tdates):
        """Generate an end date or a dict of enddates."""
        if isinstance(tdates, list):
            return dict(begindate={d: d + self.timeserie_step for d in tdates})
        else:
            return tdates + self.timeserie_step

    @staticmethod
    def _dates_normalise(begindate, enddate):
        """Convert **begin/enddate** to a proper Date object."""
        if not isinstance(begindate, Date):
            begindate = Date(begindate)
        if not isinstance(enddate, Date):
            enddate = Date(enddate)
        return begindate, enddate

    @staticmethod
    def _date_term_normalise(begindate, term):
        """Convert **begindate** and **term** to a proper Date/Time object."""
        if not isinstance(begindate, Date):
            begindate = Date(begindate)
        if not isinstance(term, Time):
            term = Time(term)
        return begindate, term

    def begindate_i(self, begindate, enddate):
        """Find the file dates encompassing [**begindate**, **enddate**]."""
        begindate, enddate = self._dates_normalise(begindate, enddate)
        tdate = self._begin_lookup(begindate)
        tlength = (enddate - begindate).length
        return self._begindates_expansion(tdate, tlength)

    def enddate_i(self, begindate, enddate):
        """Find the file enddates encompassing [**begindate**, **enddate**]."""
        return self._enddates_expansion(self.begindate_i(begindate, enddate))

    def term_i(self, begindate, enddate):  # @UnusedVariable
        """Find the term of the time serie files."""
        return Time(self.timeserie_step)

    def begindate(self, begindate, term):
        """Find the file dates encompassing [**begindate**, **begindate** + **term**]."""
        begindate, term = self._date_term_normalise(begindate, term)
        return self._begindates_expansion(
            self._begin_lookup(begindate), int(term) * 60
        )

    def enddate(self, begindate, term):
        """Find the file enddates encompassing [**begindate**, **begindate** + **term**]."""
        return self._enddates_expansion(self.begindate(begindate, term))

    def term(self, begindate, term):  # @UnusedVariable
        """Find the term of the time serie files."""
        return Time(self.timeserie_step)


class ArpIfsForecastTermConfTool(ConfTool):
    """Deal with any Arpege/IFS model final term and outputs.


    The conf tool will look like::

      >>> ct = ArpIfsForecastTermConfTool(kind="arpifs_fcterms",
      ...                                 fcterm_def=dict(production={0:102, 12:24},
      ...                                                 assim={"default": 6}),
      ...                                 hist_terms_def=dict(production={"default":"0-47-6,48-finalterm-12"},
      ...                                                     assim={"default":"0,3,6"}),
      ...                                 surf_terms_def=dict(production={"default":None, 0:"3,6"},
      ...                                                     assim={"default":"3,6"}),
      ...                                 diag_fp_terms_def=dict(default={"default":"0-47-3,48-finalterm-6"}),
      ...                                 extra_fp_terms_def=dict(
      ...                                     aero=dict(production={0:"0-48-3"}),
      ...                                     foo=dict(default={"default":"2,3"})
      ...                                 ),
      ...                                 secondary_diag_terms_def=dict(
      ...                                     labo=dict(production={0: "0-12-1"})
      ...                                 ),
      ...      )

    The forecast term can be retrieved:

      >>> print(ct.fcterm('assim', 6))
      6
      >>> print(ct.fcterm('production', 0))
      102
      >>> print(ct.fcterm('production', 12))
      24

    If nothing is defined it crashes:

      >>> print(ct.fcterm('production', 6))
      Traceback (most recent call last):
      ...
      ValueError: Nothing is defined for cutoff="production"/hh="06:00" in "fcterm"

    The list of requested historical terms can be retrieved. It is automaticaly
    constrained by the forecast term:

      >>> print(','.join([str(t) for t in ct.hist_terms('assim', 6)]))
      0,3,6
      >>> print(','.join([str(t) for t in ct.hist_terms('production', 0)]))
      0,6,12,18,24,30,36,42,48,60,72,84,96
      >>> print(','.join([str(t) for t in ct.hist_terms('production', 12)]))
      0,6,12,18,24

    The list of requested Surfex files can be retrieved:

      >>> print(','.join([str(t) for t in ct.surf_terms('assim', 6)]))
      3,6

    The list of terms produced by the inline fullpos is:

      >>> print(','.join([str(t) for t in ct.inline_terms('assim', 6)]))
      0,3,6
      >>> print(','.join([str(t) for t in ct.inline_terms('production', 0)]))
      0,1,2,3,4,5,6,7,8,9,10,11,12,15,18,21,24,27,30,33,36,39,42,45,48,54,60,66,72,78,84,90,96,102
      >>> print(','.join([str(t) for t in ct.inline_terms('production', 12)]))
      0,3,6,9,12,15,18,21,24

    Note: It depends on the value of **use_inline_fp**. If ``False`` an empty
    list will be returned.

    The inline Fullpos can also be switched-off manually using the `no_inline`
    property:

      >>> print(','.join([str(t) for t in ct.no_inline.inline_terms('production', 0)]))
      <BLANKLINE>
      >>> print(','.join([str(t) for t in ct.no_inline.diag_terms('production', 0)]))
      0,1,2,3,4,5,6,7,8,9,10,11,12,15,18,21,24,27,30,33,36,39,42,45,48,54,60,66,72,78,84,90,96,102

    The list of terms when some offline fullpos job is needed (for any of the
    domains):

      >>> print(','.join([str(t) for t in ct.fpoff_terms('assim', 6)]))
      2,3
      >>> print(','.join([str(t) for t in ct.fpoff_terms('production', 0)]))
      0,2,3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48
      >>> print(','.join([str(t) for t in ct.fpoff_terms('production', 12)]))
      2,3

    The list of terms, in addition to requested historical terms, needed to run
    offline fullpos job:

      >>> print(','.join([str(t) for t in ct.extra_hist_terms('production', 0)]))
      2,3,9,15,21,27,33,39,45

    The list of all historical terms (both requested terms and terms required
    for offline Fullpos)

      >>> print(','.join([str(t) for t in ct.all_hist_terms('production', 0)]))
      0,2,3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48,60,72,84,96

    The list of involved Fullpos objects for a given cutoff/hh:

      >>> print(','.join([t for t in ct.fpoff_items('assim', 6)]))
      foo
      >>> print(','.join([t for t in ct.fpoff_items('production', 0)]))
      aero,foo
      >>> print(','.join([t for t in ct.fpoff_items('production', 0, discard=['aero'])]))
      foo
      >>> print(','.join([t for t in ct.fpoff_items('production', 0, only=['foo'])]))
      foo
      >>> print(','.join([t for t in ct.fpoff_items('production', 12)]))
      foo

    The list of terms associated to a given Fullpos object can be obtained:

      >>> print(','.join([str(t) for t in ct.foo_terms('assim', 6)]))
      2,3
      >>> print(','.join([str(t) for t in ct.aero_terms('assim', 6)]))
      <BLANKLINE>
      >>> print(','.join([str(t) for t in ct.foo_terms('production', 0)]))
      2,3
      >>> print(','.join([str(t) for t in ct.aero_terms('production', 0)]))
      0,3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48
      >>> print(','.join([str(t) for t in ct.foo_terms('production', 12)]))
      2,3
      >>> print(','.join([str(t) for t in ct.aero_terms('production', 12)]))
      <BLANKLINE>

    It can also be obtained as a FPList objects (if empty, an empty list is returned
    instead of an FPList object):

      >>> ct.aero_terms_fplist('assim', 6)
      []
      >>> print(','.join([str(t) for t in ct.aero_terms_fplist('production', 0)]))
      0,3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48
      >>> print(type(ct.aero_terms_fplist('production', 0)).__name__)
      FPList
      >>> ct.aero_terms_fplist('production', 12)
      []

    A mapping dictionary can also be obtained:

      >>> for k, v in sorted(ct.fpoff_terms_map('production', 0).items()):
      ...     print('{:s}: {:s}'.format(k, ','.join([str(vv) for vv in v])))
      aero: 0,3,6,9,12,15,18,21,24,27,30,33,36,39,42,45,48
      foo: 2,3

    The list of terms associated to secondary diagnostics can be obtained
    ("secondary diagnostics" stands for diagnostics that are based on files
    pre-calculated by the inline/offline fullpos):

      >>> print(','.join([str(t) for t in ct.labo_terms('production', 0)]))
      0,1,2,3,4,5,6,7,8,9,10,11,12
      >>> print(','.join([str(t) for t in ct.labo_terms('production', 12)]))
      <BLANKLINE>

    """

    _footprint = dict(
        info="Conf tool that helps setting up Arpege's forecast term and outputs",
        attr=dict(
            kind=dict(
                values=[
                    "arpifs_fcterms",
                ],
            ),
            fcterm_def=dict(
                info=(
                    "The forecast's term for each cutoff and base time "
                    + "(e.g ``{'assim':{0:6, 12:6}, 'production':{0:102}}``)"
                ),
                type=dict,
            ),
            fcterm_unit=dict(
                info="The forecast's term unit (hour or timestep)",
                values=["hour", "timestep"],
                optional=True,
                default="hour",
            ),
            hist_terms_def=dict(
                info=(
                    "The forecast's terms when historical files are needed "
                    + "(for permanant storage) "
                    + "(e.g ``{'assim':{default: '0-finalterm-3'}, "
                    + "'production':{0:'0-23-1,24-finalterm-6}}``)"
                ),
                type=dict,
                optional=True,
            ),
            surf_terms_def=dict(
                info=(
                    "The forecast's terms when surface files are needed "
                    + "(for permanant storage) "
                ),
                type=dict,
                optional=True,
            ),
            norm_terms_def=dict(
                info="The forecast's terms when spectral norms are computed",
                type=dict,
                optional=True,
            ),
            diag_fp_terms_def=dict(
                info="The forecast's terms when fullpos core diagnostics are computed",
                type=dict,
                optional=True,
            ),
            extra_fp_terms_def=dict(
                info=(
                    "The forecast's terms when extra fullpos diagnostics are computed. "
                    + "They are always computed by some offline tasks. "
                    + "The dictionary has an additional level (describing the 'name' of the "
                    + "extra fullpos processing"
                ),
                type=dict,
                optional=True,
            ),
            secondary_diag_terms_def=dict(
                info=(
                    "The forecast's terms when secondary diagnostics are computed. "
                    + "Secondary dignostics are based on diagnostics previously created by "
                    + "the inline/offline diag fullpos (see diag_fp_terms_def)."
                    + "The dictionary has an additional level (describing the 'name' of the "
                    + "secondary diags"
                ),
                type=dict,
                optional=True,
            ),
            use_inline_fp=dict(
                info='Use inline Fullpos to compute "core_fp_terms"',
                type=bool,
                optional=True,
                default=True,
            ),
        ),
    )

    _ACTUAL_T_RE = re.compile(r"(\w+)_terms$")
    _ACTUAL_FPLIST_T_RE = re.compile(r"(\w+)_terms_fplist$")
    _UNDEFINED = object()

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._x_fcterm = self._check_data_keys_and_times(
            self.fcterm_def, "fcterm_def", cast=self._cast_unique_value
        )
        self._x_hist_terms = self._check_data_keys_and_times(
            self.hist_terms_def, "hist_terms_def", cast=self._cast_timerangex
        )
        self._x_surf_terms = self._check_data_keys_and_times(
            self.surf_terms_def, "surf_terms_def", cast=self._cast_timerangex
        )
        self._x_norm_terms = self._check_data_keys_and_times(
            self.norm_terms_def, "norm_terms_def", cast=self._cast_timerangex
        )
        self._x_diag_fp_terms = self._check_data_keys_and_times(
            self.diag_fp_terms_def,
            "diag_fp_terms_def",
            cast=self._cast_timerangex,
        )
        self._x_extra_fp_terms = (
            dict()
            if self.extra_fp_terms_def is None
            else self.extra_fp_terms_def
        )
        if not all(
            [isinstance(v, dict) for v in self._x_extra_fp_terms.values()]
        ):
            raise ValueError("extra_fp_terms values need to be dictionaries")
        self._x_extra_fp_terms = {
            k: self._check_data_keys_and_times(
                v,
                "extra_fp_terms_def[{:s}]".format(k),
                cast=self._cast_timerangex,
            )
            for k, v in self._x_extra_fp_terms.items()
        }
        self._x_secondary_diag_terms_def = (
            dict()
            if self.secondary_diag_terms_def is None
            else self.secondary_diag_terms_def
        )
        if not all(
            [
                isinstance(v, dict)
                for v in self._x_secondary_diag_terms_def.values()
            ]
        ):
            raise ValueError("extra_fp_terms values need to be dictionaries")
        self._x_secondary_diag_terms_def = {
            k: self._check_data_keys_and_times(
                v,
                "secondary_diag_terms_def[{:s}]".format(k),
                cast=self._cast_timerangex,
            )
            for k, v in self._x_secondary_diag_terms_def.items()
        }
        self._lookup_cache = dict()
        self._lookup_rangex_cache = dict()
        self._no_inline_cache = None

    def _clone(self, **kwargs):
        my_args = self.footprint_as_shallow_dict()
        my_args.update(kwargs)
        return self.__class__(**my_args)

    @property
    def no_inline(self):
        """Return a clone of this object with inline fullpos de-activated."""
        if self._no_inline_cache is None:
            self._no_inline_cache = self._clone(use_inline_fp=False)
        return self._no_inline_cache

    @staticmethod
    def _cast_void(value):
        return value

    def _cast_unique_value(self, value):
        if self.fcterm_unit == "hour":
            return Time(value)
        else:
            return int(value)

    @staticmethod
    def _cast_timerangex(value):
        if not (value is None or isinstance(value, str)):
            if isinstance(value, collections.abc.Iterable):
                value = ",".join([str(e) for e in value])
            else:
                value = str(value)
        return value

    @staticmethod
    def _check_data_keys(data, dataname):
        """Check the first level of any input dictionary."""
        if data is None:
            return dict(default=dict(default=None))
        else:
            if not set(data.keys()) <= {"assim", "production", "default"}:
                raise ValueError(
                    'Impoper value ({!s}) for "{:s}".'.format(data, dataname)
                )
            return data

    def _check_data_keys_and_times(self, data, dataname, cast=None):
        """Check any input dictionary and convert values."""
        data = self._check_data_keys(data, dataname)
        cast = self._cast_void if cast is None else cast
        new_data = dict()
        for data_k, data_v in data.items():
            if not isinstance(data_v, dict):
                raise ValueError(
                    'The {:s} "{:s}" entry should be a dictionary (got "{!s}")'.format(
                        dataname, data_k, data_v
                    )
                )
            try:
                new_data[data_k] = {
                    "default" if k == "default" else Time(k): cast(v)
                    for k, v in data_v.items()
                }
            except ValueError as e:
                raise ValueError(
                    "Error while processing {:s}'s {:s}: ".format(
                        dataname, data_k
                    )
                    + "Could not convert to Time (original message '{!s}')".format(
                        e
                    )
                )
        return new_data

    def _cutoff_hh_lookup(self, what_desc, cutoff, hh, rawdata=None):
        """Look for a particular cutoff in self._x_what_desc."""
        if not isinstance(hh, Time):
            hh = Time(hh)
        if (what_desc, cutoff, hh) not in self._lookup_cache:
            if rawdata is None:
                rawdata = getattr(self, "_x_{:s}".format(what_desc))
            cutoff_v = rawdata.get(
                cutoff, rawdata.get("default", self._UNDEFINED)
            )
            if cutoff_v is self._UNDEFINED:
                raise ValueError(
                    'Nothing is defined for cutoff="{:s}" in "{:s}"'.format(
                        cutoff, what_desc
                    )
                )
            hh_v = cutoff_v.get(hh, cutoff_v.get("default", self._UNDEFINED))
            if hh_v is self._UNDEFINED:
                raise ValueError(
                    'Nothing is defined for cutoff="{:s}"/hh="{!s}" in "{:s}"'.format(
                        cutoff, hh, what_desc
                    )
                )
            self._lookup_cache[(what_desc, cutoff, hh)] = hh_v
        return self._lookup_cache[(what_desc, cutoff, hh)]

    def _cutoff_hh_rangex_lookup(self, what_desc, cutoff, hh, rawdata=None):
        """Look for a particular cutoff in self._x_what_desc and resolve the rangex."""
        if (what_desc, cutoff, hh) not in self._lookup_rangex_cache:
            try:
                what = self._cutoff_hh_lookup(
                    what_desc, cutoff, hh, rawdata=rawdata
                )
            except ValueError:
                what = None
            if what is None:
                self._lookup_rangex_cache[(what_desc, cutoff, hh)] = list()
            else:
                finalterm = self._cutoff_hh_lookup("fcterm", cutoff, hh)
                if "finalterm" in what:
                    what = what.replace("finalterm", str(finalterm))
                try:
                    tir = timeintrangex(what)
                except (TypeError, ValueError):
                    raise ValueError(
                        'Could not process "{:s}" using timeintrangex (from "{:s}" with cutoff={:s}/hh={!s})'.format(
                            what, what_desc, cutoff, hh
                        )
                    )
                if self.fcterm_unit == "timestep" and not all(
                    [isinstance(i, int) for i in tir]
                ):
                    raise ValueError(
                        'No hours/minutes allowed when fcterm_unit is "timestep" '
                        + '(from "{:s}" with cutoff={:s}/hh={!s})'.format(
                            what_desc, cutoff, hh
                        )
                    )
                self._lookup_rangex_cache[(what_desc, cutoff, hh)] = sorted(
                    [t for t in tir if t <= finalterm]
                )
        return self._lookup_rangex_cache[(what_desc, cutoff, hh)]

    def fcterm(self, cutoff, hh):
        """The forecast term for **cutoff** and **hh**."""
        fcterm = self._cutoff_hh_lookup("fcterm", cutoff, hh)
        if isinstance(fcterm, Time) and fcterm.minute == 0:
            return fcterm.hour
        else:
            return fcterm

    def hist_terms(self, cutoff, hh):
        """The list of terms for requested/archived historical files."""
        return self._cutoff_hh_rangex_lookup("hist_terms", cutoff, hh)

    def surf_terms(self, cutoff, hh):
        """The list of terms for historical surface files."""
        return self._cutoff_hh_rangex_lookup("surf_terms", cutoff, hh)

    def norm_terms(self, cutoff, hh):
        """The list of terms for norm calculations."""
        return self._cutoff_hh_rangex_lookup("norm_terms", cutoff, hh)

    def inline_terms(self, cutoff, hh):
        """The list of terms for inline diagnostics."""
        if self.use_inline_fp:
            return sorted(
                set(self._cutoff_hh_rangex_lookup("diag_fp_terms", cutoff, hh))
                | self._secondary_diag_terms_set(cutoff, hh)
            )
        else:
            return list()

    def diag_terms(self, cutoff, hh):
        """The list of terms for offline diagnostics."""
        if self.use_inline_fp:
            return list()
        else:
            return sorted(
                set(self._cutoff_hh_rangex_lookup("diag_fp_terms", cutoff, hh))
                | self._secondary_diag_terms_set(cutoff, hh)
            )

    def diag_terms_fplist(self, cutoff, hh):
        """The list of terms for offline diagnostics (as a FPlist)."""
        flist = self.diag_terms(cutoff, hh)
        return FPList(flist) if flist else []

    def _extra_fp_terms_item_fplist(self, item, cutoff, hh):
        flist = self._cutoff_hh_rangex_lookup(
            "extra_fp_terms[{:s}]".format(item),
            cutoff,
            hh,
            rawdata=self._x_extra_fp_terms[item],
        )
        return FPList(flist) if flist else []

    def _secondary_diag_terms_item_fplist(self, item, cutoff, hh):
        flist = self._cutoff_hh_rangex_lookup(
            "secondary_diag_terms[{:s}]".format(item),
            cutoff,
            hh,
            rawdata=self._x_secondary_diag_terms_def[item],
        )
        return FPList(flist) if flist else []

    @secure_getattr
    def __getattr__(self, item):
        actual_m = self._ACTUAL_T_RE.match(item)
        actual_fplist_m = self._ACTUAL_FPLIST_T_RE.match(item)
        if actual_m and actual_m.group(1) in self._x_extra_fp_terms.keys():
            return functools.partial(
                self._cutoff_hh_rangex_lookup,
                "extra_fp_terms[{:s}]".format(actual_m.group(1)),
                rawdata=self._x_extra_fp_terms[actual_m.group(1)],
            )
        elif (
            actual_fplist_m
            and actual_fplist_m.group(1) in self._x_extra_fp_terms.keys()
        ):
            return functools.partial(
                self._extra_fp_terms_item_fplist, actual_fplist_m.group(1)
            )
        elif (
            actual_m
            and actual_m.group(1) in self._x_secondary_diag_terms_def.keys()
        ):
            return functools.partial(
                self._cutoff_hh_rangex_lookup,
                "secondary_diag_terms[{:s}]".format(actual_m.group(1)),
                rawdata=self._x_secondary_diag_terms_def[actual_m.group(1)],
            )
        elif (
            actual_fplist_m
            and actual_fplist_m.group(1)
            in self._x_secondary_diag_terms_def.keys()
        ):
            return functools.partial(
                self._secondary_diag_terms_item_fplist,
                actual_fplist_m.group(1),
            )
        else:
            raise AttributeError('Attribute "{:s}" was not found'.format(item))

    def _fpoff_terms_set(self, cutoff, hh):
        fpoff_terms = set()
        for k, v in self._x_extra_fp_terms.items():
            fpoff_terms.update(
                self._cutoff_hh_rangex_lookup(
                    "extra_fp_terms[{:s}]".format(k), cutoff, hh, rawdata=v
                )
            )
        if not self.use_inline_fp:
            fpoff_terms.update(
                self._cutoff_hh_rangex_lookup("diag_fp_terms", cutoff, hh)
            )
            fpoff_terms.update(self._secondary_diag_terms_set(cutoff, hh))
        return fpoff_terms

    def _secondary_diag_terms_set(self, cutoff, hh):
        sec_terms = set()
        for k, v in self._x_secondary_diag_terms_def.items():
            sec_terms.update(
                self._cutoff_hh_rangex_lookup(
                    "secondary_diag_terms[{:s}]".format(k),
                    cutoff,
                    hh,
                    rawdata=v,
                )
            )
        return sec_terms

    def extra_hist_terms(self, cutoff, hh):
        """The list of terms for historical file terms solely produced for fullpos use."""
        fpoff_terms = self._fpoff_terms_set(cutoff, hh)
        fpoff_terms -= set(self.hist_terms(cutoff, hh))
        return sorted(fpoff_terms)

    def all_hist_terms(self, cutoff, hh):
        """The list of terms for all historical file."""
        all_terms = self._fpoff_terms_set(cutoff, hh)
        all_terms |= set(self.hist_terms(cutoff, hh))
        return sorted(all_terms)

    def fpoff_terms(self, cutoff, hh):
        """The list of terms for offline fullpos."""
        fpoff_terms = self._fpoff_terms_set(cutoff, hh)
        return sorted(fpoff_terms)

    def fpoff_items(self, cutoff, hh, discard=None, only=None):
        """List of active offline post-processing domains."""
        items = {
            k
            for k, v in self._x_extra_fp_terms.items()
            if self._cutoff_hh_rangex_lookup(
                "extra_fp_terms[{:s}]".format(k), cutoff, hh, rawdata=v
            )
        }
        if not self.use_inline_fp and self._cutoff_hh_rangex_lookup(
            "diag_fp_terms", cutoff, hh
        ):
            items.add("diag")
        if discard:
            items -= set(discard)
        if only:
            items &= set(only)
        return sorted(items)

    def fpoff_terms_map(self, cutoff, hh):
        """The mapping dictionary between offline post-processing terms and domains."""
        return {
            k: getattr(self, "{:s}_terms".format(k))(cutoff, hh)
            for k in self.fpoff_items(cutoff, hh)
        }

    def fpoff_terms_fpmap(self, cutoff, hh):
        """The mapping dictionary between offline post-processing terms and domains (as a FPlist)."""
        return {
            k: getattr(self, "{:s}_terms_fplist".format(k))(cutoff, hh)
            for k in self.fpoff_items(cutoff, hh)
        }


class TimeSlotsConfTool(AbstractObjectProxyConfTool):
    """Gives easy access to a Timeslots object.

    The conf tool will look like::

      >>> ct = TimeSlotsConfTool(kind="objproxy",
      ...                        timeslots_def="7/-PT3H/PT6H")
      >>> print(ct.start)
      -PT10800S

    """

    _footprint = dict(
        info="Gives easy access to a Timeslots object.",
        attr=dict(
            timeslots_def=dict(
                info="The timeslots specification",
            ),
        ),
    )

    def _create_proxied_obj(self):
        return TimeSlots(self.timeslots_def)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
