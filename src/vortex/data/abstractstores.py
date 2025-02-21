# pylint: disable=unused-argument

"""
This module handles store objects in charge of physically accessing resources.
Store objects use the :mod:`footprints` mechanism.
"""

import copy

from bronx.fancies import loggers
from bronx.patterns import observer
from bronx.stdtypes import date
from bronx.system import hash as hashutils
import footprints

from vortex import sessions
from vortex.config import from_config, ConfigurationError
from vortex.syntax.stdattrs import (
    hashalgo,
    hashalgo_avail_list,
    compressionpipeline,
)
from vortex.tools import storage
from vortex.tools import compression
from vortex.tools.systems import ExecutionError
from vortex.syntax.stdattrs import Namespace

#: Export base class
__all__ = ["Store"]

logger = loggers.getLogger(__name__)

OBSERVER_TAG = "Stores-Activity"

CACHE_PUT_INTENT = "in"
CACHE_GET_INTENT_DEFAULT = "in"

ARCHIVE_PUT_INTENT = "in"
ARCHIVE_GET_INTENT_DEFAULT = "in"


def observer_board(obsname=None):
    """Proxy to :func:`footprints.observers.get`."""
    if obsname is None:
        obsname = OBSERVER_TAG
    return observer.get(tag=obsname)


class Store(footprints.FootprintBase):
    """Root class for any :class:`Store` subclasses."""

    _abstract = True
    _collector = ("store",)
    _footprint = [
        hashalgo,
        dict(
            info="Default store",
            attr=dict(
                scheme=dict(alias=("protocol",)),
                netloc=dict(type=Namespace, alias=("domain", "namespace")),
                storetrack=dict(
                    type=bool,
                    default=True,
                    optional=True,
                ),
                readonly=dict(
                    type=bool,
                    optional=True,
                    default=False,
                ),
            ),
        ),
    ]

    def __init__(self, *args, **kw):
        logger.debug("Abstract store init %s", self.__class__)
        sh = kw.pop("system", sessions.system())
        super().__init__(*args, **kw)
        self._sh = sh
        self._observer = observer_board()
        self._observer.notify_new(self, dict())
        self._cpipeline = False
        self.delayed = False

    @property
    def realkind(self):
        return "store"

    @property
    def system(self):
        """Shortcut to current system interface."""
        return self._sh

    def use_cache(self):
        """Boolean function to check if the current store uses a local cache."""
        return False

    def use_archive(self):
        """Boolean function to check if the current store uses a remote archive."""
        return not self.use_cache()

    def has_fast_check(self):
        """How fast and reliable is a check call ?"""
        return False

    def _observer_notify(self, action, rc, remote, local=None, options=None):
        strack = options is None or options.get("obs_notify", True)
        if self.storetrack and strack:
            infos = dict(action=action, status=rc, remote=remote)
            # Is a localpath provided ?
            if local is not None:
                infos["local"] = local
            # We may want to cheat on the localpath...
            if options is not None and "obs_overridelocal" in options:
                infos["local"] = options["obs_overridelocal"]
            self._observer.notify_upd(self, infos)

    def notyet(self, *args):
        """
        Internal method to be used as a critical backup method
        when a specific method is not yet defined.
        """
        logger.critical("Scheme %s not yet implemented", self.scheme)

    @property
    def writeable(self):
        return not self.readonly

    def enforce_readonly(self):
        if self.readonly:
            raise OSError("This store is in readonly mode")

    @staticmethod
    def _verbose_log(options, level, *kargs, **kwargs):
        slevel = kwargs.pop("slevel", "debug")
        if options is not None and options.get("silent", False):
            level = slevel
        getattr(logger, level)(*kargs, **kwargs)

    @property
    def _actual_cpipeline(self):
        """Check if the current store has a CompressionPipeline."""
        if self._cpipeline is False:
            cpipeline_desc = getattr(self, "store_compressed", None)
            if cpipeline_desc is not None:
                self._cpipeline = compression.CompressionPipeline(
                    self.system, cpipeline_desc
                )
            else:
                self._cpipeline = None
        return self._cpipeline

    @property
    def tracking_extraargs(self):
        """When tracking get/put request: extra args that will be added to the URI query."""
        return dict()

    def _incache_inarchive_check(self, options):
        rc = True
        incache = options.get("incache", False)
        inarchive = options.get("inarchive", False)
        if incache and inarchive:
            raise ValueError(
                "'incache=True' and 'inarchive=True' are mutually exclusive"
            )
        if incache and not self.use_cache():
            self._verbose_log(
                options,
                "info",
                'Skip this "%s" store because a cache is requested',
                self.__class__,
            )
            rc = False
        if inarchive and not self.use_archive():
            self._verbose_log(
                options,
                "info",
                'Skip this "%s" store because an archive is requested',
                self.__class__,
            )
            rc = False
        return rc

    def _hash_check_or_delete(self, callback, remote, options):
        """Check or delete a hash file."""
        if (self.storehash is None) or (
            remote["path"].endswith("." + self.storehash)
        ):
            return True
        options = self._hash_store_defaults(options)
        remote = remote.copy()
        remote["path"] = remote["path"] + "." + self.storehash
        return callback(remote, options)

    @staticmethod
    def _options_fixup(options):
        return dict() if options is None else options

    def check(self, remote, options=None):
        """Proxy method to dedicated check method according to scheme."""
        logger.debug("Store check from %s", remote)
        options = self._options_fixup(options)
        if not self._incache_inarchive_check(options):
            return False
        rc = getattr(self, self.scheme + "check", self.notyet)(remote, options)
        self._observer_notify("check", rc, remote, options=options)
        return rc

    def locate(self, remote, options=None):
        """Proxy method to dedicated locate method according to scheme."""
        options = self._options_fixup(options)
        logger.debug("Store locate %s", remote)
        if not self._incache_inarchive_check(options):
            return None
        return getattr(self, self.scheme + "locate", self.notyet)(
            remote, options
        )

    def list(self, remote, options=None):
        """Proxy method to dedicated list method according to scheme."""
        options = self._options_fixup(options)
        logger.debug("Store list %s", remote)
        if not self._incache_inarchive_check(options):
            return None
        return getattr(self, self.scheme + "list", self.notyet)(
            remote, options
        )

    def prestage_advertise(self, remote, options=None):
        """Use the Stores-Activity observer board to advertise the prestaging request.

        Hopefully, something will register to the ober board in order to process
        the request.
        """
        options = self._options_fixup(options)
        logger.debug("Store prestage through hub %s", remote)
        infos_cb = getattr(self, self.scheme + "prestageinfo", None)
        if infos_cb:
            infodict = infos_cb(remote, options)
            infodict.setdefault("issuerkind", self.realkind)
            infodict.setdefault("scheme", self.scheme)
            if options and "priority" in options:
                infodict["priority"] = options["priority"]
            infodict["action"] = "prestage_req"
            self._observer.notify_upd(self, infodict)
        else:
            logger.info(
                "Prestaging is not supported for scheme: %s", self.scheme
            )
        return True

    def prestage(self, remote, options=None):
        """Proxy method to dedicated prestage method according to scheme."""
        options = self._options_fixup(options)
        logger.debug("Store prestage %s", remote)
        if not self._incache_inarchive_check(options):
            return True
        return getattr(
            self, self.scheme + "prestage", self.prestage_advertise
        )(remote, options)

    @staticmethod
    def _hash_store_defaults(options):
        """Update default options when fetching hash files."""
        options = options.copy()
        options["obs_notify"] = False
        options["fmt"] = "ascii"
        options["intent"] = CACHE_GET_INTENT_DEFAULT
        options["auto_tarextract"] = False
        options["auto_dirextract"] = False
        return options

    def _hash_get_check(self, callback, remote, local, options):
        """Update default options when fetching hash files."""
        if (self.storehash is None) or (
            remote["path"].endswith("." + self.storehash)
        ):
            return True
        if isinstance(local, str) and not self.system.path.isfile(local):
            logger.info(
                "< %s > is not a plain file. The control sum can't be checked.",
                local,
            )
            return True
        options = self._hash_store_defaults(options)
        remote = remote.copy()
        remote["path"] = (
            remote["path"] + "." + self.storehash
        )  # Name of the hash file
        remote["query"].pop("extract", None)  # Ignore any extract request
        try:
            tempcontainer = None
            try:
                # First, try to fetch the sum in a real file
                # (in order to potentially use ftserv...)
                tempcontainer = footprints.proxy.container(
                    shouldfly=True, mode="rb"
                )
                try:
                    rc = callback(remote, tempcontainer.iotarget(), options)
                except (OSError, ExecutionError):
                    # This may happen if the user has insufficient rights on
                    # the current directory
                    tempcontainer = footprints.proxy.container(
                        incore=True, mode="w+b"
                    )
                    rc = callback(remote, tempcontainer.iotarget(), options)
            except (OSError, ExecutionError):
                logger.warning(
                    "Something went very wrong when fetching the hash file ! (assuming rc=False)"
                )
                rc = False
            # check the hash key
            hadapt = hashutils.HashAdapter(self.storehash)
            rc = rc and hadapt.filecheck(local, tempcontainer)
            if rc:
                logger.info("%s hash sanity check succeeded.", self.storehash)
            else:
                logger.warning("%s hash sanity check failed.", self.storehash)
        finally:
            if tempcontainer is not None:
                tempcontainer.clear()
        return rc

    def _actual_get(self, action, remote, local, options, result_id=None):
        """Proxy method to dedicated get method according to scheme."""
        logger.debug("Store %s from %s to %s", action, remote, local)
        if not self._incache_inarchive_check(options):
            return False
        if not options.get("insitu", False) or self.use_cache():
            if result_id:
                rc = getattr(self, self.scheme + action, self.notyet)(
                    result_id, remote, local, options
                )
            else:
                rc = getattr(self, self.scheme + action, self.notyet)(
                    remote, local, options
                )
            self._observer_notify(
                "get", rc, remote, local=local, options=options
            )
            return rc
        else:
            logger.error("Only cache stores can be used when insitu is True.")
            return False

    def get(self, remote, local, options=None):
        """Proxy method to dedicated get method according to scheme."""
        options = self._options_fixup(options)
        return self._actual_get("get", remote, local, options)

    def earlyget(self, remote, local, options=None):
        options = self._options_fixup(options)
        """Proxy method to dedicated earlyget method according to scheme."""
        logger.debug("Store earlyget from %s to %s", remote, local)
        if not self._incache_inarchive_check(options):
            return None
        rc = None
        if not options.get("insitu", False) or self.use_cache():
            available_dget = getattr(self, self.scheme + "earlyget", None)
            if available_dget is not None:
                rc = available_dget(remote, local, options)
        return rc

    def finaliseget(self, result_id, remote, local, options=None):
        options = self._options_fixup(options)
        """Proxy method to dedicated finaliseget method according to scheme."""
        return self._actual_get(
            "finaliseget", remote, local, options, result_id=result_id
        )

    def _hash_put(self, callback, local, remote, options):
        """Put a hash file next to the 'real' file."""
        if (self.storehash is None) or (
            remote["path"].endswith("." + self.storehash)
        ):
            return True
        options = self._hash_store_defaults(options)
        remote = remote.copy()
        remote["path"] = remote["path"] + "." + self.storehash
        # Generate the hash sum
        hadapt = hashutils.HashAdapter(self.storehash)
        tmplocal = hadapt.file2hash_fh(local)
        # Write it whereever the original store wants to.
        return callback(tmplocal, remote, options)

    def put(self, local, remote, options=None):
        """Proxy method to dedicated put method according to scheme."""
        options = self._options_fixup(options)
        logger.debug("Store put from %s to %s", local, remote)
        self.enforce_readonly()
        if not self._incache_inarchive_check(options):
            return True
        filtered = False
        if options is not None and "urifilter" in options:
            filtered = options["urifilter"](self, remote)
        if filtered:
            rc = True
            logger.info(
                "This remote URI has been filtered out: we are skipping it."
            )
        else:
            dryrun = False
            if options is not None and "dryrun" in options:
                dryrun = options["dryrun"]
            rc = dryrun or getattr(self, self.scheme + "put", self.notyet)(
                local, remote, options
            )
            self._observer_notify(
                "put", rc, remote, local=local, options=options
            )
        return rc

    def delete(self, remote, options=None):
        """Proxy method to dedicated delete method according to scheme."""
        options = self._options_fixup(options)
        logger.debug("Store delete from %s", remote)
        self.enforce_readonly()
        if not self._incache_inarchive_check(options):
            return True
        rc = getattr(self, self.scheme + "delete", self.notyet)(
            remote, options
        )
        self._observer_notify("del", rc, remote, options=options)
        return rc


class MultiStore(footprints.FootprintBase):
    """Agregate various :class:`Store` items."""

    _abstract = True
    _collector = ("store",)
    _footprint = [
        compressionpipeline,  # Not used by cache stores but ok, just in case...
        hashalgo,
        dict(
            info="Multi store",
            attr=dict(
                scheme=dict(alias=("protocol",)),
                netloc=dict(type=Namespace, alias=("domain", "namespace")),
                refillstore=dict(
                    type=bool,
                    optional=True,
                    default=False,
                ),
                storehash=dict(
                    values=hashalgo_avail_list,
                ),
                # ArchiveStores only be harmless for others...
                storage=dict(
                    optional=True,
                    default=None,
                ),
                storetube=dict(
                    optional=True,
                ),
                storeroot=dict(
                    optional=True,
                ),
            ),
        ),
    ]

    def __init__(self, *args, **kw):
        logger.debug("Abstract multi store init %s", self.__class__)
        sh = kw.pop("system", sessions.system())
        super().__init__(*args, **kw)
        self._sh = sh
        self._openedstores = self.loadstores()
        self.delayed = False

    @property
    def realkind(self):
        return "multistore"

    @property
    def system(self):
        """Shortcut to current system interface."""
        return self._sh

    @staticmethod
    def _verbose_log(options, level, *kargs, **kwargs):
        slevel = kwargs.pop("slevel", "debug")
        if options is not None and options.get("silent", False):
            level = slevel
        getattr(logger, level)(*kargs, **kwargs)

    def loadstores(self):
        """
        Load default stores during the initialisation of the current object.
        Stores could be reloaded at any time. The current method provides
        a default loading mechanism through the actual module :func:`load` function
        and an alternate list of footprint descriptors as returned by method
        :func:`alternates_fp`.
        """
        activestores = list()
        for desc in self.alternates_fp():
            xstore = footprints.proxy.store(**desc)
            if xstore:
                activestores.append(xstore)
        logger.debug(
            "Multistore %s includes active stores %s", self, activestores
        )
        return activestores

    @property
    def openedstores(self):
        return self._openedstores

    def filtered_readable_openedstores(self, remote):  # @UnusedVariable
        return self._openedstores

    def filtered_writeable_openedstores(self, remote):  # @UnusedVariable
        return self._openedstores

    def alternates_scheme(self):
        """Default method returns actual scheme in a tuple."""
        return (self.scheme,)

    def alternates_netloc(self):
        """Abstract method."""
        pass

    def alternates_fpextras(self):
        """Abstract method."""
        return dict()

    def alternates_fp(self):
        """
        Returns a list of anonymous descriptions to be used as footprint entries
        while loading alternates stores.
        """
        return [
            dict(
                system=self.system,
                storehash=self.storehash,
                store_compressed=self.store_compressed,
                storage=self.storage,
                storetube=self.storetube,
                storeroot=self.storeroot,
                scheme=x,
                netloc=y,
                **self.alternates_fpextras(),
            )
            for x in self.alternates_scheme()
            for y in self.alternates_netloc()
        ]

    def use_cache(self):
        """Boolean function to check if any included store uses a local cache."""
        return any([x.use_cache() for x in self.openedstores])

    def use_archive(self):
        """Boolean function to check if any included store uses a remote archive."""
        return any([x.use_archive() for x in self.openedstores])

    def has_fast_check(self):
        """How fast and reliable is a check call ?"""
        return all([x.has_fast_check() for x in self.openedstores])

    @property
    def readonly(self):
        return all([x.readonly for x in self.openedstores])

    @property
    def writeable(self):
        return not self.readonly

    @staticmethod
    def _options_fixup(options):
        return dict() if options is None else options

    def check(self, remote, options=None):
        """Go through internal opened stores and check for the resource."""
        options = self._options_fixup(options)
        logger.debug("Multistore check from %s", remote)
        rc = False
        for sto in self.filtered_readable_openedstores(remote):
            rc = sto.check(remote.copy(), options)
            if rc:
                break
        return rc

    def locate(self, remote, options=None):
        """Go through internal opened stores and locate the expected resource for each of them."""
        options = self._options_fixup(options)
        logger.debug("Multistore locate %s", remote)
        f_ostores = self.filtered_readable_openedstores(remote)
        if not f_ostores:
            return False
        rloc = list()
        for sto in f_ostores:
            logger.debug("Multistore locate at %s", sto)
            tmp_rloc = sto.locate(remote.copy(), options)
            if tmp_rloc:
                rloc.append(tmp_rloc)
        return ";".join(rloc)

    def list(self, remote, options=None):
        """Go through internal opened stores and list the expected resource for each of them."""
        options = self._options_fixup(options)
        logger.debug("Multistore list %s", remote)
        rlist = set()
        for sto in self.filtered_readable_openedstores(remote):
            logger.debug("Multistore list at %s", sto)
            tmp_rloc = sto.list(remote.copy(), options)
            if isinstance(tmp_rloc, (list, tuple, set)):
                rlist.update(tmp_rloc)
            elif tmp_rloc is True:
                return True
        return sorted(rlist)

    def prestage(self, remote, options=None):
        """Go through internal opened stores and prestage the resource for each of them."""
        options = self._options_fixup(options)
        logger.debug("Multistore prestage %s", remote)
        f_ostores = self.filtered_readable_openedstores(remote)
        if not f_ostores:
            return False
        if len(f_ostores) == 1:
            logger.debug("Multistore prestage at %s", f_ostores[0])
            rc = f_ostores[0].prestage(remote.copy(), options)
        else:
            rc = True
            for sto in f_ostores:
                if sto.check(remote.copy(), options):
                    logger.debug("Multistore prestage at %s", sto)
                    rc = sto.prestage(remote.copy(), options)
                    break
        return rc

    def _refilling_get(self, remote, local, options, result_id=None):
        """Go through internal opened stores for the first available resource."""
        rc = False
        refill_in_progress = True
        f_rd_ostores = self.filtered_readable_openedstores(remote)
        if self.refillstore:
            f_wr_ostores = self.filtered_writeable_openedstores(remote)
        get_options = copy.copy(options)
        get_options["silent"] = True
        while refill_in_progress:
            for num, sto in enumerate(f_rd_ostores):
                logger.debug("Multistore get at %s", sto)
                if result_id and num == len(f_rd_ostores) - 1:
                    rc = sto.finaliseget(
                        result_id, remote.copy(), local, get_options
                    )
                    result_id = (
                        None  # result_ids can not be re-used during refill
                    )
                else:
                    rc = sto.get(remote.copy(), local, get_options)
                    if rc:
                        result_id = None  # result_ids can not be re-used during refills
                # Are we trying a refill ? -> find the previous writeable store
                restores = []
                if rc and self.refillstore and num > 0:
                    restores = [
                        ostore
                        for ostore in f_rd_ostores[:num]
                        if (
                            ostore.writeable
                            and ostore in f_wr_ostores
                            and ostore.use_cache()
                        )
                    ]
                # Do the refills and check if one of them succeed
                refill_in_progress = False
                for restore in restores:
                    # Another refill may have filled the gap...
                    if not restore.check(remote.copy(), options):
                        logger.info(
                            "Refill back in writeable store [%s].", restore
                        )
                        try:
                            refill_in_progress = (
                                restore.put(local, remote.copy(), options)
                                and (
                                    options.get(
                                        "intent", CACHE_GET_INTENT_DEFAULT
                                    )
                                    != CACHE_PUT_INTENT
                                )
                            ) or refill_in_progress
                        except (ExecutionError, OSError) as e:
                            logger.error(
                                "An ExecutionError happened during the refill: %s",
                                str(e),
                            )
                            logger.error(
                                "This error is ignored... but that's ugly !"
                            )
                if refill_in_progress:
                    logger.info(
                        "Starting another round because at least one refill succeeded."
                    )
                # Whatever the refill's outcome, that's fine
                if rc:
                    break
        if not rc:
            self._verbose_log(
                options,
                "warning",
                "Multistore get {:s}://{:s}: none of the opened store succeeded.".format(
                    self.scheme, self.netloc
                ),
                slevel="info",
            )
        return rc

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        options = self._options_fixup(options)
        logger.debug("Multistore get from %s to %s", remote, local)
        return self._refilling_get(remote, local, options)

    def earlyget(self, remote, local, options=None):
        options = self._options_fixup(options)
        logger.debug("Multistore earlyget from %s to %s", remote, local)
        f_ostores = self.filtered_readable_openedstores(remote)
        get_options = copy.copy(options)
        if len(f_ostores) > 1:
            first_checkable = all([s.has_fast_check() for s in f_ostores[:-1]])
            # Early-fetch is only available on the last resort store...
            if first_checkable and all(
                [
                    not s.check(remote.copy(), get_options)
                    for s in f_ostores[:-1]
                ]
            ):
                return f_ostores[-1].earlyget(
                    remote.copy(), local, get_options
                )
            else:
                return None
        elif len(f_ostores) == 1:
            return f_ostores[0].earlyget(remote.copy(), local, get_options)
        else:
            return None

    def finaliseget(self, result_id, remote, local, options=None):
        options = self._options_fixup(options)
        logger.debug("Multistore finaliseget from %s to %s", remote, local)
        return self._refilling_get(remote, local, options, result_id=result_id)

    def put(self, local, remote, options=None):
        """Go through internal opened stores and put resource for each of them."""
        options = self._options_fixup(options)
        logger.debug("Multistore put from %s to %s", local, remote)
        f_ostores = self.filtered_writeable_openedstores(remote)
        if not f_ostores:
            logger.warning("Funny attempt to put on an empty multistore...")
            return False
        rc = True
        for sto in [ostore for ostore in f_ostores if ostore.writeable]:
            logger.debug("Multistore put at %s", sto)
            rcloc = sto.put(local, remote.copy(), options)
            logger.debug("Multistore out = %s", rcloc)
            rc = rc and rcloc
        return rc

    def delete(self, remote, options=None):
        """Go through internal opened stores and delete the resource."""
        options = self._options_fixup(options)
        logger.debug("Multistore delete from %s", remote)
        f_ostores = self.filtered_writeable_openedstores(remote)
        rc = False
        for sto in [ostore for ostore in f_ostores if ostore.writeable]:
            logger.debug("Multistore delete at %s", sto)
            rc = sto.delete(remote.copy(), options)
            if not rc:
                break
        return rc


class ArchiveStore(Store):
    """Generic Archive Store."""

    _archives_object_stack = set()

    _abstract = True
    _footprint = [
        compressionpipeline,
        dict(
            info="Generic archive store",
            attr=dict(
                scheme=dict(
                    values=[
                        "inarchive",
                    ],
                ),
                netloc=dict(
                    values=["open.archive.fr"],
                ),
                storehash=dict(
                    values=hashalgo_avail_list,
                ),
                storage=dict(
                    optional=True,
                ),
                storetube=dict(
                    optional=True,
                ),
                storeroot=dict(
                    optional=True,
                ),
                storehead=dict(
                    optional=True,
                ),
                storetrue=dict(
                    type=bool,
                    optional=True,
                    default=True,
                ),
            ),
        ),
    ]

    def __init__(self, *args, **kw):
        logger.debug("Archive store init %s", self.__class__)
        self._archive = None
        self._actual_storage = None
        self._actual_storetube = None
        super().__init__(*args, **kw)
        self._actual_storage = self.storage
        self._actual_storetube = self.storetube

    @property
    def realkind(self):
        return "archivestore"

    @property
    def tracking_extraargs(self):
        tea = super().tracking_extraargs
        if self.storage:
            tea["storage"] = self.storage
        return tea

    def _str_more(self):
        return "archive={!r}".format(self.archive)

    @property
    def underlying_archive_kind(self):
        return "std"

    @property
    def actual_storage(self):
        """This archive network name (potentially read form the configuration file)."""
        if self._actual_storage is None:
            try:
                self._actual_storage = (
                    self.system.env.VORTEX_DEFAULT_STORAGE
                    or self.system.glove.default_fthost
                    or from_config(section="storage", key="address")
                )
            except ConfigurationError as e:
                msg = (
                    "Trying to access storage archive but no "
                    "storage location configured.\n"
                    'Make sure configuration section "section" and key '
                    '"address" exist.\n'
                    "See https://vortex-nwp.readthedocs.io/en/latest/user-guide/configuration.html#storage"
                )
                logger.error(msg)
                raise e
            if self._actual_storage is None:
                raise ValueError("Unable to find the archive network name.")
        return self._actual_storage

    @property
    def actual_storetube(self):
        """This archive network name (potentially read form the configuration file)."""
        if self._actual_storetube is None:
            self._actual_storetube = from_config(
                section="storage",
                key="protocol",
            )
            if self._actual_storetube is None:
                raise ValueError("Unable to find the archive access method.")
        return self._actual_storetube

    def _get_archive(self):
        """Create a new Archive object only if needed."""
        if not self._archive:
            self._archive = footprints.proxy.archives.default(
                kind=self.underlying_archive_kind,
                storage=self.actual_storage,
                tube=self.actual_storetube,
                readonly=self.readonly,
            )
            self._archives_object_stack.add(self._archive)
        return self._archive

    def _set_archive(self, newarchive):
        """Set a new archive reference."""
        if isinstance(newarchive, storage.Archive):
            self._archive = newarchive

    def _del_archive(self):
        """Invalidate internal archive reference."""
        self._archive = None

    archive = property(_get_archive, _set_archive, _del_archive)

    def _inarchiveformatpath(self, remote):
        # Remove extra slashes
        formatted = remote["path"].lstrip(self.system.path.sep)
        # Store head ?
        if self.storehead:
            formatted = self.system.path.join(self.storehead, formatted)
        # Store root (if specified)
        pathroot = remote.get("root", self.storeroot)
        if pathroot is not None:
            formatted = self.system.path.join(pathroot, formatted)
        return formatted

    def inarchivecheck(self, remote, options):
        """Use the archive object to check if **remote** exists."""
        # Try to delete the md5 file but ignore errors...
        if self._hash_check_or_delete(self.inarchivecheck, remote, options):
            return self.archive.check(
                self._inarchiveformatpath(remote),
                username=remote.get("username", None),
                fmt=options.get("fmt", "foo"),
                compressionpipeline=self._actual_cpipeline,
            )
        else:
            return False

    def inarchivelocate(self, remote, options):
        """Use the archive object to obtain **remote** physical location."""
        return self.archive.fullpath(
            self._inarchiveformatpath(remote),
            username=remote.get("username", None),
            fmt=options.get("fmt", "foo"),
            compressionpipeline=self._actual_cpipeline,
        )

    def inarchivelist(self, remote, options):
        """Use the archive object to list available files."""
        return self.archive.list(
            self._inarchiveformatpath(remote),
            username=remote.get("username", None),
        )

    def inarchiveprestageinfo(self, remote, options):
        """Returns the prestaging informations"""
        return self.archive.prestageinfo(
            self._inarchiveformatpath(remote),
            username=remote.get("username", None),
            fmt=options.get("fmt", "foo"),
            compressionpipeline=self._actual_cpipeline,
        )

    def inarchiveget(self, remote, local, options):
        """Use the archive object to retrieve **remote** in **local**."""
        logger.info(
            "inarchiveget on %s://%s/%s (to: %s)",
            self.scheme,
            self.netloc,
            self._inarchiveformatpath(remote),
            local,
        )
        rc = self.archive.retrieve(
            self._inarchiveformatpath(remote),
            local,
            intent=options.get("intent", ARCHIVE_GET_INTENT_DEFAULT),
            fmt=options.get("fmt", "foo"),
            info=options.get("rhandler", None),
            username=remote["username"],
            compressionpipeline=self._actual_cpipeline,
        )
        return rc and self._hash_get_check(
            self.inarchiveget, remote, local, options
        )

    def inarchiveearlyget(self, remote, local, options):
        """Use the archive object to initiate an early get request on **remote**."""
        logger.debug(
            "inarchiveearlyget on %s://%s/%s (to: %s)",
            self.scheme,
            self.netloc,
            self._inarchiveformatpath(remote),
            local,
        )
        rc = self.archive.earlyretrieve(
            self._inarchiveformatpath(remote),
            local,
            intent=options.get("intent", ARCHIVE_GET_INTENT_DEFAULT),
            fmt=options.get("fmt", "foo"),
            info=options.get("rhandler", None),
            username=remote["username"],
            compressionpipeline=self._actual_cpipeline,
        )
        return rc

    def inarchivefinaliseget(self, result_id, remote, local, options):
        """Use the archive object to finalise the **result_id** early get request."""
        logger.info(
            "inarchivefinaliseget on %s://%s/%s (to: %s)",
            self.scheme,
            self.netloc,
            self._inarchiveformatpath(remote),
            local,
        )
        rc = self.archive.finaliseretrieve(
            result_id,
            self._inarchiveformatpath(remote),
            local,
            intent=options.get("intent", ARCHIVE_GET_INTENT_DEFAULT),
            fmt=options.get("fmt", "foo"),
            info=options.get("rhandler", None),
            username=remote["username"],
            compressionpipeline=self._actual_cpipeline,
        )
        return rc and self._hash_get_check(
            self.inarchiveget, remote, local, options
        )

    def inarchiveput(self, local, remote, options):
        """Use the archive object to put **local** to **remote**"""
        logger.info(
            "inarchiveput to %s://%s/%s (from: %s)",
            self.scheme,
            self.netloc,
            self._inarchiveformatpath(remote),
            local,
        )
        rc = self.archive.insert(
            self._inarchiveformatpath(remote),
            local,
            intent=ARCHIVE_PUT_INTENT,
            fmt=options.get("fmt", "foo"),
            info=options.get("rhandler"),
            username=remote["username"],
            compressionpipeline=self._actual_cpipeline,
            enforcesync=options.get("enforcesync", False),
            usejeeves=options.get("delayed", None),
        )
        return rc and self._hash_put(self.inarchiveput, local, remote, options)

    def inarchivedelete(self, remote, options):
        logger.info(
            "inarchivedelete on %s://%s/%s",
            self.scheme,
            self.netloc,
            self._inarchiveformatpath(remote),
        )
        # Try to delete the md5 file but ignore errors...
        self._hash_check_or_delete(self.inarchivedelete, remote, options)
        return self.archive.delete(
            self._inarchiveformatpath(remote),
            fmt=options.get("fmt", "foo"),
            info=options.get("rhandler", None),
            username=remote["username"],
            compressionpipeline=self._actual_cpipeline,
        )


class CacheStore(Store):
    """Generic Cache Store."""

    # Each Cache object created by a CacheStore will be stored here:
    # This way it won't be garbage collect and could be re-used later on
    _caches_object_stack = set()

    _abstract = True
    _footprint = dict(
        info="Generic cache store",
        attr=dict(
            scheme=dict(
                values=["incache"],
            ),
            netloc=dict(
                values=["open.cache.fr"],
            ),
            storehash=dict(
                values=hashalgo_avail_list,
            ),
            strategy=dict(
                optional=True,
                default="std",
            ),
            headdir=dict(
                optional=True,
                default="conf",
            ),
            rtouch=dict(
                type=bool,
                optional=True,
                default=False,
            ),
            rtouchskip=dict(
                type=int,
                optional=True,
                default=0,
            ),
        ),
    )

    def __init__(self, *args, **kw):
        del self.cache
        logger.debug("Generic cache store init %s", self.__class__)
        super().__init__(*args, **kw)

    @property
    def realkind(self):
        return "cachestore"

    def use_cache(self):
        """Boolean value to insure that this store is using a cache."""
        return True

    def has_fast_check(self):
        """Because that's why caching is used !"""
        return True

    @property
    def underlying_cache_kind(self):
        """The kind of cache that will be used."""
        return self.strategy

    def _get_cache(self):
        if not self._cache:
            self._cache = footprints.proxy.caches.default(
                entry=self.location,
                rtouch=self.rtouch,
                rtouchskip=self.rtouchskip,
                readonly=self.readonly,
            )
            self._caches_object_stack.add(self._cache)
        return self._cache

    def _set_cache(self, newcache):
        """Set a new cache reference."""
        if isinstance(newcache, storage.Cache):
            self._cache = newcache

    def _del_cache(self):
        """Invalidate internal cache reference."""
        self._cache = None

    cache = property(_get_cache, _set_cache, _del_cache)

    def _str_more(self):
        return "entry={:s}".format(self.cache.entry)

    def incachecheck(self, remote, options):
        """Returns a stat-like object if the ``remote`` exists in the current cache."""
        if self._hash_check_or_delete(self.incachecheck, remote, options):
            st = self.cache.check(remote["path"])
            if options.get("isfile", False) and st:
                st = self.system.path.isfile(
                    self.incachelocate(remote, options)
                )
            return st
        else:
            return False

    def incachelocate(self, remote, options):
        """Agregates cache to remote subpath."""
        return self.cache.fullpath(remote["path"])

    def incachelist(self, remote, options):
        """List the content of a remote path."""
        return self.cache.list(remote["path"])

    def incacheprestageinfo(self, remote, options):
        """Returns pre-staging informations."""
        return self.cache.prestageinfo(remote["path"])

    def incacheget(self, remote, local, options):
        """Simple copy from current cache cache to ``local``."""
        logger.info(
            "incacheget on %s://%s/%s (to: %s)",
            self.scheme,
            self.netloc,
            remote["path"],
            local,
        )
        rc = self.cache.retrieve(
            remote["path"],
            local,
            intent=options.get("intent", CACHE_GET_INTENT_DEFAULT),
            fmt=options.get("fmt"),
            info=options.get("rhandler", None),
            tarextract=options.get("auto_tarextract", False),
            dirextract=options.get("auto_dirextract", False),
            uniquelevel_ignore=options.get("uniquelevel_ignore", True),
            silent=options.get("silent", False),
        )
        if rc or not options.get("silent", False):
            logger.info(
                "incacheget retrieve rc=%s location=%s",
                str(rc),
                str(self.incachelocate(remote, options)),
            )
        return rc and self._hash_get_check(
            self.incacheget, remote, local, options
        )

    def incacheput(self, local, remote, options):
        """Simple copy from ``local`` to the current cache in readonly mode."""
        logger.info(
            "incacheput to %s://%s/%s (from: %s)",
            self.scheme,
            self.netloc,
            remote["path"],
            local,
        )
        rc = self.cache.insert(
            remote["path"],
            local,
            intent=CACHE_PUT_INTENT,
            fmt=options.get("fmt"),
            info=options.get("rhandler", None),
        )
        logger.info(
            "incacheput insert rc=%s location=%s",
            str(rc),
            str(self.incachelocate(remote, options)),
        )
        return rc and self._hash_put(self.incacheput, local, remote, options)

    def incachedelete(self, remote, options):
        """Simple removing of the remote resource in cache."""
        logger.info(
            "incachedelete on %s://%s/%s",
            self.scheme,
            self.netloc,
            remote["path"],
        )
        self._hash_check_or_delete(self.incachedelete, remote, options)
        return self.cache.delete(
            remote["path"],
            fmt=options.get("fmt"),
            info=options.get("rhandler", None),
        )


class PromiseStore(footprints.FootprintBase):
    """Combined a Promise Store for expected resources and any other matching Store."""

    _abstract = True
    _collector = ("store",)
    _footprint = dict(
        info="Promise store",
        attr=dict(
            scheme=dict(alias=("protocol",)),
            netloc=dict(type=Namespace, alias=("domain", "namespace")),
            storetrack=dict(
                type=bool,
                default=True,
                optional=True,
            ),
            prstorename=dict(
                type=Namespace,
                optional=True,
                default="promise.cache.fr",
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug("Abstract promise store init %s", self.__class__)
        sh = kw.pop("system", sessions.system())
        super().__init__(*args, **kw)
        self._sh = sh

        # Assume that the actual scheme is the current scheme without "x" prefix
        self.proxyscheme = self.scheme.lstrip("x")

        # Find a store for the promised resources
        self.promise = footprints.proxy.store(
            scheme=self.proxyscheme,
            netloc=self.prstorename,
            storetrack=self.storetrack,
        )
        if self.promise is None:
            logger.critical(
                "Could not find store scheme <%s> netloc <%s>",
                self.proxyscheme,
                self.prstorename,
            )
            raise ValueError("Could not get a Promise Store")

        # Find the other "real" store (could be a multi-store)
        self.other = footprints.proxy.store(
            scheme=self.proxyscheme,
            netloc=self.netloc,
            storetrack=self.storetrack,
        )
        if self.other is None:
            logger.critical(
                "Could not find store scheme <%s> netloc <%s>",
                self.proxyscheme,
                self.netloc,
            )
            raise ValueError("Could not get an Other Store")

        self.openedstores = (self.promise, self.other)
        self.delayed = False

    @property
    def realkind(self):
        return "promisestore"

    @property
    def system(self):
        """Shortcut to current system interface."""
        return self._sh

    def has_fast_check(self):
        """It depends..."""
        return self.other.has_fast_check()

    def mkpromise_info(self, remote, options):
        """Build a dictionary with relevant informations for the promise."""
        return dict(
            promise=True,
            stamp=date.stamp(),
            itself=self.promise.locate(remote, options),
            locate=self.other.locate(remote, options),
            datafmt=options.get("fmt", None),
            rhandler=options.get("rhandler", None),
        )

    def mkpromise_file(self, info, local):
        """Build a virtual container with specified informations."""
        pfile = local + ".pr"
        self.system.json_dump(info, pfile, sort_keys=True, indent=4)
        return pfile

    @staticmethod
    def _options_fixup(options):
        return dict() if options is None else options

    def check(self, remote, options=None):
        """Go through internal opened stores and check for the resource."""
        options = self._options_fixup(options)
        logger.debug("Promise check from %s", remote)
        return self.other.check(remote.copy(), options) or self.promise.check(
            remote.copy(), options
        )

    def locate(self, remote, options=None):
        """Go through internal opened stores and locate the expected resource for each of them."""
        options = self._options_fixup(options)
        logger.debug("Promise locate %s", remote)
        inpromise = True
        if options:
            inpromise = options.get("inpromise", True)

        locate_other = self.other.locate(remote.copy(), options)
        if inpromise:
            locate_promised = self.promise.locate(remote.copy(), options)
            return locate_promised + ";" + locate_other
        return locate_other

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        options = self._options_fixup(options)
        logger.debug("Promise get %s", remote)
        self.delayed = False
        logger.info("Try promise from store %s", self.promise)
        try:
            rc = self.promise.get(remote.copy(), local, options)
        except OSError as e:
            # If something goes wrong, assume that the promise file had been
            # deleted during the execution of self.promise.check (which can cause
            # IOError or OSError to be raised).
            logger.info(
                "An error occurred while fetching the promise file: %s", str(e)
            )
            logger.info("Assuming this is a negative result...")
            rc = False
        if rc:
            self.delayed = True
        else:
            logger.info("Try promise from store %s", self.other)
            rc = self.other.get(remote.copy(), local, options)
        if not rc and options.get("pretend", False):
            logger.warning("Pretending to get a promise for <%s>", local)
            pr_info = self.mkpromise_info(remote, options)
            pr_file = self.mkpromise_file(pr_info, local)
            self.system.move(pr_file, local)
            rc = self.delayed = True
        return rc

    def earlyget(self, remote, local, options=None):
        """Possible early-get on the target store."""
        options = self._options_fixup(options)
        logger.debug("Promise early-get %s", remote)
        result_id = None
        try:
            rc = self.promise.has_fast_check and self.promise.check(
                remote.copy(), options
            )
        except OSError as e:
            logger.debug(
                "An error occurred while checking for the promise file: %s",
                str(e),
            )
            logger.debug("Assuming this is a negative result...")
            rc = False
        if not rc:
            result_id = self.other.earlyget(remote.copy(), local, options)
        return result_id

    def finaliseget(self, result_id, remote, local, options=None):
        options = self._options_fixup(options)
        logger.debug("Promise finalise-get %s", remote)
        self.delayed = False
        logger.info("Try promise from store %s", self.promise)
        try:
            rc = self.promise.get(remote.copy(), local, options)
        except OSError as e:
            logger.debug(
                "An error occurred while fetching the promise file: %s", str(e)
            )
            logger.debug("Assuming this is a negative result...")
            rc = False
        if rc:
            self.delayed = True
        else:
            logger.info("Try promise from store %s", self.other)
            rc = self.other.finaliseget(
                result_id, remote.copy(), local, options
            )
        return rc

    @staticmethod
    def _clean_pr_json(prjson):
        del prjson["stamp"]
        if "options" in prjson["rhandler"]:
            prjson["rhandler"]["options"].pop("storetrack", False)
        return prjson

    def put(self, local, remote, options=None):
        """Put a promise or the actual resource if available."""
        options = self._options_fixup(options)
        logger.debug("Multistore put from %s to %s", local, remote)
        if options.get("force", False) or not self.system.path.exists(local):
            options = options.copy()
            if not self.other.use_cache():
                logger.critical(
                    "Could not promise resource without other cache <%s>",
                    self.other,
                )
                raise ValueError(
                    "Could not promise: other store does not use cache"
                )
            pr_info = self.mkpromise_info(remote, options)
            pr_file = self.mkpromise_file(pr_info, local)
            # Check if a previous promise with the same description exists
            preexisting = self.promise.check(remote.copy(), options)
            if preexisting:
                pr_old_file = self.promise.locate(remote.copy())
                prcheck = self._clean_pr_json(
                    self.system.json_load(pr_old_file)
                )
                prnew = self._clean_pr_json(self.system.json_load(pr_file))
                preexisting = prcheck == prnew
                if preexisting:
                    logger.info(
                        "The promise file <%s> preexisted and is compatible",
                        pr_old_file,
                    )
                    rc = True
                else:
                    logger.warning(
                        "The promise file <%s> already exists but doesn't match",
                        pr_old_file,
                    )

            # Put the new promise file in the PromiseCache
            options["obs_overridelocal"] = local  # Pretty nasty :-(
            if not preexisting:
                logger.warning(
                    "Log a promise instead of missing resource <%s>", local
                )
                rc = self.promise.put(pr_file, remote.copy(), options)
                if rc:
                    del options["obs_overridelocal"]
                    self.other.delete(remote.copy(), options)
            else:
                options["dryrun"] = True  # Just update the tracker
                rc = self.promise.put(pr_file, remote.copy(), options)
            self.system.remove(pr_file)

        else:
            logger.info("Actual promise does exists <%s>", local)
            rc = self.other.put(local, remote.copy(), options)
            if rc:
                self.promise.delete(remote.copy(), options)
        return rc

    def delete(self, remote, options=None):
        """Go through internal opened stores and delete the resource."""
        options = self._options_fixup(options)
        logger.debug("Promise delete from %s", remote)
        return self.promise.delete(
            remote.copy(), options
        ) and self.other.delete(remote.copy(), options)


# Activate the footprint's fasttrack on the stores collector
fcollect = footprints.collectors.get(tag="store")
fcollect.fasttrack = ("netloc", "scheme")
del fcollect
