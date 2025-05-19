# pylint: disable=unused-argument

"""
This module handles store objects in charge of physically accessing resources.
Store objects use the :mod:`footprints` mechanism.
"""

import copy
import ftplib
import io
import os
import re

from bronx.fancies import loggers
import footprints

from vortex import sessions
from vortex import config
from vortex.data.abstractstores import (
    Store,
    ArchiveStore,
    CacheStore,
)
from vortex.data.abstractstores import MultiStore, PromiseStore
from vortex.data.abstractstores import ARCHIVE_GET_INTENT_DEFAULT
from vortex.layout import dataflow
from vortex.syntax.stdattrs import hashalgo_avail_list
from vortex.syntax.stdattrs import DelayedEnvValue
from vortex.tools.systems import ExecutionError

#: Export base class
__all__ = []

logger = loggers.getLogger(__name__)


def get_cache_location():
    try:
        cacheloc = config.from_config(
            section="data-tree",
            key="rootdir",
        )
    except config.ConfigurationError:
        cacheloc = os.path.join(os.environ["HOME"], ".vortex.d")
    return cacheloc


class MagicPlace(Store):
    """Somewhere, over the rainbow!"""

    _footprint = dict(
        info="Evanescent physical store",
        attr=dict(
            scheme=dict(
                values=["magic"],
            ),
        ),
        priority=dict(
            level=footprints.priorities.top.DEFAULT  # @UndefinedVariable
        ),
    )

    @property
    def realkind(self):
        return "magicstore"

    def has_fast_check(self):
        """A void check is very fast !"""
        return True

    def magiccheck(self, remote, options):
        """Void - Always False."""
        return False

    def magiclocate(self, remote, options):
        """Void - Empty string returned."""
        return ""

    def magicget(self, remote, local, options):
        """Void - Always True."""
        return True

    def magicput(self, local, remote, options):
        """Void - Always True."""
        return True

    def magicdelete(self, remote, options):
        """Void - Always False."""
        return False


class FunctionStoreCallbackError(Exception):
    pass


class FunctionStore(Store):
    """Calls a function that returns a File like object (get only).

    This store is only able to perform the get action: it imports and calls
    the function specified in the URI path. This function should return a
    file like object that will be written in the local container.

    The function is given an option dictionary that contains all of the
    options provided to the store's get function, plus any additional
    information specified in the 'query' part of the URI.

    :Example:

    Lets consider the following URI:

      ``function:///sandbox.util.storefunctions.echofunction?msg=toto&msg=titi``

    It will be seen as follows:

    * scheme: ``'function'``
    * netloc: ``''``
    * path: ``'/sandbox.utils.storefunctions.echofunction'``
    * query: ``dict(msg=['toto', 'titi'])``

    As a result, the :func:`sandbox.utils.storefunctions.echofunction` will be
    called with an option dictionary that contains ['toto', 'titi'] for the
    'msg' key (plus any other options passed to the store's get method).
    """

    _footprint = dict(
        info="Dummy store that calls a function",
        attr=dict(
            scheme=dict(
                values=["function"],
            ),
            netloc=dict(
                values=[""],
            ),
        ),
        priority=dict(
            level=footprints.priorities.top.DEFAULT  # @UndefinedVariable
        ),
    )

    @property
    def realkind(self):
        return "functionstore"

    def has_fast_check(self):
        """A void check is very fast !"""
        return True

    def functioncheck(self, remote, options):
        """Void - Always False."""
        return False

    def functionlocate(self, remote, options):
        """The name of the function that will be called."""
        cleanname = remote["path"][1:]
        if cleanname.endswith("/"):
            cleanname = cleanname[:-1]
        return cleanname

    def functionget(self, remote, local, options):
        """Calls the appropriate function and writes the result."""
        # Find the appropriate function
        cbfunc = self.system.import_function(
            self.functionlocate(remote, options)
        )
        # ... and call it
        opts = dict()
        opts.update(options)
        opts.update(remote["query"])
        try:
            fres = cbfunc(opts)
        except FunctionStoreCallbackError as e:
            logger.error("An exception was raised in the Callback function")
            logger.error("Here is the exception: %s", str(e))
            fres = None
        if fres is not None:
            if "intent" in options and options["intent"] == dataflow.intent.IN:
                logger.info("Ignore intent <in> for function input.")
            # Handle StringIO objects, by changing them to ByteIOs...
            if isinstance(fres, io.StringIO):
                s_fres = fres
                s_fres.seek(0)
                fres = io.BytesIO()
                for l in s_fres:
                    fres.write(l.encode(encoding="utf-8"))
                fres.seek(0)
            # NB: fres should be a file like object (BytesIO will do the trick)
            return self.system.cp(fres, local)
        else:
            return False

    def functionput(self, local, remote, options):
        """This should not happen - Always False."""
        logger.error("The function store is not able to perform PUTs.")
        return False

    def functiondelete(self, remote, options):
        """This should not happen - Always False."""
        logger.error("The function store is not able to perform Deletes.")
        return False


class Finder(Store):
    """The most usual store: your current filesystem!"""

    _footprint = dict(
        info="Miscellaneous file access",
        attr=dict(
            scheme=dict(
                values=["file", "ftp", "symlink", "rcp", "scp"],
            ),
            netloc=dict(
                outcast=["oper.inline.fr"],
            ),
            storehash=dict(
                values=hashalgo_avail_list,
            ),
        ),
        priority=dict(
            level=footprints.priorities.top.DEFAULT  # @UndefinedVariable
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug("Finder store init %s", self.__class__)
        super().__init__(*args, **kw)

    @property
    def realkind(self):
        return "finder"

    def hostname(self):
        """Returns the current :attr:`netloc`."""
        return self.netloc

    def fullpath(self, remote):
        """Return actual path unless explicitly defined as relative path."""
        if remote["query"].get("relative", False):
            return remote["path"].lstrip("/")
        else:
            return remote["path"]

    def _localtarfix(self, local):
        if (
            isinstance(local, str)
            and self.system.path.isfile(local)
            and self.system.is_tarfile(local)
        ):
            destdir = self.system.path.dirname(
                self.system.path.realpath(local)
            )
            try:
                self.system.smartuntar(local, destdir)
            except ExecutionError:
                if not self.system.is_tarname(local):
                    logger.warning(
                        "An automatic untar was attempted but it failed. "
                        + "Maybe the system's is_tarfile got it wrong ?"
                    )
                else:
                    raise

    def filecheck(self, remote, options):
        """Returns a stat-like object if the ``remote`` exists on the ``system`` provided."""
        try:
            st = self.system.stat(self.fullpath(remote))
        except OSError:
            st = None
        return st

    def filelocate(self, remote, options):
        """Returns the real path."""
        return self.fullpath(remote)

    def fileget(self, remote, local, options):
        """Delegates to ``system`` the copy of ``remote`` to ``local``."""
        rpath = self.fullpath(remote)
        logger.info("fileget on %s (to: %s)", rpath, local)
        if "intent" in options and options["intent"] == dataflow.intent.IN:
            logger.info("Ignore intent <in> for remote input %s", rpath)
        rc = self.system.cp(
            rpath, local, fmt=options.get("fmt"), intent=dataflow.intent.INOUT
        )
        rc = rc and self._hash_get_check(self.fileget, remote, local, options)
        if rc:
            self._localtarfix(local)
        return rc

    def fileput(self, local, remote, options):
        """Delegates to ``system`` the copy of ``local`` to ``remote``."""
        rpath = self.fullpath(remote)
        logger.info("fileput to %s (from: %s)", rpath, local)
        rc = self.system.cp(local, rpath, fmt=options.get("fmt"))
        return rc and self._hash_put(self.fileput, local, remote, options)

    def filedelete(self, remote, options):
        """Delegates to ``system`` the removing of ``remote``."""
        rc = None
        if self.filecheck(remote, options):
            rpath = self.fullpath(remote)
            logger.info("filedelete on %s", rpath)
            rc = self.system.remove(rpath, fmt=options.get("fmt"))
        else:
            logger.error(
                "Try to remove a non-existing resource <%s>",
                self.fullpath(remote),
            )
        return rc

    symlinkcheck = filecheck
    symlinklocate = filelocate

    def symlinkget(self, remote, local, options):
        rpath = self.fullpath(remote)
        if "intent" in options and options["intent"] == dataflow.intent.INOUT:
            logger.error(
                "It is unsafe to have a symlink with intent=inout: %s", rpath
            )
            return False
        rc = self.system.remove(local)
        self.system.symlink(rpath, local)
        return rc and self.system.path.exists(local)

    def symlinkput(self, local, remote, options):
        logger.error(
            "The Finder store with scheme:symlink is not able to perform Puts."
        )
        return False

    def symlinkdelete(self, remote, options):
        logger.error(
            "The Finder store with scheme:symlink is not able to perform Deletes."
        )
        return False

    def _ftpinfos(self, remote, **kwargs):
        args = kwargs.copy()
        args["hostname"] = self.hostname()
        args["logname"] = remote["username"]
        port = self.hostname().netport
        if port is not None:
            args["port"] = port
        return args

    def ftpcheck(self, remote, options):
        """Delegates to ``system.ftp`` a distant check."""
        rc = None
        ftp = self.system.ftp(**self._ftpinfos(remote))
        if ftp:
            try:
                rc = ftp.size(self.fullpath(remote))
            except (ValueError, TypeError):
                pass
            except ftplib.all_errors:
                pass
            finally:
                ftp.close()
        return rc

    def ftplocate(self, remote, options):
        """Delegates to ``system`` qualified name creation."""
        ftp = self.system.ftp(**self._ftpinfos(remote, delayed=True))
        if ftp:
            rloc = ftp.netpath(self.fullpath(remote))
            ftp.close()
            return rloc
        else:
            return None

    def ftpget(self, remote, local, options):
        """Delegates to ``system`` the file transfer of ``remote`` to ``local``."""
        rpath = self.fullpath(remote)
        logger.info(
            "ftpget on ftp://%s/%s (to: %s)", self.hostname(), rpath, local
        )
        rc = self.system.smartftget(
            rpath,
            local,
            fmt=options.get("fmt"),
            # ftp control
            **self._ftpinfos(remote),
        )
        rc = rc and self._hash_get_check(self.ftpget, remote, local, options)
        if rc:
            self._localtarfix(local)
        return rc

    def ftpput(self, local, remote, options):
        """Delegates to ``system`` the file transfer of ``local`` to ``remote``."""
        rpath = self.fullpath(remote)
        put_opts = dict()
        put_opts["fmt"] = options.get("fmt")
        put_opts["sync"] = options.get("enforcesync", False)
        logger.info(
            "ftpput to ftp://%s/%s (from: %s)", self.hostname(), rpath, local
        )
        rc = self.system.smartftput(
            local,
            rpath,
            # ftp control
            **self._ftpinfos(remote, **put_opts),
        )
        return rc and self._hash_put(self.ftpput, local, remote, options)

    def ftpdelete(self, remote, options):
        """Delegates to ``system`` a distant remove."""
        rc = None
        actualpath = self.fullpath(remote)
        if self.ftpcheck(remote, options):
            logger.info(
                "ftpdelete on ftp://%s/%s", self.hostname(), actualpath
            )
            ftp = self.system.ftp(**self._ftpinfos(remote))
            if ftp:
                try:
                    rc = ftp.delete(actualpath)
                finally:
                    ftp.close()
        else:
            logger.error(
                "Try to remove a non-existing resource <%s>", actualpath
            )
        return rc


class _VortexStackedStorageMixin:
    """Mixin class that adds utility functions to work with stacked data."""

    _STACKED_RE = re.compile("stacked-")

    @property
    def stackedstore(self):
        """Tell if the present store is looking into a stack of resources."""
        return self._STACKED_RE.search(self.netloc)

    def _stacked_remainder(self, remote, stackpath):
        path_remainder = remote["path"].strip("/").split("/")
        for a_spath in stackpath.split("/"):
            if path_remainder and path_remainder[0] == a_spath:
                del path_remainder[0]
            else:
                break
        return "/".join(path_remainder)

    def _stacked_xremote(self, remote):
        """The path to **remote** with its stack."""
        if self.stackedstore:
            remote = remote.copy()
            remote["query"] = remote["query"].copy()
            stackpath = remote["query"].pop("stackpath", (None,))[0]
            stackfmt = remote["query"].pop("stackfmt", (None,))[0]
            if stackpath is None or stackfmt is None:
                raise ValueError(
                    '"stackpath" and "stackfmt" are not available in the query.'
                )
            else:
                remote["path"] = (
                    stackpath
                    + "/"
                    + self._stacked_remainder(remote, stackpath)
                )
        return remote

    def _stacked_xegglocate(self, remote):
        """Return various informations about the stack associated with **remote**.

        It returns a 3 elements tuple:

        * The remote-like dictionary to the stack resource
        * The format of the stack resource
        * The path to **remote** within the stacked resource

        """
        remote = remote.copy()
        remote["query"] = remote["query"].copy()
        stackpath = remote["query"].pop("stackpath", (None,))[0].strip("/")
        stackfmt = remote["query"].pop("stackfmt", (None,))[0]
        if stackpath is None or stackfmt is None:
            raise ValueError(
                '"stackpath" and "stackfmt" are not available in the query.'
            )
        else:
            resource_remainder = self._stacked_remainder(remote, stackpath)
            remote["path"] = "/" + stackpath
        return remote, stackfmt, resource_remainder


_vortex_readonly_store = footprints.Footprint(
    info="Abstract store' readonly=True attribute",
    attr=dict(
        readonly=dict(
            values=[
                True,
            ],
            optional=True,
            default=True,
        )
    ),
)


class _VortexBaseArchiveStore(ArchiveStore, _VortexStackedStorageMixin):
    """Some kind of archive for VORTEX experiments."""

    _abstract = True
    _footprint = dict(
        info="VORTEX archive access",
        attr=dict(
            scheme=dict(
                values=["vortex"],
            ),
            netloc=dict(),
            storehead=dict(
                optional=True,
                default="vortex",
                outcast=["xp"],
            ),
        ),
    )

    _STACKS_AUTOREFILL_CRIT = "stacked-archive-smart"

    def __init__(self, *args, **kw):
        logger.debug("Vortex archive store init %s", self.__class__)
        super().__init__(*args, **kw)

    def remap_read(self, remote, options):
        """Remap actual remote path to distant store path for intrusive actions."""
        raise NotImplementedError

    def remap_write(self, remote, options):
        """Remap actual remote path to distant store path for intrusive actions."""
        raise NotImplementedError

    def remap_list(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        if len(remote["path"].split("/")) >= 4:
            return self.remap_read(remote, options)
        else:
            logger.critical(
                "The << %s >> path is not listable.", remote["path"]
            )
            return None

    @property
    def stacks_autorefill(self):
        """Where to refill a stack retrieved from the archive."""
        if self._STACKS_AUTOREFILL_CRIT in self.netloc:
            return self.netloc.replace(self._STACKS_AUTOREFILL_CRIT, "cache")
        else:
            return None

    def _vortex_stacked_egg_retrieve(self, remote, result_id=None):
        """Retrieve the stack associated with **remote**."""
        remote, remotefmt, remainder = self._stacked_xegglocate(remote)
        rundir = sessions.current().context.rundir
        if not rundir:
            rundir = self.system.pwd()
        rundir = self.system.path.join(rundir, "vortex_stacks_xeggs")
        target = self.system.path.join(
            rundir, *remote["path"].strip("/").split("/")
        )
        targetopts = dict(fmt=remotefmt, intent=dataflow.intent.IN)
        if self.system.path.exists(target):
            logger.info(
                "Stack previously retrieved (in %s). Using it.", target
            )
            rc = True
        else:
            if result_id:
                rc = self._vortexfinaliseget(
                    result_id, remote, target, targetopts
                )
            else:
                rc = self._vortexget(remote, target, targetopts)
        if rc and self.stacks_autorefill:
            rstore = footprints.proxy.store(
                scheme=self.scheme, netloc=self.stacks_autorefill
            )
            logger.info("Refilling the stack egg to [%s]", rstore)
            try:
                rstore.put(target, remote.copy(), targetopts)
            except (ExecutionError, OSError) as e:
                logger.error(
                    "An ExecutionError happened during the refill: %s", str(e)
                )
                logger.error("This error is ignored... but that's ugly !")
        return rc, target, remainder

    def vortexcheck(self, remote, options):
        """Vortex' archive check sequence."""
        if self.stackedstore:
            s_remote, s_remotefmt, _ = self._stacked_xegglocate(remote)
            options = options.copy()
            options["fmt"] = s_remotefmt
            rc = self._vortexcheck(s_remote, options)
            if rc:
                rc, target, remainder = self._vortex_stacked_egg_retrieve(
                    remote
                )
                rc = rc and self.system.path.exists(
                    self.system.path.join(target, remainder)
                )
            return rc
        else:
            return self._vortexcheck(remote, options)

    def _vortexcheck(self, remote, options):
        """Remap and ftpcheck sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchivecheck(remote, options)

    def vortexlocate(self, remote, options):
        """Vortex' archive locate sequence."""
        if self.stackedstore:
            remote, s_remotefmt, _ = self._stacked_xegglocate(remote)
            options = options.copy()
            options["fmt"] = s_remotefmt
        return self._vortexlocate(remote, options)

    def _vortexlocate(self, remote, options):
        """Remap and ftplocate sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchivelocate(remote, options)

    def vortexlist(self, remote, options):
        """Vortex' archive list sequence."""
        if self.stackedstore:
            return None
        else:
            return self._vortexlist(remote, options)

    def _vortexlist(self, remote, options):
        """Remap and ftplist sequence."""
        remote = self.remap_list(remote, options)
        if remote:
            return self.inarchivelist(remote, options)
        else:
            return None

    def vortexprestageinfo(self, remote, options):
        """Vortex' archive prestageinfo sequence."""
        if self.stackedstore:
            remote, s_remotefmt, _ = self._stacked_xegglocate(remote)
            options = options.copy()
            options["fmt"] = s_remotefmt
        return self._vortexprestageinfo(remote, options)

    def _vortexprestageinfo(self, remote, options):
        """Remap and ftpprestageinfo sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchiveprestageinfo(remote, options)

    def vortexget(self, remote, local, options):
        """Vortex' archive get sequence."""
        if self.stackedstore:
            rc, target, remainder = self._vortex_stacked_egg_retrieve(remote)
            rc = rc and self.system.cp(
                self.system.path.join(target, remainder),
                local,
                fmt=options.get("fmt"),
                intent=options.get("intent", ARCHIVE_GET_INTENT_DEFAULT),
            )
            return rc
        else:
            return self._vortexget(remote, local, options)

    def _vortexget(self, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchiveget(remote, local, options)

    def vortexearlyget(self, remote, local, options):
        """Vortex' archive earlyget sequence."""
        if self.stackedstore:
            s_remote, s_remotefmt, _ = self._stacked_xegglocate(remote)
            targetopts = dict(fmt=s_remotefmt, intent=dataflow.intent.IN)
            return self._vortexearlyget(s_remote, "somelocalfile", targetopts)
        else:
            return self._vortexearlyget(remote, local, options)

    def _vortexearlyget(self, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchiveearlyget(remote, local, options)

    def vortexfinaliseget(self, result_id, remote, local, options):
        """Vortex' archive finaliseget sequence."""
        if self.stackedstore:
            rc, target, remainder = self._vortex_stacked_egg_retrieve(
                remote, result_id=result_id
            )
            rc = rc and self.system.cp(
                self.system.path.join(target, remainder),
                local,
                fmt=options.get("fmt"),
                intent=options.get("intent", ARCHIVE_GET_INTENT_DEFAULT),
            )
            return rc
        else:
            return self._vortexfinaliseget(result_id, remote, local, options)

    def _vortexfinaliseget(self, result_id, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self.remap_read(remote, options)
        return self.inarchivefinaliseget(result_id, remote, local, options)

    def vortexput(self, local, remote, options):
        """Remap root dir and ftpput sequence."""
        if self.stackedstore:
            raise RuntimeError("stacked archive stores are never writable.")
        if not self.storetrue:
            logger.info("put deactivated for %s", str(local))
            return True
        remote = self.remap_write(remote, options)
        return self.inarchiveput(local, remote, options)

    def vortexdelete(self, remote, options):
        """Remap root dir and ftpdelete sequence."""
        if self.stackedstore:
            raise RuntimeError("stacked archive stores are never writable.")
        remote = self.remap_write(remote, options)
        return self.inarchivedelete(remote, options)


class VortexStdBaseArchiveStore(_VortexBaseArchiveStore):
    """Archive for casual VORTEX experiments: Support for legacy/Olive XPIDs.

    This 'archive-legacy' store looks into the resource 'main' location not
    into a potential stack.
    """

    _footprint = dict(
        info="VORTEX archive access for casual experiments",
        attr=dict(
            netloc=dict(
                values=["vortex.archive-legacy.fr"],
            ),
        ),
    )

    def remap_read(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        try:
            remote["root"] = config.from_config(
                section="storage",
                key="rootdir",
            )
        except config.ConfigurationError as e:
            msg = (
                "Trying to write to archive but location is not configured.\n"
                'Make sure key "rootdir" is defined in storage section of '
                "the configuration.\n"
                "See https://vortex-nwp.readthedocs.io/en/latest/user-guide/configuration.html#storage"
            )
            logger.error(msg)
            raise e
        return remote

    remap_write = remap_read


class VortexStdStackedArchiveStore(VortexStdBaseArchiveStore):
    """Archive for casual VORTEX experiments: Support for legacy/Olive XPIDs.

    This 'stacked-archive-legacy' or 'stacked-archive-smart' store looks into
    the stack associated to the resource. The '-smart' variant, has the ability
    to refill the whole stack into local cache (to be faster in the future).
    """

    _footprint = [
        _vortex_readonly_store,
        dict(
            attr=dict(
                netloc=dict(
                    values=[
                        "vortex.stacked-archive-legacy.fr",
                        "vortex.stacked-archive-smart.fr",
                    ],
                ),
            )
        ),
    ]


class VortexOpBaseArchiveStore(_VortexBaseArchiveStore):
    """Archive for op VORTEX experiments.

    This 'archive-legacy' store looks into the resource 'main' location not
    into a potential stack.
    """

    _footprint = dict(
        info="VORTEX archive access for op experiments",
        attr=dict(
            netloc=dict(
                values=["vsop.archive-legacy.fr"],
            ),
            storetrue=dict(
                default=DelayedEnvValue("op_archive", True),
            ),
        ),
    )

    def remap_read(self, remote, options):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        try:
            remote["root"] = config.from_config(
                section="storage",
                key="op_rootdir",
            )
        except config.ConfigurationError as e:
            msg = (
                "Trying to write to operational data archive but location"
                'is not configured.\nMake sure key "rootdir" is defined in '
                "the storage section of the configuration.\n"
                "See https://vortex-nwp.readthedocs.io/en/latest/user-guide/configuration.html#storage"
            )
            logger.error(msg)
            raise e
        xpath = remote["path"].split("/")
        if len(xpath) >= 5 and re.match(r"^\d{8}T\d{2,4}", xpath[4]):
            # If a date is detected
            vxdate = list(xpath[4])
            vxdate.insert(4, "/")
            vxdate.insert(7, "/")
            vxdate.insert(10, "/")
            xpath[4] = "".join(vxdate)
        remote["path"] = self.system.path.join(*xpath)
        return remote

    remap_write = remap_read


class VortexOpStackedArchiveStore(VortexOpBaseArchiveStore):
    """Archive for op VORTEX experiments.

    This 'stacked-archive-legacy' or 'stacked-archive-smart' store looks into
    the stack associated to the resource. The '-smart' variant, has the ability
    to refill the whole stack into local cache (to be faster in the future).
    """

    _footprint = [
        _vortex_readonly_store,
        dict(
            attr=dict(
                netloc=dict(
                    values=[
                        "vsop.stacked-archive-legacy.fr",
                        "vsop.stacked-archive-smart.fr",
                    ],
                ),
            )
        ),
    ]


class VortexArchiveStore(MultiStore):
    """Archive store for any Vortex experiments.

    Depending on the netloc, legacy/Olive XPIDs ('vortex'), free XPIDs
    ('vortex-free') or operational experiments ('vsop') will be dealt with.

    First, this multi store will look onto the resource 'main' location. In a
    second phase, if sensible, il will also dig into the stack associated with
    the resource.
    """

    _footprint = dict(
        info="VORTEX archive access",
        attr=dict(
            scheme=dict(
                values=["vortex"],
            ),
            netloc=dict(
                values=[
                    "vortex.archive.fr",
                    "vortex-free.archive.fr",
                    "vsop.archive.fr",
                ],
            ),
            refillstore=dict(
                default=False,
            ),
            storehead=dict(
                optional=True,
            ),
            storesync=dict(
                alias=("archsync", "synchro"),
                type=bool,
                optional=True,
            ),
        ),
    )

    def filtered_readable_openedstores(self, remote):
        """Only use the stacked store if sensible."""
        ostores = [
            self.openedstores[0],
        ]
        ostores.extend(
            [
                sto
                for sto in self.openedstores[1:]
                if not sto.stackedstore or "stackpath" in remote["query"]
            ]
        )
        return ostores

    def alternates_netloc(self):
        """Return netlocs describing both base and stacked archives."""
        netloc_m = re.match(
            r"(?P<base>v.*)\.archive\.(?P<country>\w+)", self.netloc
        )
        return [
            "{base:s}.archive-legacy.{country:s}".format(
                **netloc_m.groupdict()
            ),
            "{base:s}.stacked-archive-legacy.{country:s}".format(
                **netloc_m.groupdict()
            ),
        ]

    def alternates_fpextras(self):
        """Deal with some ArchiveStores' specific attributes."""
        return dict(storehead=self.storehead, storesync=self.storesync)


class _VortexCacheBaseStore(CacheStore, _VortexStackedStorageMixin):
    """Some kind of cache for VORTEX experiments: one still needs to choose the cache strategy."""

    _abstract = True
    _footprint = dict(
        info="VORTEX cache access",
        attr=dict(
            scheme=dict(
                values=["vortex"],
            ),
            headdir=dict(
                default="",
                outcast=[
                    "xp",
                ],
            ),
            rtouch=dict(
                default=True,
            ),
            rtouchskip=dict(
                default=3,
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug("Vortex cache store init %s", self.__class__)
        del self.cache
        super().__init__(*args, **kw)

    def vortexcheck(self, remote, options):
        """Proxy to :meth:`incachecheck`."""
        return self.incachecheck(self._stacked_xremote(remote), options)

    def vortexlocate(self, remote, options):
        """Proxy to :meth:`incachelocate`."""
        return self.incachelocate(self._stacked_xremote(remote), options)

    def vortexlist(self, remote, options):
        """Proxy to :meth:`incachelocate`."""
        return self.incachelist(remote, options)

    def vortexprestageinfo(self, remote, options):
        """Proxy to :meth:`incacheprestageinfo`."""
        return self.incacheprestageinfo(self._stacked_xremote(remote), options)

    def vortexget(self, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        return self.incacheget(self._stacked_xremote(remote), local, options)

    def vortexput(self, local, remote, options):
        """Proxy to :meth:`incacheput`."""
        return self.incacheput(local, self._stacked_xremote(remote), options)

    def vortexdelete(self, remote, options):
        """Proxy to :meth:`incachedelete`."""
        return self.incachedelete(self._stacked_xremote(remote), options)


class VortexCacheMtStore(_VortexCacheBaseStore):
    """Some kind of MTOOL cache for VORTEX experiments."""

    _footprint = dict(
        info="VORTEX MTOOL like Cache access",
        attr=dict(
            netloc=dict(
                values=[
                    "{:s}.{:s}cache-mt.fr".format(v, s)
                    for v in ("vortex", "vortex-free", "vsop")
                    for s in ("", "stacked-")
                ]
            ),
        ),
    )

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.location = get_cache_location()


class VortexCacheOp2ResearchStore(_VortexCacheBaseStore):
    """The DSI/OP VORTEX cache where researchers can get the freshest data."""

    _footprint = dict(
        info="VORTEX Mtool cache access",
        attr=dict(
            netloc=dict(
                values=[
                    "vsop.{:s}cache-op2r.fr".format(s)
                    for s in ("", "stacked-")
                ],
            ),
            readonly=dict(
                default=True,
            ),
        ),
    )

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        try:
            cachepath = config.from_config(
                section="data-tree",
                key="op_rootdir",
            )
        except config.ConfigurationError as e:
            logger.error(
                "Cannot use special experiment cache without providing",
                "cache location",
            )
            raise e

        self.location = os.path.join(cachepath, "vortex")


class _AbstractVortexCacheMultiStore(MultiStore):
    """Any Cache based Vortex multi store."""

    _abstract = True
    _footprint = dict(
        info="VORTEX cache access",
        attr=dict(
            scheme=dict(
                values=["vortex"],
            ),
            refillstore=dict(
                default=False,
            ),
        ),
    )

    def filtered_readable_openedstores(self, remote):
        """Deals with stacked stores that are not always active."""
        ostores = [
            self.openedstores[0],
        ]
        # TODO is the call to cache.allow_reads still required without
        # marketplace stores?
        ostores.extend(
            [
                sto
                for sto in self.openedstores[1:]
                if (
                    (not sto.stackedstore or "stackpath" in remote["query"])
                    and sto.cache.allow_reads(remote["path"])
                )
            ]
        )
        return ostores

    def filtered_writeable_openedstores(self, remote):
        """never writes into stack stores."""
        ostores = [
            self.openedstores[0],
        ]
        ostores.extend(
            [
                sto
                for sto in self.openedstores[1:]
                if not sto.stackedstore
                and sto.cache.allow_writes(remote["path"])
            ]
        )
        return ostores


class VortexCacheStore(_AbstractVortexCacheMultiStore):
    """The go to store for data cached by VORTEX R&D experiments."""

    _footprint = dict(
        attr=dict(
            netloc=dict(
                values=[
                    "vortex.cache.fr",
                    "vortex-free.cache.fr",
                ],
            ),
        )
    )

    def alternates_netloc(self):
        """For Non-Op users, Op caches may be accessed in read-only mode."""
        return [
            f"{self.netloc.firstname}.cache-mt.fr",
            f"{self.netloc.firstname}.stacked-cache-mt.fr",
        ]


class VortexVsopCacheStore(_AbstractVortexCacheMultiStore):
    """The go to store for data cached by VORTEX operational experiments.

    It behaves differently depending on the profile of the user running the
    code 'see the **glovekind** attribute).
    """

    _footprint = dict(
        info="VORTEX vsop magic cache access",
        attr=dict(
            netloc=dict(
                values=[
                    "vsop.cache.fr",
                ],
            ),
            glovekind=dict(
                optional=True,
                default="[glove::realkind]",
            ),
        ),
    )

    def alternates_netloc(self):
        """For Non-Op users, Op caches may be accessed in read-only mode."""
        todo = [
            "vsop.cache-mt.fr",
            "vsop.stacked-cache-mt.fr",
        ]

        # Only set up op2r cache if the associated filepath
        # is configured
        if (self.glovekind != "opuser") and config.is_defined(
            section="data-tree",
            key="op_rootdir",
        ):
            todo += [
                "vsop.cache-op2r.fr",
                "vsop.stacked-cache-op2r.fr",
            ]
        return todo


class _AbstractVortexStackMultiStore(MultiStore):
    """Any Cache based Vortex multi store."""

    _abstract = True
    _footprint = dict(
        info="VORTEX stack access",
        attr=dict(
            scheme=dict(
                values=["vortex"],
            ),
            refillstore=dict(
                default=False,
            ),
        ),
    )

    # TODO is this still needed without marketplace stores?
    def filtered_readable_openedstores(self, remote):
        """Deals with marketplace stores that are not always active."""
        ostores = [
            self.openedstores[0],
        ]
        ostores.extend(
            [
                sto
                for sto in self.openedstores[1:]
                if sto.cache.allow_reads(remote["path"])
            ]
        )
        return ostores

    def filtered_writeable_openedstores(self, remote):
        """Deals with marketplace stores that are not always active."""
        ostores = [
            self.openedstores[0],
        ]
        ostores.extend(
            [
                sto
                for sto in self.openedstores[1:]
                if sto.cache.allow_writes(remote["path"])
            ]
        )
        return ostores


class VortexStackStore(_AbstractVortexStackMultiStore):
    """Store intended to read and write data into VORTEX R&D stacks."""

    _footprint = dict(
        info="VORTEX stack access",
        attr=dict(
            netloc=dict(
                values=["vortex.stack.fr", "vortex-free.stack.fr"],
            ),
        ),
    )

    def alternates_netloc(self):
        """Go through the various stacked stores."""
        return [f"{self.netloc.firstname}.stacked-cache-mt.fr"]


class VortexVsopStackStore(_AbstractVortexStackMultiStore):
    """Store intended to read and write data into VORTEX R&D stacks."""

    _footprint = dict(
        info="VORTEX stack access",
        attr=dict(
            netloc=dict(
                values=["vsop.stack.fr"],
            ),
            glovekind=dict(
                optional=True,
                default="[glove::realkind]",
            ),
        ),
    )

    def alternates_netloc(self):
        """For Non-Op users, Op caches may be accessed in read-only mode."""
        todo = [
            "vsop.stacked-cache-mt.fr",
        ]
        if self.glovekind != "opuser":
            todo.append("vsop.stacked-cache-op2r.fr")
        return todo


class VortexStoreLegacy(MultiStore):
    """Combined cache and archive legacy VORTEX stores.

    By '-legacy' we mean that stack resources are ignored.
    """

    _footprint = dict(
        info="VORTEX multi access",
        attr=dict(
            scheme=dict(
                values=["vortex"],
            ),
            netloc=dict(
                values=[
                    "vortex.multi-legacy.fr",
                    "vortex-free.multi-legacy.fr",
                    "vsop.multi-legacy.fr",
                ],
            ),
            refillstore=dict(
                default=True,
            ),
        ),
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return [
            self.netloc.firstname + d
            for d in (".cache.fr", ".archive-legacy.fr")
        ]


class VortexStore(MultiStore):
    """Combined cache and archive VORTEX stores.

    If sensible, stack will be explored and might be refilled into cache.
    """

    _footprint = dict(
        info="VORTEX multi access",
        attr=dict(
            scheme=dict(
                values=["vortex"],
            ),
            netloc=dict(
                values=[
                    "vortex.multi.fr",
                    "vortex-free.multi.fr",
                    "vsop.multi.fr",
                ],
            ),
            refillstore=dict(default=False),
        ),
    )

    def filtered_readable_openedstores(self, remote):
        """Deals with stacked stores that are not always active."""
        ostores = [
            self.openedstores[0],
        ]
        ostores.extend(
            [
                sto
                for sto in self.openedstores[1:]
                if not sto.stackedstore or "stackpath" in remote["query"]
            ]
        )
        return ostores

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return [
            self.netloc.firstname + d
            for d in (
                ".multi-legacy.fr",
                ".stacked-archive-smart.fr",
            )
        ]


class PromiseCacheStore(VortexCacheMtStore):
    """Some kind of vortex cache for EXPECTED resources."""

    _footprint = dict(
        info="EXPECTED cache access",
        attr=dict(
            netloc=dict(
                values=["promise.cache.fr"],
            ),
            headdir=dict(
                default="promise",
                outcast=["xp", "vortex"],
            ),
        ),
    )

    @staticmethod
    def _add_default_options(options):
        options_upd = options.copy()
        options_upd["fmt"] = "ascii"  # Promises are always JSON files
        options_upd["intent"] = "in"  # Promises are always read-only
        return options_upd

    def vortexget(self, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        return super().vortexget(
            remote, local, self._add_default_options(options)
        )

    def vortexput(self, local, remote, options):
        """Proxy to :meth:`incacheput`."""
        return super().vortexput(
            local, remote, self._add_default_options(options)
        )

    def vortexdelete(self, remote, options):
        """Proxy to :meth:`incachedelete`."""
        return super().vortexdelete(remote, self._add_default_options(options))


class VortexPromiseStore(PromiseStore):
    """Combine a Promise Store for expected resources and any VORTEX Store."""

    _footprint = dict(
        info="VORTEX promise store",
        attr=dict(
            scheme=dict(
                values=["xvortex"],
            ),
            netloc=dict(
                outcast=[
                    "vortex-demo.cache.fr",
                    "vortex-demo.multi.fr",
                    "vortex.testcache.fr",
                    "vortex.testmulti.fr",
                ],
            ),
        ),
    )


# Activate the footprint's fasttrack on the stores collector
fcollect = footprints.collectors.get(tag="store")
fcollect.fasttrack = ("netloc", "scheme")
del fcollect
