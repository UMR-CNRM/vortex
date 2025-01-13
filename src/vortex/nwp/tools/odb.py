"""
Common interest classes to help setup the ODB software environment.
"""

import re

from bronx.fancies import loggers
from bronx.stdtypes import date as bdate
import footprints

from vortex.algo.components import (
    AlgoComponentDecoMixin,
    AlgoComponentError,
    algo_component_deco_mixin_autodoc,
)
from vortex import config
from vortex.layout.dataflow import intent

from ..syntax.stdattrs import ArpIfsSimplifiedCycle

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class TimeSlots:
    """Handling of assimilation time slots."""

    def __init__(
        self, nslot=7, start="-PT3H", window="PT6H", chunk=None, center=True
    ):
        if isinstance(nslot, str):
            info = [x.strip() for x in nslot.split("/")]
            nslot = info[0]
            if len(info) > 1:
                start = info[1]
            if len(info) > 2:
                window = info[2]
            if len(info) > 3:
                if re.match("^regular", info[3]):
                    center = False
                else:
                    chunk = info[3]
        self.nslot = int(nslot)
        self.center = center if self.nslot > 1 else False
        self.start = bdate.Period(start)
        self.window = bdate.Period(window)
        if chunk is None:
            cslot = self.nslot - 1 if self.center else self.nslot
            chunk = (
                "PT" + str((self.window.length // max(1, cslot)) // 60) + "M"
            )
        self.chunk = self.window if self.nslot < 2 else bdate.Period(chunk)

    def __eq__(self, other):
        if isinstance(other, str):
            try:
                other = TimeSlots(other)
            except ValueError:
                pass
        return (
            isinstance(other, TimeSlots)
            and self.nslot == other.nslot
            and self.center == other.center
            and self.start == other.start
            and self.window == other.window
            and self.chunk == other.chunk
        )

    def __str__(self):
        chunky = self.chunk.isoformat() if self.center else "regular"
        return "{0.nslot:d}/{1:s}/{2:s}/{3:s}".format(
            self, self.start.isoformat(), self.window.isoformat(), chunky
        )

    def __repr__(self, *args, **kwargs):
        return super().__repr__()[:-1] + " | {!s}>".format(self)

    def as_slots(self):
        """Return a list of slots in seconds."""
        if self.center:
            slots = [
                self.chunk.length,
            ] * self.nslot
            nb = self.window.length // self.chunk.length
            if nb != self.nslot:
                slots[0] = slots[-1] = self.chunk.length // 2
        else:
            islot = self.window.length // self.nslot
            slots = [
                islot,
            ] * self.nslot
        return slots

    def as_centers_fromstart(self):
        """Return time slots centers as a list of Period objects."""
        slots = self.as_slots()
        fromstart = []
        acc = 0
        for i in range(len(slots)):
            fromstart.append(acc + slots[i] / 2)
            acc += slots[i]
        if self.center and (
            self.window.length // self.chunk.length != self.nslot
        ):
            fromstart[0] = 0
            fromstart[-1] = self.window.length
        return [bdate.Period(seconds=t) for t in fromstart]

    def as_bounds(self, date):
        """Return time slots as a list of compact date values."""
        date = bdate.Date(date)
        boundlist = [
            date + self.start,
        ]
        for x in self.as_slots():
            boundlist.append(boundlist[-1] + x)
        boundlist = [x.compact() for x in boundlist]
        return boundlist

    @property
    def leftmargin(self):
        """Return length in minutes from left margin of the window."""
        return int(self.start.total_seconds()) // 60

    @property
    def rightmargin(self):
        """Return length in minutes from rigth margin of the window."""
        return int((self.start + self.window).total_seconds()) // 60

    def as_environment(self):
        """Return a dictionary of ready-to-export variables that describe the timeslots."""
        thelen = (
            self.chunk.length // 60 if self.center and self.nslot > 1 else 0
        )
        return dict(
            BATOR_WINDOW_LEN=self.window.length // 60,
            BATOR_WINDOW_SHIFT=int(self.start.total_seconds()) // 60,
            BATOR_SLOT_LEN=thelen,
            BATOR_CENTER_LEN=thelen,
        )

    def as_file(self, date, filename):
        """Fill the specified ``filename`` wih the current list of time slots at this ``date``."""
        with open(filename, "w") as fd:
            for x in self.as_bounds(date):
                fd.write(str(x) + "\n")
            nbx = fd.tell()
        return nbx


class OdbDriver:
    """A dedicated class for handling some ODB settings."""

    def __init__(self, cycle, sh=None, env=None):
        """
        A quite challenging initialisation since cycle, sh, env and target
        should be provided...
        """
        self.cycle = cycle
        self.sh = sh
        if self.sh is None:
            logger.critical(
                "%s created with a proper shell access [%s]",
                self.__class__,
                self,
            )
        self.env = env
        if self.env is None:
            logger.critical(
                "%s created with a proper environment access [%s]",
                self.__class__,
                self,
            )

    def setup(self, date, npool=1, nslot=1, iomethod=1, layout="ecma"):
        """Setup given environment with default ODB env variables."""

        (logger.info("ODB: generic setup called."),)
        self.env.update(
            ODB_CMA=layout.upper(),
            ODB_IO_METHOD=iomethod,
        )

        self.env.default(
            ODB_DEBUG=0,
            ODB_CTX_DEBUG=0,
            ODB_REPRODUCIBLE_SEQNO=4,
            ODB_STATIC_LINKING=1,
            ODB_ANALYSIS_DATE=date.ymd,
            ODB_ANALYSIS_TIME=date.hm + "00",
            TO_ODB_ECMWF=0,
            TO_ODB_SWAPOUT=0,
        )

        if iomethod == 4:
            self.env.default(
                ODB_IO_GRPSIZE=npool,
                ODB_IO_FILESIZE=128,
            )

        if self.sh.path.exists("IOASSIGN"):
            self.env.default(
                IOASSIGN=self.sh.path.abspath("IOASSIGN"),
            )

    def force_overwrite_method(self):
        """Force ODB_OVERWRITE_METHOD if necessary."""
        if not int(self.env.get("ODB_OVERWRITE_METHOD", 0)):
            logger.info(
                "ODB: Some input ODB databases are read-only. Setting ODB_OVERWRITE_METHOD to 1."
            )
            self.env.ODB_OVERWRITE_METHOD = 1

    def _process_layout_dbpath(self, layout, dbpath=None):
        """Normalise **layout** and **dbpath**."""
        layout = layout.upper()
        thispwd = self.sh.path.abspath(self.sh.getcwd())
        if dbpath is None:
            dbpath = self.sh.path.join(thispwd, layout)
        return layout, dbpath, thispwd

    def fix_db_path(self, layout, dbpath=None, env=None):
        """Setup the path to the **layout** database."""
        if env is None:
            env = self.env
        layout, dbpath, _ = self._process_layout_dbpath(layout, dbpath)
        logger.info("ODB: Fix %s path: %s", layout, dbpath)
        env["ODB_SRCPATH_{:s}".format(layout)] = dbpath
        env["ODB_DATAPATH_{:s}".format(layout)] = dbpath

    @property
    def _default_iocreate_path(self):
        """The location to the default create_ioassign utility."""
        return self.sh.path.join(
            config.from_config(section="nwp-tools", key="odb"),
            config.get_from_config_w_default(
                section="nwp-tools",
                key="iocreate_cmd",
                default="create_ioassign",
            ),
        )

    @property
    def _default_iomerge_path(self):
        """The location to the default merge_ioassign utility."""
        return self.sh.path.join(
            config.from_config(section="nwp-tools", key="odb"),
            config.get_from_config_w_default(
                section="nwp-tools",
                key="iomerge_cmd",
                default="merge_ioassign",
            ),
        )

    def ioassign_create(
        self,
        ioassign="ioassign.x",
        npool=1,
        layout="ecma",
        dbpath=None,
        iocreate_path=None,
    ):
        """Build IO-Assign table."""
        layout, dbpath, _ = self._process_layout_dbpath(layout, dbpath)
        if iocreate_path is None:
            iocreate_path = self._default_iocreate_path
        ioassign = self.sh.path.abspath(ioassign)
        self.sh.xperm(ioassign, force=True)
        self.sh.mkdir(dbpath)
        with self.env.clone() as lenv:
            lenv["ODB_IOASSIGN_BINARY"] = ioassign
            self.fix_db_path(layout, dbpath, env=lenv)
            self.sh.spawn(
                [
                    iocreate_path,
                    "-d" + dbpath,
                    "-l" + layout,
                    "-n" + str(npool),
                ],
                output=False,
            )
        return dbpath

    def ioassign_merge(
        self,
        ioassign="ioassign.x",
        layout="ecma",
        odbnames=None,
        dbpath=None,
        iomerge_path=None,
        iocreate_path=None,
    ):
        """Build IO-Assign table."""
        layout, dbpath, thispwd = self._process_layout_dbpath(layout, dbpath)
        if iomerge_path is None:
            iomerge_path = self._default_iomerge_path
        if iocreate_path is None:
            iocreate_path = self._default_iocreate_path
        iocmd = [iomerge_path]
        ioassign = self.sh.path.abspath(ioassign)
        self.sh.xperm(ioassign, force=True)
        with self.sh.cdcontext(dbpath, create=True):
            iocmd.extend(["-d", thispwd])
            for dbname in odbnames:
                iocmd.extend(["-t", dbname])
            with self.env.clone() as lenv:
                lenv["ODB_IOASSIGN_BINARY"] = ioassign
                if "ODB_IOCREATE_COMMAND" not in lenv:
                    lenv["ODB_IOCREATE_COMMAND"] = iocreate_path
                self.fix_db_path(layout, dbpath, env=lenv)
                self.sh.spawn(iocmd, output=False)
        return dbpath

    def _ioassign_process(self, dbpaths, wmode):
        with open("IOASSIGN", wmode) as fhgather:
            for dbpath in dbpaths:
                with open(self.sh.path.join(dbpath, "IOASSIGN")) as fhlay:
                    for line in fhlay:
                        fhgather.write(line)

    def ioassign_gather(self, *dbpaths):
        """Gather IOASSIGN data from **dbpaths** databases and create a global IOASSIGN file."""
        logger.info(
            "ODB: creating a global IOASSIGN file from: %s",
            ",".join([self.sh.path.basename(db) for db in dbpaths]),
        )
        self._ioassign_process(dbpaths, "w")

    def ioassign_append(self, *dbpaths):
        """Append IOASSIGN data from **dbpaths** databases into the global IOASSIGN file."""
        logger.info(
            "ODB: extending the IOASSIGN file with: %s",
            ",".join([self.sh.path.basename(db) for db in dbpaths]),
        )
        self._ioassign_process(dbpaths, "a")

    def shuffle_setup(self, slots, mergedirect=False, ccmadirect=False):
        """Setup environment variables to control ODB shuffle behaviour.

        :param bool mergedirect: Run the shuffle procedure on the input database.
        :param bool ccmadirect: Create a CCMA database at the end of the run.
        """
        logger.info(
            "ODB: shuffle_setup: mergedirect=%s, ccmadirect=%s",
            str(mergedirect),
            str(ccmadirect),
        )
        if mergedirect or ccmadirect:
            self.env.update(
                ODB_CCMA_TSLOTS=slots.nslot,
            )
            self.env.default(
                ODB_CCMA_LEFT_MARGIN=slots.leftmargin,
                ODB_CCMA_RIGHT_MARGIN=slots.rightmargin,
            )
            if mergedirect:
                self.env.default(ODB_MERGEODB_DIRECT=1)
            if ccmadirect:
                self.env.update(ODB_CCMA_CREATE_DIRECT=1)

    def create_poolmask(self, layout, dbpath=None):
        """Request the poolmask file creation."""
        layout, dbpath, _ = self._process_layout_dbpath(layout, dbpath)
        logger.info(
            "ODB: requesting poolmask file for: %s (layout=%s).",
            dbpath,
            layout,
        )
        self.env.update(
            ODB_CCMA_CREATE_POOLMASK=1,
            ODB_CCMA_POOLMASK_FILE=self.sh.path.join(
                dbpath, layout + ".poolmask"
            ),
        )

    def change_layout(self, layout, layout_new, dbpath=None):
        """Make the appropriate renaming of files in ECMA to CCMA."""
        layout, dbpath, _ = self._process_layout_dbpath(layout, dbpath)
        layout_new = layout_new.upper()
        logger.info(
            "ODB: changing layout (%s -> %s) for %s.",
            layout,
            layout_new,
            dbpath,
        )
        to_cleanup = set()
        for f in self.sh.ls(dbpath):
            if self.sh.path.islink(self.sh.path.join(dbpath, f)):
                fullpath = self.sh.path.join(dbpath, f)
                target = self.sh.readlink(fullpath)
                self.sh.unlink(fullpath)
                self.sh.symlink(
                    target.replace(layout, layout_new),
                    fullpath.replace(layout, layout_new),
                )
                continue
            if f in [n.format(layout) for n in ("{:s}.dd", "{:s}.flags")]:
                self.sh.mv(
                    self.sh.path.join(dbpath, f),
                    self.sh.path.join(dbpath, f.replace(layout, layout_new)),
                )
            if f in [
                n.format(layout)
                for n in (
                    "{:s}.iomap",
                    "{:s}.sch",
                    "{:s}.IOASSIGN",
                    "IOASSIGN.{:s}",
                    "IOASSIGN",
                )
            ]:
                tmp_target = self.sh.path.join(dbpath, f + ".tmp_new")
                with open(self.sh.path.join(dbpath, f)) as inodb:
                    with open(tmp_target, "w") as outodb:
                        for line in inodb:
                            outodb.write(line.replace(layout, layout_new))
                self.sh.mv(
                    tmp_target,
                    self.sh.path.join(dbpath, f.replace(layout, layout_new)),
                )
                if layout in f:
                    to_cleanup.add(self.sh.path.join(dbpath, f))
        for f_name in to_cleanup:
            self.sh.rm(f_name)


#: Footprint's attributes needed to ODB to setup properly
odbmix_attributes = footprints.Footprint(
    info="Abstract ODB footprints' attributes.",
    attr=dict(
        npool=dict(
            info="The number of pool(s) in the ODB database.",
            type=int,
            optional=True,
            default=1,
        ),
        iomethod=dict(
            info="The io_method of the ODB database.",
            type=int,
            optional=True,
            default=1,
            doc_zorder=-50,
        ),
        slots=dict(
            info="The timeslots of the assimilation window.",
            type=TimeSlots,
            optional=True,
            default=TimeSlots(7, chunk="PT1H"),
        ),
        virtualdb=dict(
            info="The type of the virtual ODB database.",
            optional=True,
            default="ecma",
            access="rwx",
            doc_visibility=footprints.doc.visibility.ADVANCED,
        ),
        date=dict(
            info="The current run date.",
            optional=True,
            access="rwx",
            type=bdate.Date,
            doc_zorder=-50,
        ),
        ioassign=dict(
            info="The path to the ioassign binary (needed for merge/create actions",
            optional=True,
            default="ioassign.x",
        ),
    ),
)


@algo_component_deco_mixin_autodoc
class OdbComponentDecoMixin(AlgoComponentDecoMixin):
    """Handle ODB settings in AlgoComponents.

    This mixin class is intended to be used with AlgoComponent classes. It will
    automatically add footprints' arguments related to ODB
    (see :data:`odbmix_attributes`), set up generic ODB environment variables
    (:meth:`_odbobj_setup`) and provides a :attr:`odb` property that gives
    access to a properly initialised :class:`OdbDriver` object that can be used
    directly in AlgoComponents.

    In addition it provides directly some utility methods that can be called
    manually if needed.
    """

    _MIXIN_EXTRA_FOOTPRINTS = [
        odbmix_attributes,
    ]

    def _odbobj_init(self, rh, opts):  # @UnusedVariable
        """Setup the OdbDriver object."""
        cycle = ArpIfsSimplifiedCycle("cy01")
        if rh and hasattr(rh.resource, "cycle"):
            cycle = rh.resource.cycle
        self._odb = OdbDriver(
            cycle=cycle,
            sh=self.system,
            env=self.env,
        )
        if self.system.path.exists(self.ioassign):
            self._x_ioassign = self.system.path.abspath(self.ioassign)
        else:
            # Legacy...
            self._x_ioassign = self.ioassign

    def _odbobj_setup(self, rh, opts):  # @UnusedVariable
        """Setup the ODB object."""
        self.odb.setup(
            layout=self.virtualdb,
            date=self.date,
            npool=self.npool,
            nslot=self.slots.nslot,
            iomethod=self.iomethod,
        )

    _MIXIN_PREPARE_PREHOOKS = (_odbobj_init,)
    _MIXIN_PREPARE_HOOKS = (_odbobj_setup,)

    @property
    def odb(self):
        """Access to a properly initialised :class:`OdbDriver` object."""
        if not hasattr(self, "_odb"):
            raise RuntimeError("Uninitialised *odb* object.")
        return self._odb

    def lookupodb(self, fatal=True):
        """Return a list of effective input resources which are odb observations."""
        allodb = [
            x
            for x in self.context.sequence.effective_inputs(
                kind="observations"
            )
            if x.rh.container.actualfmt == "odb"
        ]
        allodb.sort(key=lambda s: s.rh.resource.part)
        if not allodb and fatal:
            logger.critical("Missing ODB input data for %s", self.fullname())
            raise ValueError("Missing ODB input data")
        return allodb

    def odb_date_and_layout_from_sections(self, odbsections):
        """
        Look into the **odsections** section list in order to find the current
        run date and ODB database layout.
        """
        alllayouts = {s.rh.resource.layout for s in odbsections}
        alldates = {s.rh.resource.date for s in odbsections}
        if len(alllayouts) != 1:
            raise AlgoComponentError("Inconsistent ODB layouts")
        if len(alldates) != 1:
            raise AlgoComponentError("Inconsistent ODB dates")
        self.virtualdb = alllayouts.pop()
        self.date = alldates.pop()
        logger.info(
            "ODB: Detected from ODB database(s). self.date=%s, self.virtualdb=%s.",
            self.date.stdvortex,
            self.virtualdb,
        )

    def _odb_find_ioassign_script(self, purpose):
        """Look for ioassign script of *purpose" attribute, return path."""
        scripts = [
            x.rh.container.abspath
            for x in self.context.sequence.effective_inputs(
                kind="ioassign_script"
            )
            if x.rh.resource.purpose == purpose
        ]
        if len(scripts) > 1:
            raise AlgoComponentError(
                "More than one purpose={} ioassign_script found in resources."
            )
        elif len(scripts) == 1:
            self.system.xperm(scripts[0], force=True)
            return scripts[0]
        else:
            return None

    def odb_merge_if_needed(self, odbsections, subdir="."):
        """
        If multiple ODB databases are listed in the **odsections** section list,
        start an ODB merge.

        :return: The path to the ODB database (the virtual database if a merge is
                 performed).
        """
        if len(odbsections) > 1 or self.virtualdb.lower() == "ecma":
            logger.info("ODB: merge for: %s.", self.virtualdb)
            iomerge_p = self._odb_find_ioassign_script("merge")
            iocreate_p = self._odb_find_ioassign_script("create")
            with self.system.cdcontext(subdir):
                virtualdb_path = self.odb.ioassign_merge(
                    layout=self.virtualdb,
                    ioassign=self._x_ioassign,
                    odbnames=[x.rh.resource.part for x in odbsections],
                    iomerge_path=iomerge_p,
                    iocreate_path=iocreate_p,
                )
        else:
            virtualdb_path = self.system.path.abspath(
                odbsections[0].rh.container.localpath()
            )
        return virtualdb_path

    def odb_create_db(self, layout, dbpath=None):
        """Create a new empty ODB database.

        :param str layout: The new database layout
        :param str dbpath: The path to the new database (current_dir/layout if omitted)
        :return: The path to the new ODB database.
        """
        dbout = self.odb.ioassign_create(
            layout=layout,
            npool=self.npool,
            ioassign=self._x_ioassign,
            dbpath=dbpath,
            iocreate_path=self._odb_find_ioassign_script("create"),
        )
        logger.info("ODB: database created: %s (layout=%s).", dbout, layout)
        return dbout

    def odb_handle_raw_dbs(self):
        """Look for extras ODB raw databases and fix the environment accordingly."""
        odbraw = [
            x.rh
            for x in self.context.sequence.effective_inputs(kind="odbraw")
            if x.rh.container.actualfmt == "odb"
        ]
        if not odbraw:
            logger.error("No ODB raw databases found.")
        else:
            for rraw in odbraw:
                rawpath = rraw.container.localpath()
                self.odb.fix_db_path(rraw.resource.layout, rawpath)
                for badlink in [
                    bl
                    for bl in self.system.glob(
                        self.system.path.join(rawpath, "*.h")
                    )
                    if self.system.path.islink(bl)
                    and not self.system.path.exists(bl)
                ]:
                    self.system.unlink(badlink)
            self.odb.ioassign_append(
                *[rraw.container.localpath() for rraw in odbraw]
            )
        return odbraw

    def odb_rw_or_overwrite_method(self, *dbsections):
        """Are the input databases fetch with intent=inout ?"""
        needs_work = [s for s in dbsections if s.intent == intent.IN]
        if needs_work:
            self.odb.force_overwrite_method()
