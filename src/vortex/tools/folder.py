"""
Various shell addons that handle formats relying on a folder structure.

In any kind of cache directories, the folder structure is kept as is. When
data are sent using FTP or SSH, a tar file is created on the fly.
"""

import contextlib
import ftplib
import tempfile

from bronx.fancies import loggers
from vortex.tools.net import DEFAULT_FTP_PORT
from vortex.util.iosponge import IoSponge
from . import addons

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

_folder_exposed_methods = {
    "cp",
    "mv",
    "forcepack",
    "forceunpack",
    "anyft_remote_rewrite",
    "ftget",
    "rawftget",
    "batchrawftget",
    "ftput",
    "rawftput",
    "scpget",
    "scpput",
    "ecfsget",
    "ecfsput",
    "ectransget",
    "ectransput",
}


def folderize(cls):
    """Create the necessary methods in a class that inherits from :class:`FolderShell`."""
    addon_kind = cls.footprint_retrieve().get_values("kind")
    if len(addon_kind) != 1:
        raise SyntaxError(
            "Authorised values for a given Addon's kind must be unique"
        )
    addon_kind = addon_kind[0]
    for basic_mtdname in _folder_exposed_methods:
        expected_mtdname = "{:s}_{:s}".format(addon_kind, basic_mtdname)
        if not hasattr(cls, expected_mtdname):
            parent_mtd = getattr(cls, "_folder_{:s}".format(basic_mtdname))
            setattr(cls, expected_mtdname, parent_mtd)
    return cls


class FolderShell(addons.FtrawEnableAddon):
    """
    This abstract class defines methods to manipulate folders.
    """

    _COMPRESSED = "gz"

    _abstract = True
    _footprint = dict(
        info="Tools for manipulating folders",
        attr=dict(
            kind=dict(
                values=["folder"],
            ),
            tmpname=dict(
                optional=True,
                default="folder_tmpunpack",
            ),
            pipeget=dict(
                type=bool,
                optional=True,
                default=False,
            ),
            supportedfmt=dict(
                optional=True,
                default="[kind]",
            ),
        ),
    )

    def _folder_cp(
        self,
        source,
        destination,
        smartcp_threshold=0,
        intent="in",
        silent=False,
    ):
        """Extended copy for a folder repository."""
        rc, source, destination = self._folder_tarfix_out(source, destination)
        rc = rc and self.sh.cp(
            source,
            destination,
            smartcp_threshold=smartcp_threshold,
            intent=intent,
        )
        if rc:
            rc, source, destination = self._folder_tarfix_in(
                source, destination
            )
            if rc and intent == "inout":
                self.sh.stderr("chmod", 0o644, destination)
                with self.sh.mute_stderr():
                    for infile in self.sh.ffind(destination):
                        self.sh.chmod(infile, 0o644)
        return rc

    def _folder_mv(self, source, destination):
        """Shortcut to :meth:`move` method (file or directory)."""
        if not isinstance(source, str) or not isinstance(destination, str):
            rc = self.sh.hybridcp(source, destination)
            if isinstance(source, str):
                rc = rc and self.sh.remove(source)
        else:
            rc, source, destination = self._folder_tarfix_out(
                source, destination
            )
            rc = rc and self.sh.move(source, destination)
            if rc:
                rc, source, destination = self._folder_tarfix_in(
                    source, destination
                )
        return rc

    def _folder_forcepack(self, source, destination=None):
        """Returned a path to a packed data."""
        if not self.sh.is_tarname(source):
            destination = (
                destination
                if destination
                else "{:s}.{:s}".format(
                    self.sh.safe_fileaddsuffix(source),
                    self._folder_tarfix_extension,
                )
            )
            if not self.sh.path.exists(destination):
                absdestination = self.sh.path.abspath(destination)
                with self.sh.cdcontext(self.sh.path.dirname(source)):
                    self.sh.tar(absdestination, self.sh.path.basename(source))
            return destination
        else:
            return source

    def _folder_forceunpack(self, source):
        """Unpack the data "inplace"."""
        fakesource = "{:s}.{:s}".format(
            self.sh.safe_fileaddsuffix(source), self._folder_tarfix_extension
        )
        rc, _, _ = self._folder_tarfix_in(fakesource, source)
        return rc

    def _folder_pack_stream(self, source, stdout=True):
        source_name = self.sh.path.basename(source)
        source_dirname = self.sh.path.dirname(source)
        compression_map = {"gz": "z", "bz2": "j"}
        compression_opt = compression_map.get(self._COMPRESSED, "")
        cmd = [
            "tar",
            "--directory",
            source_dirname,
            "-c" + compression_opt,
            source_name,
        ]
        return self.sh.popen(cmd, stdout=stdout, bufsize=8192)

    def _folder_unpack_stream(self, stdin=True, options="xvf"):
        return self.sh.popen(
            # the z option is omitted consequently it also works if the file is not compressed
            ["tar", options, "-"],
            stdin=stdin,
            bufsize=8192,
        )

    def _packed_size(self, source):
        """Size of the final file, must be exact or be an overestimation.

        A file 1 byte bigger than this estimation might be rejected,
        hence the conservative options:
        - tar adds 1% with a minimum of 1 Mbytes
        - compression gain is 0%
        """
        dir_size = self.sh.treesize(source)
        tar_mini = 1024 * 1024  # 1 Mbytes
        tar_loss = 1  # 1%
        zip_gain = 0
        tar_size = dir_size + max(tar_mini, (dir_size * tar_loss) // 100)
        return (tar_size * (100 - zip_gain)) // 100

    def _folder_preftget(self, source, destination):
        """Prepare source and destination"""
        destination = self.sh.path.abspath(
            self.sh.path.expanduser(destination)
        )
        self.sh.rm(destination)
        return source, destination

    def _folder_postftget(self, destination):
        """Move the untared stuff to the destination and clean-up things."""
        try:
            unpacked = self.sh.glob("*")
            if unpacked:
                if len(unpacked) == 1 and self.sh.path.isdir(
                    self.sh.path.join(unpacked[-1])
                ):
                    # This is the most usual case... (ODB, DDH packs produced by Vortex)
                    self.sh.wpermtree(unpacked[-1], force=True)
                    if self.sh.path.isdir(unpacked[-1]):
                        with self.sh.secure_directory_move(destination):
                            self.sh.mv(unpacked[-1], destination)
                    else:
                        self.sh.mv(unpacked[-1], destination)
                else:
                    # Old-style DDH packs (produced by Olive)
                    with self.sh.secure_directory_move(destination):
                        self.sh.mkdir(destination)
                        for item in unpacked:
                            self.sh.wpermtree(item, force=True)
                            self.sh.mv(
                                item, self.sh.path.join(destination, item)
                            )
            else:
                logger.error("Nothing to unpack")
        except Exception as trouble:
            logger.critical("Unable to proceed folder post-ftget step")
            raise trouble

    @contextlib.contextmanager
    def _folder_postftget_context(self, destination):
        """Move the untared stuff to the destination and clean-up things."""
        with self.sh.temporary_dir_cdcontext(
            prefix="folder_", dir=self.sh.getcwd()
        ):
            try:
                yield
            finally:
                self._folder_postftget(destination)

    @contextlib.contextmanager
    def _folder_ftget_file_extract(self, source):
        ext_name = self.sh.tarname_splitext(source)[1]
        target = self.tmpname + ext_name
        try:
            yield target
            if self.sh.path.exists(target):
                self.sh.untar(target, autocompress=False)
        finally:
            self.sh.rm(target)

    @contextlib.contextmanager
    def _folder_ftget_pipe_extract(self):
        p = self._folder_unpack_stream()
        yield p
        self.sh.pclose(p)

    @contextlib.contextmanager
    def _folder_ftput_file_compress(self, source):
        c_source = (
            self.sh.safe_fileaddsuffix(source)
            + "."
            + self._folder_tarfix_extension
        )
        try:
            self.sh.tar(c_source, source)
            yield c_source
        finally:
            self.sh.rm(c_source)

    @contextlib.contextmanager
    def _folder_ftput_pipe_compress(self, source):
        p = self._folder_pack_stream(source)
        yield p
        self.sh.pclose(p)

    def _folder_anyft_remote_rewrite(self, remote):
        """Add the folder suffix before using file transfert protocols."""
        if not self.sh.is_tarname(self.sh.path.basename(remote)):
            return "{:s}.{:s}".format(remote, self._folder_tarfix_extension)
        else:
            return remote

    def _folder_ftget(
        self,
        source,
        destination,
        hostname=None,
        logname=None,
        port=DEFAULT_FTP_PORT,
        cpipeline=None,
    ):
        """Proceed direct ftp get on the specified target."""
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        hostname = self.sh.fix_fthostname(hostname)
        with self.sh.ftpcontext(hostname, logname, port=port) as ftp:
            if ftp:
                source, destination = self._folder_preftget(
                    source, destination
                )
                with self._folder_postftget_context(destination):
                    try:
                        if self.pipeget:
                            with self._folder_ftget_pipe_extract() as p:
                                rc = ftp.get(source, p.stdin)
                        else:
                            with self._folder_ftget_file_extract(
                                source
                            ) as tmp_target:
                                rc = ftp.get(source, tmp_target)
                    except ftplib.all_errors as e:
                        logger.warning("An FTP error occurred: %s", str(e))
                        rc = False
                return rc
            else:
                return False

    def _folder_rawftget(
        self,
        source,
        destination,
        hostname=None,
        logname=None,
        port=None,
        cpipeline=None,
    ):
        """Use ftserv as much as possible."""
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        if self.sh.ftraw:
            source, destination = self._folder_preftget(source, destination)
            with self._folder_postftget_context(destination):
                with self._folder_ftget_file_extract(source) as tmp_target:
                    rc = self.sh.ftserv_get(
                        source,
                        tmp_target,
                        hostname=hostname,
                        logname=logname,
                        port=port,
                    )
            return rc
        else:
            if port is None:
                port = DEFAULT_FTP_PORT
            return self._folder_ftget(
                source, destination, hostname, logname, port=port
            )

    def _folder_batchrawftget(
        self,
        source,
        destination,
        hostname=None,
        logname=None,
        port=None,
        cpipeline=None,
    ):
        """Use ftserv to fetch several folder-like resources."""
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        if self.sh.ftraw:
            actualsources = list()
            actualdestinations = list()
            tmpdestinations = list()
            try:
                for s, d in zip(source, destination):
                    actual_s, actual_d = self._folder_preftget(s, d)
                    actualsources.append(actual_s)
                    actualdestinations.append(actual_d)
                    d_dirname = self.sh.path.dirname(actual_d)
                    self.sh.mkdir(d_dirname)
                    d_tmpdir = tempfile.mkdtemp(
                        prefix="folder_", dir=d_dirname
                    )
                    d_extname = self.sh.tarname_splitext(actual_s)[1]
                    tmpdestinations.append(
                        self.sh.path.join(d_tmpdir, self.tmpname + d_extname)
                    )

                rc = self.sh.ftserv_batchget(
                    actualsources,
                    tmpdestinations,
                    hostname,
                    logname,
                    port=port,
                )

                for i, (d, t) in enumerate(
                    zip(actualdestinations, tmpdestinations)
                ):
                    if rc[i]:
                        with self.sh.cdcontext(self.sh.path.dirname(t)):
                            try:
                                try:
                                    rc[i] = rc[i] and bool(
                                        self.sh.untar(
                                            self.sh.path.basename(t),
                                            autocompress=False,
                                        )
                                    )
                                finally:
                                    self.sh.rm(t)
                            finally:
                                self._folder_postftget(d)
            finally:
                for t in tmpdestinations:
                    self.sh.rm(self.sh.path.dirname(t))
            return rc
        else:
            raise RuntimeError("You are not supposed to land here !")

    def _folder_ftput(
        self,
        source,
        destination,
        hostname=None,
        logname=None,
        port=DEFAULT_FTP_PORT,
        cpipeline=None,
        sync=False,
    ):
        """Proceed direct ftp put on the specified target."""
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        hostname = self.sh.fix_fthostname(hostname)
        source = self.sh.path.abspath(source)
        with self.sh.ftpcontext(hostname, logname, port=port) as ftp:
            if ftp:
                packed_size = self._packed_size(source)
                with self._folder_ftput_pipe_compress(source) as p:
                    sponge = IoSponge(p.stdout, guessed_size=packed_size)
                    try:
                        rc = ftp.put(
                            sponge, destination, size=sponge.size, exact=False
                        )
                    except ftplib.all_errors as e:
                        logger.warning("An FTP error occurred: %s", str(e))
                        rc = False
                return rc
            else:
                return False

    def _folder_rawftput(
        self,
        source,
        destination,
        hostname=None,
        logname=None,
        port=None,
        cpipeline=None,
        sync=False,
    ):
        """Use ftserv as much as possible."""
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        if self.sh.ftraw and self.rawftshell is not None:
            newsource = self.sh.copy2ftspool(
                source, nest=True, fmt=self.supportedfmt
            )
            request = self.sh.path.dirname(newsource) + ".request"
            with open(request, "w") as request_fh:
                request_fh.write(str(self.sh.path.dirname(newsource)))
            self.sh.readonly(request)
            rc = self.sh.ftserv_put(
                request,
                destination,
                hostname=hostname,
                logname=logname,
                port=port,
                specialshell=self.rawftshell,
                sync=sync,
            )
            self.sh.rm(request)
            return rc
        else:
            if port is None:
                port = DEFAULT_FTP_PORT
            return self._folder_ftput(
                source, destination, hostname, logname, port=port, sync=sync
            )

    def _folder_scpget(
        self, source, destination, hostname, logname=None, cpipeline=None
    ):
        """Retrieve a folder using scp."""
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        logname = self.sh.fix_ftuser(
            hostname, logname, fatal=False, defaults_to_user=False
        )
        ssh = self.sh.ssh(hostname, logname)
        rc = False
        source, destination = self._folder_preftget(source, destination)
        with self._folder_postftget_context(destination):
            with self._folder_ftget_pipe_extract() as p:
                rc = ssh.scpget_stream(source, p.stdin)
        return rc

    def _folder_scpput(
        self, source, destination, hostname, logname=None, cpipeline=None
    ):
        """Upload a folder using scp."""
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        source = self.sh.path.abspath(source)
        logname = self.sh.fix_ftuser(
            hostname, logname, fatal=False, defaults_to_user=False
        )
        ssh = self.sh.ssh(hostname, logname)
        with self._folder_ftput_pipe_compress(source) as p:
            rc = ssh.scpput_stream(p.stdout, destination)
        return rc

    @addons.require_external_addon("ecfs")
    def _folder_ecfsget(self, source, target, cpipeline=None, options=None):
        """Get a folder resource using ECfs.

        :param source: source file
        :param target: target file
        :param cpipeline: compression pipeline to be used, if provided
        :param options: list of options to be used
        :return: return code and additional attributes used
        """
        # The folder must not be compressed
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        source, target = self._folder_preftget(source, target)
        with self._folder_postftget_context(target):
            with self._folder_ftget_file_extract(source) as tmp_target:
                rc = self.sh.ecfsget(
                    source=source, target=tmp_target, options=options
                )
        return rc

    @addons.require_external_addon("ecfs")
    def _folder_ecfsput(self, source, target, cpipeline=None, options=None):
        """Put a folder resource using ECfs.

        :param source: source file
        :param target: target file
        :param cpipeline: compression pipeline to be used, if provided
        :param options: list of options to be used
        :return: return code and additional attributes used
        """
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        source = self.sh.path.abspath(source)
        with self._folder_ftput_file_compress(source) as c_source:
            rc = self.sh.ecfsput(
                source=c_source, target=target, options=options
            )
        return rc

    @addons.require_external_addon("ectrans")
    def _folder_ectransget(
        self, source, target, gateway=None, remote=None, cpipeline=None
    ):
        """Get a folder resource using ECtrans.

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline to be used, if provided
        :return: return code and additional attributes used
        """
        # The folder must not be compressed
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        source, target = self._folder_preftget(source, target)
        with self._folder_postftget_context(target):
            with self._folder_ftget_file_extract(source) as tmp_target:
                rc = self.sh.raw_ectransget(
                    source=source,
                    target=tmp_target,
                    gateway=gateway,
                    remote=remote,
                )
        return rc

    @addons.require_external_addon("ectrans")
    def _folder_ectransput(
        self,
        source,
        target,
        gateway=None,
        remote=None,
        cpipeline=None,
        sync=False,
    ):
        """Put a folder resource using ECtrans.

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline to be used, if provided
        :param bool sync: If False, allow asynchronous transfers.
        :return: return code and additional attributes used
        """
        if cpipeline is not None:
            raise OSError("It's not allowed to compress folder like data.")
        source = self.sh.path.abspath(source)
        with self._folder_ftput_file_compress(source) as c_source:
            rc = self.sh.raw_ectransput(
                source=c_source,
                target=target,
                gateway=gateway,
                remote=remote,
                sync=sync,
            )
        return rc

    @property
    def _folder_tarfix_extension(self):
        """Return the extension of tar file associated with this extension."""
        if self._COMPRESSED:
            if self._COMPRESSED == "gz":
                return "tgz"
            elif self._COMPRESSED == "bz2":
                return "tar.bz2"
            else:
                raise ValueError(
                    "Unsupported compression type: {:s}".format(
                        self._COMPRESSED
                    )
                )
        else:
            return "tar"

    def _folder_tarfix_in(self, source, destination):
        """Automatically untar **source** if **source** is a tarfile and **destination** is not.

        This is called after a copy was blindly done: a ``source='foo.tgz'`` might have
        been copied to ``destination='bar'``, which must be untarred here.
        """
        ok = True
        sh = self.sh
        if sh.is_tarname(source) and not sh.is_tarname(destination):
            logger.info(
                "tarfix_in: untar from get <%s> to <%s>", source, destination
            )
            (destdir, destfile) = sh.path.split(sh.path.abspath(destination))
            tar_ext = sh.tarname_splitext(source)[1]
            desttar = sh.path.abspath(destination + tar_ext)
            sh.remove(desttar)
            ok = ok and sh.move(destination, desttar)
            with sh.temporary_dir_cdcontext(prefix="untar_", dir=destdir):
                ok = ok and sh.untar(desttar, output=False)
                unpacked = sh.glob("*")
                ok = (
                    ok and len(unpacked) == 1
                )  # Only one element allowed in this kind of tarfiles
                ok = ok and sh.move(
                    unpacked[0], sh.path.join(destdir, destfile)
                )
                ok = ok and sh.remove(desttar)
        return (ok, source, destination)

    def _folder_tarfix_out(self, source, destination):
        """Automatically tar **source** if **destination** is a tarfile and **source** is not.

        This is called after a copy was blindly done: a directory might have been copied
        to ``destination='foo.tgz'`` or ``destination='foo.tar.bz2'``.
        The tar and compression implied by the name must be addressed here.
        """
        ok = True
        sh = self.sh
        if sh.is_tarname(destination) and not sh.is_tarname(source):
            logger.info(
                "tarfix_out: tar before put <%s> to <%s>", source, destination
            )
            tar_ext = sh.tarname_splitext(destination)[1]
            sourcetar = sh.path.abspath(source + tar_ext)
            source_rel = sh.path.basename(source)
            (sourcedir, sourcefile) = sh.path.split(sourcetar)
            with sh.cdcontext(sourcedir):
                ok = ok and sh.remove(sourcefile)
                ok = ok and sh.tar(sourcefile, source_rel, output=False)
            return (ok, sourcetar, destination)
        else:
            return (ok, source, destination)


@folderize
class OdbShell(FolderShell):
    """
    Default interface to ODB commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info="Default ODB system interface",
        attr=dict(
            kind=dict(
                values=["odb"],
            ),
        ),
    )


@folderize
class DdhPackShell(FolderShell):
    """
    Default interface to DDHpack commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info="Default DDHpack system interface",
        attr=dict(
            kind=dict(
                values=["ddhpack"],
            ),
        ),
    )


@folderize
class RawFilesShell(FolderShell):
    """
    Default interface to rawfiles commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info="Default (g)RRRRawfiles system interface",
        attr=dict(
            kind=dict(
                values=["rawfiles"],
            ),
        ),
    )


@folderize
class ObsLocationPackShell(FolderShell):
    """
    Default interface to  Obs Location packs commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info="Default Obs Location packs system interface",
        attr=dict(
            kind=dict(
                values=["obslocationpack"],
            ),
        ),
    )


@folderize
class ObsFirePackShell(FolderShell):
    """
    Default interface to Obs Fire packs commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info="Default Obs Location packs system interface",
        attr=dict(
            kind=dict(
                values=["obsfirepack"],
            ),
        ),
    )


@folderize
class WavesBCShell(FolderShell):
    """
    Default interface to waves bounding conditions commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info="Default waves BC system interface",
        attr=dict(
            kind=dict(
                values=["wbcpack"],
            ),
        ),
    )


@folderize
class FilesPackShell(FolderShell):
    """
    Default interface to files packs commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info="Default Files packs system interface",
        attr=dict(
            kind=dict(
                values=["filespack"],
            ),
        ),
    )


available_foldershells = [
    e.footprint_values("kind")[0]
    for e in locals().values()
    if (
        isinstance(e, type)
        and issubclass(e, FolderShell)
        and not e.footprint_abstract()
    )
]


class FolderShellsGroup(addons.AddonGroup):
    """The whole bunch of folder shells."""

    _footprint = dict(
        info="The whole bunch of folder shells",
        attr=dict(
            kind=dict(
                values=[
                    "allfolders",
                ],
            ),
        ),
    )

    _addonslist = available_foldershells
