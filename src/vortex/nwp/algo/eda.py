"""
AlgoComponents dedicated to computations related to the Ensemble Data Assimilation
system.
"""

import math
import re

from bronx.fancies import loggers
from bronx.stdtypes.date import Month, Time
import footprints

from vortex.algo.components import AlgoComponentError
from .ifsroot import IFSParallel

#: Automatic export off
__all__ = []

logger = loggers.getLogger(__name__)


class IFSEdaAbstractAlgo(IFSParallel):
    """Base class for any EDA related task wrapped into an IFS/Arpege binary."""

    _abstract = True
    _footprint = dict(
        info="Base class for any EDA related task",
        attr=dict(
            inputnaming=dict(
                info="Prescribe your own naming template for input files.",
                optional=True,
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
        ),
    )

    def naming_convention(self, kind, rh, actualfmt=None, **kwargs):
        """Take into account the *inputnaming* attribute."""
        if kind == "edainput":
            return super().naming_convention(
                kind,
                rh,
                actualfmt=actualfmt,
                namingformat=self.inputnaming,
                **kwargs,
            )
        else:
            return super().naming_convention(
                kind, rh, actualfmt=actualfmt, **kwargs
            )


class IFSEdaEnsembleAbstractAlgo(IFSEdaAbstractAlgo):
    """Base class for any EDA related task wrapped into an IFS/Arpege binary.

    This extends the :class:`IFSEdaAbstractAlgo` with a *nbmember* attribute and
    the ability to detect the input files and re-number them (in order to be able
    to deal with missing members).
    """

    _INPUTS_ROLE = "ModelState"

    _abstract = True
    _footprint = dict(
        info="Base class for any EDA related task",
        attr=dict(
            nbmember=dict(
                info="The number of members to deal will (auto-detected if omitted)",
                type=int,
                optional=True,
            ),
            nbmin=dict(
                info="The minimum number of input members that is mandatory to go one",
                type=int,
                optional=True,
                default=2,
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._actual_nbe = self.nbmember

    @property
    def actual_nbe(self):
        """The effective number of members."""
        return self._actual_nbe

    @property
    def actual_totalnumber(self):
        """The total number of members (=! actual_nbe for lagged ensembles. see below)."""
        return self.actual_nbe

    @property
    def actual_nbmin(self):
        """The minimum number of effective members that are mandatory to go one."""
        return self.nbmin

    @staticmethod
    def _members_sorting_key(s):
        """Return the sorting key for the **s** section."""
        member = getattr(s.rh.provider, "member", None)
        member = -math.inf if member is None else member
        block = getattr(s.rh.provider, "block", "")
        filename = getattr(s.rh.container, "basename", "")
        return member, block, filename

    def _members_effective_inputs(self):
        """The list of effective sections representing input data."""
        return sorted(
            self.context.sequence.effective_inputs(role=self._INPUTS_ROLE),
            key=self._members_sorting_key,
        )

    def _members_all_inputs(self):
        """The list of sections representing input data."""
        return sorted(
            self.context.sequence.filtered_inputs(role=self._INPUTS_ROLE),
            key=self._members_sorting_key,
        )

    def _check_members_list_numbering(self, rh, mlist, mformats):
        """Check if, for the **mlist** members list, some renaming id needed."""
        if len(set(mlist)) != len(mlist):
            logger.warning(
                "Some members are duplicated. That's very strange..."
            )
        if self.nbmember is None:
            self.algoassert(
                len(mformats) <= 1, "Mixed formats are not allowed !"
            )
        elif self.nbmember and len(mformats) > 1:
            logger.info(
                "%s have mixed formats... please correct that.",
                self._INPUTS_ROLE,
            )
        if mlist and self.nbmember is not None:
            # Consistency check
            if len(mlist) != self.nbmember:
                logger.warning(
                    "Discrepancy between *nbmember* and effective input files..."
                    + " sticking with *nbmember*"
                )
            else:
                logger.info("The input files member numbers checks out !")
            return False  # Ok, apparently the user knows what she/he is doing
        elif self.nbmember and not mlist:
            return False  # Ok, apparently the user knows what she/he is doing
        elif mlist and self.nbmember is None:
            innc = self.naming_convention(
                kind="edainput",
                variant=self.kind,
                rh=rh,
                totalnumber=self.actual_totalnumber,
                actualfmt=mformats.pop(),
            )
            checkfiles = [
                m
                for m in range(1, len(mlist) + 1)
                if self.system.path.exists(innc(number=m))
            ]
            if len(checkfiles) == len(mlist):
                logger.info("The input files numbering checks out !")
                return (
                    False  # Ok, apparently the user knows what she/he is doing
                )
            elif len(checkfiles) == 0:
                return True
            else:
                raise AlgoComponentError(
                    "Members renumbering is needed but some "
                    + "files are blocking the way !"
                )
        elif len(mlist) == 0 and self.nbmember is None:
            raise AlgoComponentError("No input files where found !")

    def modelstate_needs_renumbering(self, rh):
        """Check if, for the **mlist** members list, some renaming id needed."""
        eff_sections = self._members_effective_inputs()
        eff_members = [sec.rh.provider.member for sec in eff_sections]
        eff_formats = {sec.rh.container.actualfmt for sec in eff_sections}
        if eff_members and self.nbmember is None:
            self._actual_nbe = len(eff_members)
        return self._check_members_list_numbering(rh, eff_members, eff_formats)

    def modelstate_renumbering(self, rh, mlist):
        """Actualy rename the effective inputs."""
        eff_format = mlist[0].rh.container.actualfmt
        innc = self.naming_convention(
            kind="edainput",
            variant=self.kind,
            rh=rh,
            totalnumber=self.actual_totalnumber,
            actualfmt=eff_format,
        )
        for i, s in enumerate(mlist, start=1):
            logger.info(
                "Soft-Linking %s to %s",
                s.rh.container.localpath(),
                innc(number=i),
            )
            self.system.softlink(s.rh.container.localpath(), innc(number=i))

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        """Update the namelists with EDA related macros."""
        nam_updated = super(IFSEdaAbstractAlgo, self).prepare_namelist_delta(
            rh, namcontents, namlocal
        )
        if self.actual_nbe is not None:
            self._set_nam_macro(namcontents, namlocal, "NBE", self.actual_nbe)
            nam_updated = True
        return nam_updated

    def prepare(self, rh, opts):
        """Check the input files and act on it."""
        self.system.subtitle("Solving the input files nightmare...")
        if self.modelstate_needs_renumbering(rh):
            eff_sections = self._members_effective_inputs()
            if len(eff_sections) < self.actual_nbmin:
                raise AlgoComponentError(
                    "Not enough input files to continue..."
                )
            logger.info(
                "Starting input files renumbering. %d effective members found",
                len(eff_sections),
            )
            self.modelstate_renumbering(rh, eff_sections)
        self.system.subtitle("Other IFS related settings")
        super().prepare(rh, opts)


class IFSEdaLaggedEnsembleAbstractAlgo(IFSEdaEnsembleAbstractAlgo):
    """Base class for any EDA related task wrapped into an IFS/Arpege binary.

    This extends the :class:`IFSEdaEnsembleAbstractAlgo` with a *nblag* attribute
    and the ability to detect the input files and re-number them (in order to be
    able to deal with missing members).
    """

    _PADDING_ROLE = "PaddingModelState"

    _abstract = True
    _footprint = dict(
        info="Base class for any EDA related task",
        attr=dict(
            nblag=dict(
                info="The number of lagged dates (auto-detected if omitted)",
                type=int,
                optional=True,
            ),
            padding=dict(
                info="Fill the gaps with some kind of climatological data",
                type=bool,
                optional=True,
                default=False,
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._actual_nresx = self.nblag

    @property
    def actual_nresx(self):
        """The effective number of lagged dates."""
        return self._actual_nresx

    @property
    def actual_totalnumber(self):
        """The total number of members."""
        return (
            self.actual_nbe * self.actual_nresx
            if self.padding
            else self.actual_nbe
        )

    @property
    def actual_nbmin(self):
        """The minimum number of effective members that are mandatory to go one."""
        return self.nbmin * self.actual_nresx if self.padding else self.nbmin

    def _members_sorting_key(self, s):
        """Return the sorting key for the **s** section."""
        stuple = list(super()._members_sorting_key(s))
        rdate = getattr(s.rh.resource, "date")
        stuple.insert(0, rdate)
        return tuple(stuple)

    def modelstate_needs_renumbering(self, rh):
        """Check if, for the **mlist** members list, some renaming id needed."""
        all_sections = self._members_all_inputs()
        eff_sections = self._members_effective_inputs()

        # Look for available dates (lagged ensemble)
        all_dates = {sec.rh.resource.date for sec in all_sections}
        if all_dates and self.nblag is not None:
            # Consistency check
            if len(all_dates) != self.nblag:
                logger.warning(
                    "Discrepancy between *nblag* and input files..."
                    + " sticking with *nblag*"
                )
        elif all_dates and self.nblag is None:
            self._actual_nresx = len(all_dates)

        # Fetch the effective members list
        if self.padding:
            # For each date, check the member's list
            d_blocks = dict()
            for a_date in all_dates:
                d_sections = [
                    sec
                    for sec in all_sections
                    if sec.rh.resource.date == a_date
                ]
                d_members = sorted(
                    [sec.rh.provider.member for sec in d_sections]
                )
                d_formats = {sec.rh.container.actualfmt for sec in d_sections}
                d_blocks[a_date] = (d_members, d_formats)
            ref_date, (eff_members, eff_formats) = d_blocks.popitem()
            for a_date, a_data in d_blocks.items():
                self.algoassert(
                    a_data[0] == eff_members,
                    "Inconsistent members list (date={!s} vs {!s}).".format(
                        a_date, ref_date
                    ),
                )
                self.algoassert(
                    a_data[1] == eff_formats,
                    "Inconsistent formats list (date={!s} vs {!s}).".format(
                        a_date, ref_date
                    ),
                )
            d_blocks[ref_date] = (eff_members, eff_formats)
            if eff_members and self.nbmember is None:
                # Here, NBE is the number of members for one date
                self._actual_nbe = len(eff_members)
            # Generate a complete list off input files
            eff_members = []
            for a_date, a_data in sorted(d_blocks.items()):
                for member in a_data[0]:
                    eff_members.append((a_date, member))
        else:
            eff_members = [
                (sec.rh.resource.date, sec.rh.provider.member)
                for sec in eff_sections
            ]
            eff_formats = {sec.rh.container.actualfmt for sec in eff_sections}
            if eff_members and self.nbmember is None:
                # Here, NBE is the number of members for all dates
                self._actual_nbe = len(eff_members)

        return self._check_members_list_numbering(rh, eff_members, eff_formats)

    def modelstate_renumbering(self, rh, mlist):
        """Actualy rename the effective inputs."""
        if self.padding:
            eff_format = mlist[0].rh.container.actualfmt
            innc = self.naming_convention(
                kind="edainput",
                variant=self.kind,
                rh=rh,
                totalnumber=self.actual_totalnumber,
                actualfmt=eff_format,
            )
            all_sections = self._members_all_inputs()
            paddingstuff = self.context.sequence.effective_inputs(
                role=self._PADDING_ROLE
            )
            for i, s in enumerate(all_sections, start=1):
                if s.stage == "get" and s.rh.container.exists():
                    logger.info(
                        "Soft-Linking %s to %s",
                        s.rh.container.localpath(),
                        innc(number=i),
                    )
                    self.system.softlink(
                        s.rh.container.localpath(), innc(number=i)
                    )
                else:
                    mypadding = None
                    for p in paddingstuff:
                        if (
                            getattr(
                                p.rh.resource,
                                "ipert",
                                getattr(p.rh.resource, "number", None),
                            )
                            == i
                        ):
                            mypadding = p
                            break
                        else:
                            if (
                                getattr(p.rh.resource, "date", None)
                                == s.rh.resource.date
                                and getattr(p.rh.provider, "member", None)
                                == s.rh.provider.member
                            ):
                                mypadding = p
                                break
                    if mypadding is not None:
                        logger.warning(
                            "Soft-Linking Padding data %s to %s",
                            mypadding.rh.container.localpath(),
                            innc(number=i),
                        )
                        self.system.softlink(
                            mypadding.rh.container.localpath(), innc(number=i)
                        )
                    else:
                        raise AlgoComponentError(
                            "No padding data where found for i= {:d}: {!s}".format(
                                i, s
                            )
                        )
        else:
            super().modelstate_renumbering(rh, mlist)

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        """Update the namelists with EDA related macros."""
        nam_updated = super().prepare_namelist_delta(rh, namcontents, namlocal)
        if self.actual_nresx is not None:
            self._set_nam_macro(
                namcontents, namlocal, "NRESX", self.actual_nresx
            )
            nam_updated = True
        return nam_updated


class IFSEdaFemars(IFSEdaAbstractAlgo):
    """Convert some FA file in ECMWF-GRIB files. PLEASE DO NOT USE !"""

    _footprint = dict(
        info="Convert some FA file in ECMWF-GRIB files.",
        attr=dict(
            kind=dict(
                values=["femars"],
            ),
            rawfiles=dict(
                type=bool,
                optional=True,
                default=False,
            ),
        ),
    )

    def postfix(self, rh, opts):
        """Find out if any special resources have been produced."""
        sh = self.system
        # Gather rawfiles in folders
        if self.rawfiles:
            flist = sh.glob("tmprawfile_D000_L*")
            dest = "rawfiles"
            logger.info("Creating a rawfiles pack: %s", dest)
            sh.mkdir(dest)
            for fic in flist:
                sh.mv(fic, dest, fmt="grib")
        super().postfix(rh, opts)


class IFSInflationLike(IFSEdaAbstractAlgo):
    """Apply the inflation scheme on a given modelstate."""

    _RUNSTORE = "RUNOUT"
    _USELESS_MATCH = re.compile(r"^(?P<target>\w+)\+term\d+:\d+$")

    _footprint = dict(
        info="Operations around the background error covariance matrix",
        attr=dict(
            kind=dict(
                values=[
                    "infl",
                    "pert",
                ],
            ),
            conf=dict(
                values=[
                    701,
                ]
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._outputs_shelf = list()

    def _check_effective_terms(self, roles):
        eff_terms = None
        for role in roles:
            eterm = {
                sec.rh.resource.term
                for sec in self.context.sequence.effective_inputs(role=role)
            }
            if eterm:
                if eff_terms is None:
                    eff_terms = eterm
                else:
                    if eff_terms != eterm:
                        raise AlgoComponentError(
                            "Inconsistencies between inputs effective terms."
                        )
        return sorted(eff_terms)

    def _link_stuff_in(
        self, role, actualterm, targetnc, targetintent="in", wastebasket=None
    ):
        estuff = [
            sec
            for sec in self.context.sequence.effective_inputs(role=role)
            if sec.rh.resource.term == actualterm
        ]
        if len(estuff) > 1:
            logger.warning(
                "Multiple %s  for the same date ! Going on...", role
            )
        elif len(estuff) == 1:
            # Detect the inputs format
            actfmt = estuff[0].rh.container.actualfmt
            nconv = self.naming_convention(actualfmt=actfmt, **targetnc)
            targetname = nconv(**targetnc)
            if self.system.path.exists(targetname):
                logger.info(
                    "%s: %s already exists. Hopping for the best...",
                    role,
                    targetname,
                )
            else:
                logger.info(
                    "%s: copying (intent=%s) %s to %s",
                    role,
                    targetintent,
                    estuff[0].rh.container.localpath(),
                    targetname,
                )
                self.system.cp(
                    estuff[0].rh.container.localpath(),
                    targetname,
                    fmt=actfmt,
                    intent=targetintent,
                )
                if wastebasket is not None:
                    wastebasket.append((targetname, actfmt))
            return nconv, targetname, estuff[0]
        return None, None, None

    def execute(self, rh, opts):
        """Loop on the various terms provided."""

        eff_terms = self._check_effective_terms(
            ["ModelState", "EnsembleMean", "Guess"]
        )
        fix_curclim = self.do_climfile_fixer(rh, convkind="modelclim")
        fix_clclim = self.do_climfile_fixer(rh, convkind="closest_modelclim")

        if eff_terms:
            for actualterm in eff_terms:
                wastebasket = list()
                self.system.title("Loop on term {!s}".format(actualterm))
                self.system.subtitle("Solving the input files nightmare...")
                # Ensemble Mean ?
                mean_number = 2 if self.model == "arome" else 0
                targetnc = dict(
                    kind="edainput", variant="infl", rh=rh, number=mean_number
                )
                self._link_stuff_in(
                    "EnsembleMean",
                    actualterm,
                    targetnc,
                    wastebasket=wastebasket,
                )
                # Model State ?
                targetnc = dict(
                    kind="edainput", variant="infl", rh=rh, number=1
                )
                _, _, mstate = self._link_stuff_in(
                    "ModelState", actualterm, targetnc, wastebasket=wastebasket
                )
                # Control ?
                control_number = 0 if self.model == "arome" else 2
                targetnc = dict(
                    kind="edainput",
                    variant="infl",
                    rh=rh,
                    number=control_number,
                )
                self._link_stuff_in(
                    "Control", actualterm, targetnc, wastebasket=wastebasket
                )
                # Guess ?
                targetnc = dict(
                    kind="edaoutput",
                    variant="infl",
                    rh=rh,
                    number=1,
                    term=Time(0),
                )
                outnc, _, _ = self._link_stuff_in(
                    "Guess", actualterm, targetnc, targetintent="inout"
                )
                if outnc is None:
                    outnc = self.naming_convention(
                        kind="edaoutput", variant="infl", rh=rh
                    )
                # Fix clim !
                if fix_curclim and mstate:
                    month = Month((mstate.rh.resource.date + actualterm).ymdh)
                    self.climfile_fixer(
                        rh=rh,
                        convkind="modelclim",
                        month=month,
                        inputrole=("GlobalClim", "InitialClim"),
                        inputkind="clim_model",
                    )
                if fix_clclim and mstate:
                    closestmonth = Month(
                        (mstate.rh.resource.date + actualterm).ymdh
                        + ":closest"
                    )
                    self.climfile_fixer(
                        rh=rh,
                        convkind="closest_modelclim",
                        month=closestmonth,
                        inputrole=("GlobalClim", "InitialClim"),
                        inputkind="clim_model",
                    )
                # Deal with useless stuff... SADLY !
                useless = [
                    sec
                    for sec in self.context.sequence.effective_inputs(
                        role="Useless"
                    )
                    if (
                        sec.rh.resource.term == actualterm
                        and self._USELESS_MATCH.match(
                            sec.rh.container.localpath()
                        )
                    )
                ]
                for a_useless in useless:
                    targetname = self._USELESS_MATCH.match(
                        a_useless.rh.container.localpath()
                    ).group("target")
                    if self.system.path.exists(targetname):
                        logger.warning(
                            "Some useless stuff is already here: %s. I don't care...",
                            targetname,
                        )
                    else:
                        logger.info(
                            "Dealing with useless stuff: %s -> %s",
                            a_useless.rh.container.localpath(),
                            targetname,
                        )
                        self.system.cp(
                            a_useless.rh.container.localpath(),
                            targetname,
                            fmt=a_useless.rh.container.actualfmt,
                            intent="in",
                        )
                        wastebasket.append(
                            (targetname, a_useless.rh.container.actualfmt)
                        )

                # Standard execution
                super().execute(rh, opts)

                # The concatenated listing
                self.system.cat("NODE.001_01", output="NODE.all")

                # prepares the next execution
                if len(eff_terms) > 1:
                    self.system.mkdir(self._RUNSTORE)
                    # Freeze the current output
                    shelf_label = self.system.path.join(
                        self._RUNSTORE, outnc(number=1, term=actualterm)
                    )
                    self.system.move(
                        outnc(number=1, term=Time(0)), shelf_label, fmt="fa"
                    )
                    self._outputs_shelf.append(shelf_label)
                    # Some cleaning
                    for afile in wastebasket:
                        self.system.remove(afile[0], fmt=afile[1])
                    self.system.rmall("ncf927", "dirlst")
        else:
            # We should not be here but whatever... some task are poorly written !
            super().execute(rh, opts)

    def postfix(self, rh, opts):
        """Post-processing cleaning."""
        self.system.title("Finalising the execution...")
        for afile in self._outputs_shelf:
            logger.info("Output found: %s", self.system.path.basename(afile))
            self.system.move(afile, self.system.path.basename(afile), fmt="fa")
        super().postfix(rh, opts)


class IFSInflationFactor(IFSEdaEnsembleAbstractAlgo):
    """Compute an inflation factor based on individual members."""

    _footprint = dict(
        info="Compute an inflation factor based on individual members",
        attr=dict(
            kind=dict(
                values=[
                    "infl_factor",
                ],
            ),
        ),
    )


class IFSInflationFactorLegacy(IFSInflationFactor):
    """Compute an inflation factor based on individual members. KEPT FOR COMPATIBILITY.

    DO NOT USE !
    """

    _footprint = dict(
        info="Compute an inflation factor based on individual members",
        attr=dict(
            kind=dict(
                values=["infl", "pert"],
            ),
            conf=dict(
                outcast=[
                    701,
                ]
            ),
        ),
    )


class IFSEnsembleMean(IFSEdaEnsembleAbstractAlgo):
    """Apply the inflation scheme on a given modelstate."""

    _footprint = dict(
        info="Operations around the background error covariance matrix",
        attr=dict(
            kind=dict(
                values=[
                    "mean",
                ],
            ),
        ),
    )


class IFSCovB(IFSEdaLaggedEnsembleAbstractAlgo):
    """Operations around the background error covariance matrix."""

    _footprint = dict(
        info="Operations around the background error covariance matrix",
        attr=dict(
            kind=dict(
                values=[
                    "covb",
                ],
            ),
            hybrid=dict(
                type=bool,
                optional=True,
                default=False,
            ),
        ),
    )

    _HYBRID_CLIM_ROLE = "ClimatologicalModelState"

    @property
    def actual_totalnumber(self):
        """The total number of members (times 2 if hybrid...)."""
        parent_totalnumber = super().actual_totalnumber
        return parent_totalnumber * 2 if self.hybrid else parent_totalnumber

    def prepare(self, rh, opts):
        """Default pre-link for the initial condition file"""
        super().prepare(rh, opts)
        # Legacy...
        for num, sec in enumerate(
            sorted(
                self.context.sequence.effective_inputs(role="Rawfiles"),
                key=self._members_sorting_key,
            ),
            start=1,
        ):
            repname = sec.rh.container.localpath()
            radical = repname.split("_")[0] + "_D{:03d}_L{:s}"
            for filename in self.system.listdir(repname):
                level = re.search(r"_L(\d+)$", filename)
                if level is not None:
                    self.system.softlink(
                        self.system.path.join(repname, filename),
                        radical.format(num, level.group(1)),
                    )
        # Legacy...
        for num, sec in enumerate(
            sorted(
                self.context.sequence.effective_inputs(role="LaggedEnsemble"),
                key=self._members_sorting_key,
            ),
            start=1,
        ):
            repname = sec.rh.container.localpath()
            radical = repname.split("_")[0] + "_{:03d}"
            self.system.softlink(repname, radical.format(num))
        # Requesting Hybrid computations ?
        if self.hybrid:
            hybstuff = self.context.sequence.effective_inputs(
                role=self._HYBRID_CLIM_ROLE
            )
            hybformat = hybstuff[0].rh.container.actualfmt
            totalnumber = (
                self.actual_nbe * self.actual_nresx
                if self.padding
                else self.actual_nbe
            )
            for i, tnum in enumerate(
                range(totalnumber + 1, 2 * totalnumber + 1)
            ):
                innc = self.naming_convention(
                    kind="edainput",
                    variant=self.kind,
                    totalnumber=self.actual_totalnumber,
                    rh=rh,
                    actualfmt=hybformat,
                )
                logger.info(
                    "Soft-Linking %s to %s",
                    hybstuff[i].rh.container.localpath(),
                    innc(number=tnum),
                )
                self.system.softlink(
                    hybstuff[i].rh.container.localpath(), innc(number=tnum)
                )
