"""
This package handles :class:`Storage` objects that could be in charge of
hosting data resources both locally ("Cache") or on a remote host "Archive").

* :class:`Storage` is the main abstract class that defines the user-interface for
  every class of this module. :meth:`Storage.fullpath`, :meth:`Storage.check`,
  :meth:`Storage.insert`, :meth:`Storage.retrieve` and :meth:`Storage.delete` are
  frequently used from a user point of view.
* The :class:`Cache` abstract class is a specialisation of the :class:`Storage`
  class that handles data resources locally (i.e. data hosted on the same machine
  that are readily and timelessly accessible). In this module, various concrete
  implementations are provided for this class in order to support various cache
  flavors.
* The :class:`Archive` class (readily usable) is a specialisation of the
  :class:`Storage` class dedicated to data resources stored remotely (e.g on a
  mass archive system).

These classes purely focus on the technical aspects (e.g. how to transfer a given
filename, directory or file like object to its storage place). For :class:`Cache`
based storage it determines the location of the data on the filesystem, in a
database, ... For :class:`Archive` based storage it smoothly handles communication
protocol between the local host and the remote archive.

These classes are used by :class:`Store` objects to access data. Thus,
:class:`Store` objects do not need to worry anymore about the technical
aspects. Using the :mod:`footprints` package, for a given execution target, it
allows to customise the way data are accessed leaving the :class:`Store` objects
unchanged.
"""

import contextlib
import ftplib
import re
import time
from datetime import datetime

import footprints
from bronx.fancies import loggers
from bronx.stdtypes.history import History
from bronx.syntax.decorators import nicedeco
from vortex import sessions
from vortex.tools.actions import actiond as ad
from vortex.tools.delayedactions import d_action_status

from vortex import config

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

# If the source file size exceed this threshold, a hard link will be
# used (as much as possible). Otherwise a simple copy will be used.
HARDLINK_THRESHOLD = 1048576


# Decorators: for internal use in the Storage class
# -------------------------------------------------


def do_recording(flag):
    """Add a record line in the History object (if sensible)."""

    @nicedeco
    def do_flagged_recording(f):
        def wrapped_action(self, item, *kargs, **kwargs):
            infos = self._findout_record_infos(kwargs)
            (rc, extrainfos) = f(self, item, *kargs, **kwargs)
            infos.update(extrainfos)
            self.addrecord(flag, item, status=rc, **infos)
            return rc

        return wrapped_action

    return do_flagged_recording


@nicedeco
def enforce_readonly(f):
    """Check that the current storage object is not readonly."""

    def wrapped_action(self, item, *kargs, **kwargs):
        if self.readonly:
            raise OSError("This Storage place is readonly.")
        return f(self, item, *kargs, **kwargs)

    return wrapped_action


# Main Storage abstract class
# ---------------------------


class Storage(footprints.FootprintBase):
    """Root class for any Storage class, ex: Cache, Archive, ...

    Tips for developers:

    The following methods needs to be defined in the child classes:

        * *_actual_fullpath*
        * *_actual_prestageinfo*
        * *_actual_check*
        * *_actual_list*
        * *_actual_insert*
        * *_actual_retrieve*
        * *_actual_delete*

    They must return a two elements tuple consisting of a returncode and a
    dictionary whose items will be written in the object's record.
    """

    _abstract = (True,)
    _footprint = dict(
        info="Default/Abstract storage place description.",
        attr=dict(
            storage=dict(
                info="The storage target.",
            ),
            record=dict(
                info="Record insert, retrieve, delete actions in an History object.",
                type=bool,
                optional=True,
                default=False,
                access="rwx",
            ),
            readonly=dict(
                info="Disallow insert and delete action for this storage place.",
                type=bool,
                optional=True,
                default=False,
            ),
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug("Abstract storage init %s", self.__class__)
        super().__init__(*args, **kw)
        self._history = History(tag=self.tag)

    @property
    def tag(self):
        """The identifier of the storage place."""
        raise NotImplementedError()

    @property
    def realkind(self):
        return "storage"

    def _str_more(self):
        return "tag={:s}".format(self.tag)

    @property
    def context(self):
        """Shortcut to the active context object."""
        return sessions.get().context

    @property
    def session(self):
        return sessions.current()

    @property
    def sh(self):
        """Shortcut to the active System object."""
        return sessions.system()

    @property
    def history(self):
        """The History object that will be used by this storage place.

        :note: History objects are associated with the self.tag identifier. i.e.
               all Storage's objects with the same tag will use the same History
               object.
        """
        return self._history

    def addrecord(self, action, item, **infos):
        """Push a new record to the storage place log/history."""
        if self.record:
            self.history.append(action, item, infos)

    def flush(self, dumpfile=None):
        """Flush actual history to the specified ``dumpfile`` if record is on.

        :note: May raise the :class:`NotImplementedError` exception.
        """
        raise NotImplementedError()

    def _findout_record_infos(self, kwargs):
        return dict(info=kwargs.get("info", None))

    def allow_reads(self, item):  # @UnusedVariable
        """
        This method can be used to determine whether or not the present object
        supports reads for **item**.

        :note: This is different from **check** since, **item**'s existence is
               not checked. It just tells if reads to **item** are supported...
        """
        return True

    def allow_writes(self, item):  # @UnusedVariable
        """
        This method can be used to determine whether or not the present object
        supports writes for **item**.

        :note: This is different from **check** since, **item**'s existence is
               not checked. It just tells if writes to **item** are supported...
        """
        return True

    def fullpath(self, item, **kwargs):
        """Return the path/URI to the **item**'s storage location."""
        # Currently no recording is performed for the check action
        (rc, _) = self._actual_fullpath(item, **kwargs)
        return rc

    def prestageinfo(self, item, **kwargs):
        """Return the prestage infos for an **item** in the current storage place."""
        # Currently no recording is performed for the check action
        (rc, _) = self._actual_prestageinfo(item, **kwargs)
        return rc

    def check(self, item, **kwargs):
        """Check/Stat an **item** from the current storage place."""
        # Currently no recording is performed for the check action
        (rc, _) = self._actual_check(item, **kwargs)
        return rc

    def list(self, item, **kwargs):
        """List all data resources available in the **item** directory."""
        # Currently no recording is performed for the check action
        (rc, _) = self._actual_list(item, **kwargs)
        return rc

    @enforce_readonly
    @do_recording("INSERT")
    def insert(self, item, local, **kwargs):
        """Insert an **item** in the current storage place.

        :note: **local** may be a path to a file or any kind of file like objects.
        """
        return self._actual_insert(item, local, **kwargs)

    @do_recording("RETRIEVE")
    def retrieve(self, item, local, **kwargs):
        """Retrieve an **item** from the current storage place.

        :note: **local** may be a path to a file or any kind of file like objects.
        """
        return self._actual_retrieve(item, local, **kwargs)

    def earlyretrieve(self, item, local, **kwargs):
        """Trigger a delayed retrieve of **item** from the current storage place.

        :note: **local** may be a path to a file or any kind of file like objects.
        """
        return self._actual_earlyretrieve(item, local, **kwargs)

    def _actual_earlyretrieve(self, item, local, **kwargs):  # @UnusedVariable
        """No earlyretrieve implemented by default."""
        return None

    def finaliseretrieve(self, retrieve_id, item, local, **kwargs):
        """Finalise a delayed retrieve from the current storage place.

        :note: **local** may be a path to a file or any kind of file like objects.
        """
        rc, idict = self._actual_finaliseretrieve(
            retrieve_id, item, local, **kwargs
        )
        if rc is not None:
            infos = self._findout_record_infos(kwargs)
            infos.update(idict)
            self.addrecord("RETRIEVE", item, status=rc, **infos)
        return rc

    def _actual_finaliseretrieve(
        self, retrieve_id, item, local, **kwargs
    ):  # @UnusedVariable
        """No delayedretrieve implemented by default."""
        return None, dict()

    @enforce_readonly
    @do_recording("DELETE")
    def delete(self, item, **kwargs):
        """Delete an **item** from the current storage place."""
        return self._actual_delete(item, **kwargs)


# Defining the two main flavours of storage places
# -----------------------------------------------


class Cache(Storage):
    """Root class for any :class:Cache subclasses."""

    _collector = ("cache",)
    _footprint = dict(
        info="Default cache description",
        attr=dict(
            entry=dict(
                optional=False,
                type=str,
                info="The absolute path to the cache space",
            ),
            # TODO is 'storage' used in any way?
            storage=dict(
                optional=True,
                default="localhost",
            ),
            rtouch=dict(
                info="Perform the recursive touch command on the directory structure.",
                type=bool,
                optional=True,
                default=False,
            ),
            rtouchskip=dict(
                info="Do not 'touch' the first **rtouchskip** directories.",
                type=int,
                optional=True,
                default=0,
            ),
            rtouchdelay=dict(
                info=(
                    "Do not perfom a touch if it has already been done in "
                    + "the last X seconds."
                ),
                type=float,
                optional=True,
                default=600.0,  # 10 minutes
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._touch_tracker = dict()

    @property
    def realkind(self):
        return "cache"

    @property
    def tag(self):
        """The identifier of this cache place."""
        return "{:s}_{:s}".format(self.realkind, self.entry)

    def _formatted_path(self, subpath, **kwargs):  # @UnusedVariable
        return self.sh.path.join(self.entry, subpath.lstrip("/"))

    def catalog(self):
        """List all files present in this cache.

        :note: It might be quite slow...
        """
        entry = self.sh.path.expanduser(self.entry)
        files = self.sh.ffind(entry)
        return [f[len(entry) :] for f in files]

    def _xtouch(self, path):
        """
        Perform a touch operation only if the last one, on te same path, was
        less than `self.rtouchdelay` seconds ago.
        """
        ts = time.time()
        ts_delay = ts - self._touch_tracker.get(path, 0)
        if ts_delay > self.rtouchdelay:
            logger.debug("Touching: %s (delay was %.2f)", path, ts_delay)
            self.sh.touch(path)
            self._touch_tracker[path] = ts
        else:
            logger.debug("Skipping touch: %s (delay was %.2f)", path, ts_delay)

    def _recursive_touch(self, rc, item, writing=False):
        """Make recursive touches on parent directories.

        It might be useful for cleaning scripts.
        """
        if self.rtouch and (not self.readonly) and rc:
            items = item.lstrip("/").split("/")
            items = items[:-1]
            if writing:
                # It's useless to touch the rightmost directory
                items = items[:-1] if len(items) > 1 else []
            for index in range(len(items), self.rtouchskip, -1):
                self._xtouch(
                    self._formatted_path(self.sh.path.join(*items[:index]))
                )

    def _actual_fullpath(self, item, **kwargs):
        """Return the path/URI to the **item**'s storage location."""
        return self._formatted_path(item, **kwargs), dict()

    def _actual_prestageinfo(self, item, **kwargs):
        """Returns pre-staging informations."""
        return dict(
            strategy="std", location=self.fullpath(item, **kwargs)
        ), dict()

    def _actual_check(self, item, **kwargs):
        """Check/Stat an **item** from the current storage place."""
        path = self._formatted_path(item, **kwargs)
        if path is None:
            return None, dict()
        try:
            st = self.sh.stat(path)
        except OSError:
            st = None
        return st, dict()

    def _actual_list(self, item, **kwargs):
        """List all data resources available in the **item** directory."""
        path = self.fullpath(item, **kwargs)
        if path is not None and self.sh.path.exists(path):
            if self.sh.path.isdir(path):
                return self.sh.listdir(path), dict()
            else:
                return True, dict()
        else:
            return None, dict()

    def _actual_insert(self, item, local, **kwargs):
        """Insert an **item** in the current storage place."""
        # Get the relevant options
        intent = kwargs.get("intent", "in")
        fmt = kwargs.get("fmt", "foo")
        # Insert the element
        tpath = self._formatted_path(item)
        if not self.sh.path.exists(self.entry):
            self.sh.mkdir(self.entry)
        if tpath is not None:
            rc = self.sh.cp(
                local,
                tpath,
                intent=intent,
                fmt=fmt,
                smartcp_threshold=HARDLINK_THRESHOLD,
            )
        else:
            logger.warning("No target location for < %s >", item)
            rc = False
        self._recursive_touch(rc, item, writing=True)
        return rc, dict(intent=intent, fmt=fmt)

    def _actual_retrieve(self, item, local, **kwargs):
        """Retrieve an **item** from the current storage place."""
        # Get the relevant options
        intent = kwargs.get("intent", "in")
        fmt = kwargs.get("fmt", "foo")
        silent = kwargs.get("silent", False)
        dirextract = kwargs.get("dirextract", False)
        tarextract = kwargs.get("tarextract", False)
        uniquelevel_ignore = kwargs.get("uniquelevel_ignore", True)
        source = self._formatted_path(item)
        if source is not None:
            # If auto_dirextract, copy recursively each file contained in source
            if (
                dirextract
                and self.sh.path.isdir(source)
                and self.sh.is_tarname(local)
            ):
                rc = True
                destdir = self.sh.path.dirname(self.sh.path.realpath(local))
                logger.info("Automatic directory extract to: %s", destdir)
                for subpath in self.sh.glob(source + "/*"):
                    rc = rc and self.sh.cp(
                        subpath,
                        self.sh.path.join(
                            destdir, self.sh.path.basename(subpath)
                        ),
                        intent=intent,
                        fmt=fmt,
                        smartcp_threshold=HARDLINK_THRESHOLD,
                    )
                    # For the insitu feature to work...
                    rc = rc and self.sh.touch(local)
            # The usual case: just copy source
            else:
                rc = self.sh.cp(
                    source,
                    local,
                    intent=intent,
                    fmt=fmt,
                    silent=silent,
                    smartcp_threshold=HARDLINK_THRESHOLD,
                )
                # If auto_tarextract, a potential tar file is extracted
                if (
                    rc
                    and tarextract
                    and not self.sh.path.isdir(local)
                    and self.sh.is_tarname(local)
                    and self.sh.is_tarfile(local)
                ):
                    destdir = self.sh.path.dirname(
                        self.sh.path.realpath(local)
                    )
                    logger.info("Automatic Tar extract to: %s", destdir)
                    rc = rc and self.sh.smartuntar(
                        local, destdir, uniquelevel_ignore=uniquelevel_ignore
                    )
        else:
            getattr(logger, "info" if silent else "warning")(
                "No readable source for < %s >", item
            )
            rc = False
        self._recursive_touch(rc, item)
        return rc, dict(intent=intent, fmt=fmt)

    def _actual_delete(self, item, **kwargs):
        """Delete an **item** from the current storage place."""
        # Get the relevant options
        fmt = kwargs.get("fmt", "foo")
        # Delete the element
        tpath = self._formatted_path(item)
        if tpath is not None:
            rc = self.sh.remove(tpath, fmt=fmt)
        else:
            logger.warning("No target location for < %s >", item)
            rc = False
        return rc, dict(fmt=fmt)

    def flush(self, dumpfile=None):
        """Flush actual history to the specified ``dumpfile`` if record is on."""
        if dumpfile is None:
            logfile = ".".join(
                (
                    "HISTORY",
                    datetime.now().strftime("%Y%m%d%H%M%S.%f"),
                    "P{:06d}".format(self.sh.getpid()),
                    self.sh.getlogname(),
                )
            )
            dumpfile = self.sh.path.join(self.entry, ".history", logfile)
        if self.record:
            self.sh.pickle_dump(self.history, dumpfile)


class AbstractArchive(Storage):
    """The default class to handle storage to some kind if Archive."""

    _abstract = True
    _collector = ("archive",)
    _footprint = dict(
        info="Default archive description",
        attr=dict(
            tube=dict(
                info="How to communicate with the archive ?",
            ),
        ),
    )

    @property
    def tag(self):
        """The identifier of this cache place."""
        return "{:s}_{:s}".format(self.realkind, self.storage)

    @property
    def realkind(self):
        return "archive"

    def _formatted_path(self, rawpath, **kwargs):
        root = kwargs.get("root", None)
        if root is not None:
            rawpath = self.sh.path.join(root, rawpath.lstrip("/"))
        # Deal with compression
        compressionpipeline = kwargs.get("compressionpipeline", None)
        if compressionpipeline is not None:
            rawpath += compressionpipeline.suffix
        return self.sh.anyft_remote_rewrite(
            rawpath, fmt=kwargs.get("fmt", "foo")
        )

    def _actual_proxy_method(self, pmethod):
        """Create a proxy method based on the **pmethod** actual method."""

        def actual_proxy(item, *kargs, **kwargs):
            path = self._formatted_path(item, **kwargs)
            if path is None:
                raise ValueError("The archive's path is void.")
            return pmethod(path, *kargs, **kwargs)

        actual_proxy.__name__ = pmethod.__name__
        actual_proxy.__doc__ = pmethod.__doc__
        return actual_proxy

    def __getattr__(self, attr):
        """Provides proxy methods for _actual_* methods."""
        methods = r"fullpath|prestageinfo|check|list|insert|retrieve|delete"
        mattr = re.match(r"_actual_(?P<action>" + methods + r")", attr)
        if mattr:
            pmethod = getattr(
                self, "_{:s}{:s}".format(self.tube, mattr.group("action"))
            )
            return self._actual_proxy_method(pmethod)
        else:
            raise AttributeError(
                "The {:s} attribute was not found in this object".format(attr)
            )

    def _actual_earlyretrieve(self, item, local, **kwargs):
        """Proxy to the appropriate tube dependent earlyretrieve method (if available)."""
        pmethod = getattr(
            self, "_{:s}{:s}".format(self.tube, "earlyretrieve"), None
        )
        if pmethod:
            return self._actual_proxy_method(pmethod)(item, local, **kwargs)
        else:
            return None

    def _actual_finaliseretrieve(self, retrieve_id, item, local, **kwargs):
        """Proxy to the appropriate tube dependent finaliseretrieve method (if available)."""
        pmethod = getattr(
            self, "_{:s}{:s}".format(self.tube, "finaliseretrieve"), None
        )
        if pmethod:
            return self._actual_proxy_method(pmethod)(
                item, local, retrieve_id, **kwargs
            )
        else:
            return None, dict()


class Archive(AbstractArchive):
    """The default class to handle storage to a remote location."""

    _footprint = dict(
        info="Default archive description",
        attr=dict(
            tube=dict(
                values=["ftp"],
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.default_usejeeves = config.from_config(
            section="storage",
            key="usejeeves",
        )

    @property
    def _ftp_hostinfos(self):
        """Return the FTP hostname end port number."""
        s_storage = self.storage.split(":", 1)
        hostname = s_storage[0]
        port = None
        if len(s_storage) > 1:
            try:
                port = int(s_storage[1])
            except ValueError:
                logger.error(
                    "Invalid port number < %s >. Ignoring it", s_storage[1]
                )
        return hostname, port

    def _ftp_client(self, logname=None, delayed=False):
        """Return a FTP client object."""
        hostname, port = self._ftp_hostinfos
        return self.sh.ftp(
            hostname, logname=logname, delayed=delayed, port=port
        )

    def _ftpfullpath(self, item, **kwargs):
        """Actual _fullpath using ftp."""
        username = kwargs.get("username", None)
        rc = None
        ftp = self._ftp_client(logname=username, delayed=True)
        if ftp:
            try:
                rc = ftp.netpath(item)
            finally:
                ftp.close()
        return rc, dict()

    def _ftpprestageinfo(self, item, **kwargs):
        """Actual _prestageinfo using ftp."""
        username = kwargs.get("username", None)
        if username is None:
            ftp = self._ftp_client(logname=username, delayed=True)
            if ftp:
                try:
                    username = ftp.logname
                finally:
                    ftp.close()
        baseinfo = dict(
            storage=self.storage,
            logname=username,
            location=item,
        )
        return baseinfo, dict()

    def _ftpcheck(self, item, **kwargs):
        """Actual _check using ftp."""
        rc = None
        ftp = self._ftp_client(logname=kwargs.get("username", None))
        if ftp:
            try:
                rc = ftp.size(item)
            except (ValueError, TypeError):
                pass
            except ftplib.all_errors:
                pass
            finally:
                ftp.close()
        return rc, dict()

    def _ftplist(self, item, **kwargs):
        """Actual _list using ftp."""
        ftp = self._ftp_client(logname=kwargs.get("username", None))
        rc = None
        if ftp:
            try:
                # Is this a directory ?
                rc = ftp.cd(item)
            except ftplib.all_errors:
                # Apparently not...
                try:
                    # Is it a file ?
                    if ftp.size(item) is not None:
                        rc = True
                except (ValueError, TypeError):
                    pass
                except ftplib.all_errors:
                    pass
            else:
                # Content of the directory...
                if rc:
                    rc = ftp.nlst(".")
            finally:
                ftp.close()
        return rc, dict()

    def _ftpretrieve(self, item, local, **kwargs):
        """Actual _retrieve using ftp."""
        logger.info(
            "ftpget on ftp://%s/%s (to: %s)", self.storage, item, local
        )
        extras = dict(
            fmt=kwargs.get("fmt", "foo"),
            cpipeline=kwargs.get("compressionpipeline", None),
        )
        hostname, port = self._ftp_hostinfos
        if port is not None:
            extras["port"] = port
        rc = self.sh.smartftget(
            item,
            local,
            # Ftp control
            hostname=hostname,
            logname=kwargs.get("username", None),
            **extras,
        )
        return rc, extras

    def _ftpearlyretrieve(self, item, local, **kwargs):
        """
        If FtServ/ftraw is used, trigger a delayed action in order to fetch
        several files at once.
        """
        cpipeline = kwargs.get("compressionpipeline", None)
        if self.sh.rawftget_worthy(item, local, cpipeline):
            return self.context.delayedactions_hub.register(
                (item, kwargs.get("fmt", "foo")),
                kind="archive",
                storage=self.storage,
                goal="get",
                tube="ftp",
                raw=True,
                logname=kwargs.get("username", None),
            )
        else:
            return None

    def _ftpfinaliseretrieve(
        self, item, local, retrieve_id, **kwargs
    ):  # @UnusedVariable
        """
        Get the resource given the **retrieve_id** identifier returned by the
        :meth:`_ftpearlyretrieve` method.
        """
        extras = dict(
            fmt=kwargs.get("fmt", "foo"),
        )
        d_action = self.context.delayedactions_hub.retrieve(
            retrieve_id, bareobject=True
        )
        if d_action.status == d_action_status.done:
            if self.sh.filecocoon(local):
                rc = self.sh.mv(d_action.result, local, **extras)
            else:
                raise OSError("Could not cocoon: {!s}".format(local))
        elif d_action.status == d_action_status.failed:
            logger.info(
                "The earlyretrieve failed (retrieve_id=%s)", retrieve_id
            )
            rc = False
        else:
            rc = None
        return rc, extras

    def _ftpinsert(self, item, local, **kwargs):
        """Actual _insert using ftp."""
        usejeeves = kwargs.get("usejeeves", None)
        if usejeeves is None:
            usejeeves = self.default_usejeeves
        hostname, port = self._ftp_hostinfos
        if not usejeeves:
            logger.info(
                "ftpput to ftp://%s/%s (from: %s)", self.storage, item, local
            )
            extras = dict(
                fmt=kwargs.get("fmt", "foo"),
                cpipeline=kwargs.get("compressionpipeline", None),
            )
            if port is not None:
                extras["port"] = port
            rc = self.sh.smartftput(
                local,
                item,
                # Ftp control
                hostname=hostname,
                logname=kwargs.get("username", None),
                sync=kwargs.get("enforcesync", False),
                **extras,
            )
        else:
            logger.info(
                "delayed ftpput to ftp://%s/%s (from: %s)",
                self.storage,
                item,
                local,
            )
            tempo = footprints.proxy.service(
                kind="hiddencache", asfmt=kwargs.get("fmt")
            )
            compressionpipeline = kwargs.get("compressionpipeline", "")
            if compressionpipeline:
                compressionpipeline = compressionpipeline.description_string
            extras = dict(
                fmt=kwargs.get("fmt", "foo"), cpipeline=compressionpipeline
            )
            if port is not None:
                extras["port"] = port

            rc = ad.jeeves(
                hostname=hostname,
                # Explicitly resolve the logname (because jeeves FTP client is not
                # running with the same glove (i.e. Jeeves ftuser configuration may
                # be different).
                logname=self.sh.fix_ftuser(
                    hostname, kwargs.get("username", None)
                ),
                todo="ftput",
                rhandler=kwargs.get("info", None),
                source=tempo(local),
                destination=item,
                original=self.sh.path.abspath(local),
                **extras,
            )
        return rc, extras

    def _ftpdelete(self, item, **kwargs):
        """Actual _delete using ftp."""
        rc = None
        ftp = self._ftp_client(logname=kwargs.get("username", None))
        if ftp:
            if self._ftpcheck(item, **kwargs)[0]:
                logger.info("ftpdelete on ftp://%s/%s", self.storage, item)
                rc = ftp.delete(item)
                ftp.close()
            else:
                logger.error(
                    "Try to remove a non-existing resource <%s>", item
                )
        return rc, dict()


class AbstractLocalArchive(AbstractArchive):
    """The default class to handle storage to the same host."""

    _abstract = True
    _footprint = dict(
        info="Generic local archive description",
        attr=dict(
            tube=dict(
                values=[
                    "inplace",
                ],
            ),
        ),
    )

    def _inplacefullpath(self, item, **kwargs):
        """Actual _fullpath."""
        return item, dict()

    def _inplacecheck(self, item, **kwargs):
        """Actual _check."""
        try:
            st = self.sh.stat(item)
        except OSError:
            rc = None
        else:
            rc = st.st_size
        return rc, dict()

    def _inplacelist(self, item, **kwargs):
        """Actual _list."""
        if self.sh.path.exists(item):
            if self.sh.path.isdir(item):
                return self.sh.listdir(item), dict()
            else:
                return True, dict()
        else:
            return None, dict()

    def _inplaceretrieve(self, item, local, **kwargs):
        """Actual _retrieve using ftp."""
        logger.info("inplaceget on file:///%s (to: %s)", item, local)
        fmt = kwargs.get("fmt", "foo")
        cpipeline = kwargs.get("compressionpipeline", None)
        if cpipeline:
            rc = cpipeline.file2uncompress(item, local)
        else:
            # Do not use fmt=... on purpose (otherwise "forceunpack" may be called twice)
            rc = self.sh.cp(item, local, intent="in")
        rc = rc and self.sh.forceunpack(local, fmt=fmt)
        return rc, dict(fmt=fmt, cpipeline=cpipeline)

    @contextlib.contextmanager
    def _inplaceinsert_pack(self, local, fmt):
        local_packed = self.sh.forcepack(local, fmt=fmt)
        if local_packed != local:
            try:
                yield local_packed
            finally:
                self.sh.rm(local_packed, fmt=fmt)
        else:
            yield local

    def _inplaceinsert(self, item, local, **kwargs):
        """Actual _insert using ftp."""
        logger.info("inplaceput to file:///%s (from: %s)", item, local)
        cpipeline = kwargs.get("compressionpipeline", None)
        fmt = kwargs.get("fmt", "foo")
        with self._inplaceinsert_pack(local, fmt) as local_packed:
            if cpipeline:
                rc = cpipeline.compress2file(local_packed, item)
            else:
                # Do not use fmt=... on purpose (otherwise "forcepack" may be called twice)
                rc = self.sh.cp(local_packed, item, intent="in")
        return rc, dict(fmt=fmt, cpipeline=cpipeline)

    def _inplacedelete(self, item, **kwargs):
        """Actual _delete using ftp."""
        fmt = kwargs.get("fmt", "foo")
        rc = None
        if self._inplacecheck(item, **kwargs)[0]:
            rc = self.sh.rm(item, fmt=fmt)
        return rc, dict(fmt=fmt)


class LocalArchive(AbstractLocalArchive):
    """The default class to handle storage to the same host."""

    _footprint = dict(
        info="Default local archive description",
        attr=dict(
            storage=dict(
                values=[
                    "localhost",
                ],
            ),
            auto_self_expand=dict(
                info=(
                    "Automatically expand the current user home if "
                    + "a relative path is given (should always be True "
                    + "except during unit-testing)"
                ),
                type=bool,
                default=True,
                optional=True,
            ),
        ),
    )

    def _formatted_path(self, rawpath, **kwargs):
        rawpath = self.sh.path.expanduser(rawpath)
        if "~" in rawpath:
            raise OSError('User expansion failed for "{:s}"'.format(rawpath))
        if self.auto_self_expand and not self.sh.path.isabs(rawpath):
            rawpath = self.sh.path.expanduser(self.sh.path.join("~", rawpath))
        return super()._formatted_path(rawpath, **kwargs)
