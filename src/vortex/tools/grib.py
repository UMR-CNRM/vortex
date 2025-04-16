"""
Module needed to interact with GRIB files.

It provides shell addons to deal with:

    * Splitted GRIB files (as produced by the Arpege/IFS IO server)
    * The ability to compare GRIB files

It also provdes an AlgoComponent's Mixin to properly setup the environment
when using the grib_api or ecCodes libraries.
"""

from pathlib import Path
from urllib import parse as urlparse

import re

from bronx.fancies import loggers
import footprints

from . import addons
from vortex.config import get_from_config_w_default
from vortex.algo.components import (
    AlgoComponentDecoMixin,
    algo_component_deco_mixin_autodoc,
)
from vortex.tools.net import DEFAULT_FTP_PORT

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def use_in_shell(sh, **kw):
    """Extend current shell with the LFI interface defined by optional arguments."""
    kw["shell"] = sh
    return footprints.proxy.addon(**kw)


class GRIB_Tool(addons.FtrawEnableAddon):
    """
    Handle multipart-GRIB files properly.
    """

    _footprint = dict(
        info="Default GRIB system interface",
        attr=dict(
            kind=dict(
                values=["grib"],
            ),
        ),
    )

    def _std_grib_index_get(self, source):
        with open(source) as fd:
            gribparts = fd.read().splitlines()
        return [urlparse.urlparse(url).path for url in gribparts]

    xgrib_index_get = _std_grib_index_get

    def _std_grib_index_write(self, destination, gribpaths):
        gribparts = [
            str(urlparse.urlunparse(("file", "", path, "", "", "")))
            for path in gribpaths
        ]
        tmpfile = self.sh.safe_fileaddsuffix(destination)
        with open(tmpfile, "w") as fd:
            fd.write("\n".join(gribparts))
        return self.sh.move(tmpfile, destination)

    def is_xgrib(self, source):
        """Check if the given ``source`` is a multipart-GRIB file."""
        rc = False
        if source and isinstance(source, str) and self.sh.path.exists(source):
            with open(source, "rb") as fd:
                rc = fd.read(7) == b"file://"
        return rc

    def _backend_cp(
        self, source, destination, smartcp_threshold=0, intent="in"
    ):
        return self.sh.cp(
            source,
            destination,
            smartcp_threshold=smartcp_threshold,
            intent=intent,
            smartcp=True,
        )

    def _backend_rm(self, *args):
        return self.sh.rm(*args)

    def _backend_mv(self, source, destination):
        return self.sh.mv(source, destination)

    def _std_remove(self, *args):
        """Remove (possibly) multi GRIB files."""
        rc = True
        for pname in args:
            for objpath in self.sh.glob(pname):
                if self.is_xgrib(objpath):
                    with self.sh.mute_stderr():
                        idx = self._std_grib_index_get(objpath)
                        target_dirs = set()
                        for a_mpart in idx:
                            target_dirs.add(self.sh.path.dirname(a_mpart))
                            rc = rc and self._backend_rm(a_mpart)
                        for a_dir in target_dirs:
                            # Only if the directory is empty
                            if not self.sh.listdir(a_dir):
                                rc = rc and self._backend_rm(a_dir)
                        rc = rc and self._backend_rm(objpath)
                else:
                    rc = rc and self._backend_rm(objpath)
        return rc

    grib_rm = grib_remove = _std_remove

    def _std_copy(
        self,
        source,
        destination,
        smartcp_threshold=0,
        intent="in",
        pack=False,
        silent=False,
    ):
        """Extended copy for (possibly) multi GRIB file."""
        # Might be multipart
        if self.is_xgrib(source):
            rc = True
            if isinstance(destination, str) and not pack:
                with self.sh.mute_stderr():
                    idx = self._std_grib_index_get(source)
                    destdir = self.sh.path.abspath(
                        self.sh.path.expanduser(destination) + ".d"
                    )
                    rc = rc and self.sh.mkdir(destdir)
                    target_idx = list()
                    for i, a_mpart in enumerate(idx):
                        target_idx.append(
                            self.sh.path.join(
                                destdir, "GRIB_mpart{:06d}".format(i)
                            )
                        )
                        rc = rc and self._backend_cp(
                            a_mpart,
                            target_idx[-1],
                            smartcp_threshold=smartcp_threshold,
                            intent=intent,
                        )
                        rc = rc and self._std_grib_index_write(
                            destination, target_idx
                        )
                    if intent == "in":
                        self.sh.chmod(destination, 0o444)
            else:
                rc = rc and self.xgrib_pack(source, destination)
        else:
            # Usual file or file descriptor
            rc = self._backend_cp(
                source,
                destination,
                smartcp_threshold=smartcp_threshold,
                intent=intent,
            )
        return rc

    grib_cp = grib_copy = _std_copy

    def _std_move(self, source, destination):
        """Extended mv for (possibly) multi GRIB file."""
        # Might be multipart
        if self.is_xgrib(source):
            intent = "inout" if self.sh.access(source, self.sh.W_OK) else "in"
            rc = self._std_copy(source, destination, intent=intent)
            rc = rc and self._std_remove(source)
        else:
            rc = self._backend_mv(source, destination)
        return rc

    grib_mv = grib_move = _std_move

    def _pack_stream(self, source, stdout=True):
        cmd = [
            "cat",
        ]
        cmd.extend(self._std_grib_index_get(source))
        return self.sh.popen(cmd, stdout=stdout, bufsize=8192)

    def _packed_size(self, source):
        total = 0
        for filepath in self._std_grib_index_get(source):
            size = self.sh.size(filepath)
            if size == -1:
                return None
            total += size
        return total

    def xgrib_pack(self, source, destination, intent="in"):
        """Manually pack a multi GRIB."""
        if isinstance(destination, str):
            tmpfile = self.sh.safe_fileaddsuffix(destination)
            with open(tmpfile, "wb") as fd:
                p = self._pack_stream(source, stdout=fd)
            self.sh.pclose(p)
            if intent == "in":
                self.sh.chmod(tmpfile, 0o444)
            return self.sh.move(tmpfile, destination)
        else:
            p = self._pack_stream(source, stdout=destination)
            self.sh.pclose(p)
            return True

    def _std_forcepack(self, source, destination=None):
        """Returned a path to a packed data."""
        if self.is_xgrib(source):
            destination = (
                destination
                if destination
                else self.sh.safe_fileaddsuffix(source)
            )
            if not self.sh.path.exists(destination):
                if self.xgrib_pack(source, destination):
                    return destination
                else:
                    raise OSError("XGrib packing failed")
            else:
                return destination
        else:
            return source

    grib_forcepack = _std_forcepack

    def _std_ftput(
        self,
        source,
        destination,
        hostname=None,
        logname=None,
        port=DEFAULT_FTP_PORT,
        cpipeline=None,
        sync=False,
    ):
        """On the fly packing and ftp."""
        if self.is_xgrib(source):
            if cpipeline is not None:
                raise OSError("It's not allowed to compress xgrib files.")
            hostname = self.sh.fix_fthostname(hostname)
            ftp = self.sh.ftp(hostname, logname, port=port)
            if ftp:
                packed_size = self._packed_size(source)
                p = self._pack_stream(source)
                rc = ftp.put(
                    p.stdout, destination, size=packed_size, exact=True
                )
                self.sh.pclose(p)
                ftp.close()
            else:
                rc = False
            return rc
        else:
            return self.sh.ftput(
                source,
                destination,
                hostname=hostname,
                logname=logname,
                port=port,
                cpipeline=cpipeline,
                sync=sync,
            )

    def _std_rawftput(
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
        if self.is_xgrib(source):
            if cpipeline is not None:
                raise OSError("It's not allowed to compress xgrib files.")
            if self.sh.ftraw and self.rawftshell is not None:
                # Copy the GRIB pieces individually
                pieces = self.xgrib_index_get(source)
                newsources = [
                    str(self.sh.copy2ftspool(piece)) for piece in pieces
                ]
                request = newsources[0] + ".request"
                with open(request, "w") as request_fh:
                    request_fh.writelines("\n".join(newsources))
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
                return self._std_ftput(
                    source,
                    destination,
                    hostname=hostname,
                    logname=logname,
                    port=port,
                    sync=sync,
                )
        else:
            return self.sh.rawftput(
                source,
                destination,
                hostname=hostname,
                logname=logname,
                port=port,
                cpipeline=cpipeline,
                sync=sync,
            )

    grib_ftput = _std_ftput
    grib_rawftput = _std_rawftput

    def _std_scpput(
        self, source, destination, hostname, logname=None, cpipeline=None
    ):
        """On the fly packing and scp."""
        if self.is_xgrib(source):
            if cpipeline is not None:
                raise OSError("It's not allowed to compress xgrib files.")
            logname = self.sh.fix_ftuser(
                hostname, logname, fatal=False, defaults_to_user=False
            )
            ssh = self.sh.ssh(hostname, logname)
            permissions = ssh.get_permissions(source)
            # remove the .d companion directory (scp_stream removes the destination)
            # go on on failure : the .d lingers on, but the grib will be self-contained
            ssh.remove(destination + ".d")
            p = self._pack_stream(source)
            rc = ssh.scpput_stream(
                p.stdout, destination, permissions=permissions
            )
            self.sh.pclose(p)
            return rc
        else:
            return self.sh.scpput(
                source,
                destination,
                hostname,
                logname=logname,
                cpipeline=cpipeline,
            )

    grib_scpput = _std_scpput

    @addons.require_external_addon("ecfs")
    def grib_ecfsput(self, source, target, cpipeline=None, options=None):
        """Put a grib resource using ECfs.

        :param source: source file
        :param target: target file
        :param cpipeline: compression pipeline used, if provided
        :param options: list of options to be used
        :return: return code and additional attributes used
        """
        if self.is_xgrib(source):
            if cpipeline is not None:
                raise OSError("It's not allowed to compress xgrib files.")
            psource = self.sh.safe_fileaddsuffix(source)
            try:
                rc = self.xgrib_pack(source=source, destination=psource)
                dict_args = dict()
                if rc:
                    rc, dict_args = self.sh.ecfsput(
                        source=psource, target=target, options=options
                    )
            finally:
                self.sh.rm(psource)
            return rc, dict_args
        else:
            return self.sh.ecfsput(
                source=source,
                target=target,
                options=options,
                cpipeline=cpipeline,
            )

    @addons.require_external_addon("ectrans")
    def grib_ectransput(
        self,
        source,
        target,
        gateway=None,
        remote=None,
        cpipeline=None,
        sync=False,
    ):
        """Put a grib resource using ECtrans.

        :param source: source file
        :param target: target file
        :param gateway: gateway used by ECtrans
        :param remote: remote used by ECtrans
        :param cpipeline: compression pipeline used, if provided
        :param bool sync: If False, allow asynchronous transfers
        :return: return code and additional attributes used
        """
        if self.is_xgrib(source):
            if cpipeline is not None:
                raise OSError("It's not allowed to compress xgrib files.")
            psource = self.sh.safe_fileaddsuffix(source)
            try:
                rc = self.xgrib_pack(source=source, destination=psource)
                dict_args = dict()
                if rc:
                    rc, dict_args = self.sh.raw_ectransput(
                        source=psource,
                        target=target,
                        gateway=gateway,
                        remote=remote,
                        sync=sync,
                    )
            finally:
                self.sh.rm(psource)
            return rc, dict_args
        else:
            return self.sh.ectransput(
                source=source,
                target=target,
                gateway=gateway,
                remote=remote,
                cpipeline=cpipeline,
                sync=sync,
            )


@algo_component_deco_mixin_autodoc
class EcGribDecoMixin(AlgoComponentDecoMixin):
    """Extend Algo Components with EcCodes/GribApi features."

    This mixin class is intended to be used with AlgoComponent classes. It will
    automatically set up the ecCodes/GribApi environment variable given the
    path to the EcCodes/GribApi library (which is found by performing a ``ldd``
    on the AlgoComponent's target binary).
    """

    _ECGRIB_SETUP_COMPAT = True
    _ECGRIB_SETUP_FATAL = True

    def _ecgrib_libs_detext(self, rh):
        """Run ldd and tries to find ecCodes or grib_api libraries locations."""
        eccodes_lib = None
        gribapi_lib = None
        if rh is not None:
            if not isinstance(rh, (list, tuple)):
                rh = [
                    rh,
                ]
            for a_rh in rh:
                libs = self.system.ldd(a_rh.container.localpath())
                a_eccodes_lib = None
                a_gribapi_lib = None
                for lib, path in libs.items():
                    if re.match(
                        r"^libeccodes(?:-[.0-9]+)?\.so(?:\.[.0-9]+)?$", lib
                    ):
                        a_eccodes_lib = path
                    if re.match(
                        r"^libgrib_api(?:-[.0-9]+)?\.so(?:\.[.0-9]+)?$", lib
                    ):
                        a_gribapi_lib = path
                if a_eccodes_lib:
                    self.algoassert(
                        eccodes_lib is None or (eccodes_lib == a_eccodes_lib),
                        "ecCodes library inconsistency (rh: {!s})".format(
                            a_rh
                        ),
                    )
                    eccodes_lib = a_eccodes_lib
                if a_gribapi_lib:
                    self.algoassert(
                        gribapi_lib is None or (gribapi_lib == a_gribapi_lib),
                        "grib_api library inconsistency (rh: {!s})".format(
                            a_rh
                        ),
                    )
                    gribapi_lib = a_gribapi_lib
        return eccodes_lib, gribapi_lib

    def _ecgrib_additional_config(self, a_role, a_var):
        """Add axtra definitions/samples to the library path."""
        for gdef in self.context.sequence.effective_inputs(role=a_role):
            local_path = gdef.rh.container.localpath()
            new_path = (
                local_path
                if self.system.path.isdir(local_path)
                else self.system.path.dirname(local_path)
            )
            # NB: Grib-API doesn't understand relative paths...
            new_path = self.system.path.abspath(new_path)
            self.env.setgenericpath(a_var, new_path, pos=0)

    def _gribapi_envsetup(self, gribapi_lib):
        """Setup environment variables for grib_api."""
        defvar = "GRIB_DEFINITION_PATH"
        samplevar = "GRIB_SAMPLES_PATH"
        if gribapi_lib is not None:
            gribapi_root = self.system.path.dirname(gribapi_lib)
            gribapi_root = self.system.path.split(gribapi_root)[0]
            gribapi_share = self.system.path.join(
                gribapi_root, "share", "grib_api"
            )
            if defvar not in self.env:
                # This one is for compatibility with old versions of the gribapi !
                self.env.setgenericpath(
                    defvar,
                    self.system.path.join(
                        gribapi_root, "share", "definitions"
                    ),
                )
                # This should be the lastest one:
                self.env.setgenericpath(
                    defvar, self.system.path.join(gribapi_share, "definitions")
                )
            if samplevar not in self.env:
                # This one is for compatibility with old versions of the gribapi !
                self.env.setgenericpath(
                    samplevar,
                    self.system.path.join(
                        gribapi_root, "ifs_samples", "grib1"
                    ),
                )
                # This should be the lastest one:
                self.env.setgenericpath(
                    samplevar,
                    self.system.path.join(
                        gribapi_share, "ifs_samples", "grib1"
                    ),
                )
        else:
            # Use the default GRIB-API config if the ldd approach fails
            self.export("gribapi")
        return defvar, samplevar

    def gribapi_setup(self, rh, opts):
        """Setup the grib_api related stuff."""
        _, gribapi_lib = self._ecgrib_libs_detext(rh)
        defvar, samplevar = self._gribapi_envsetup(gribapi_lib)
        self._ecgrib_additional_config("AdditionalGribAPIDefinitions", defvar)
        self._ecgrib_additional_config("AdditionalGribAPISamples", samplevar)
        # Recap
        for a_var in (defvar, samplevar):
            logger.info(
                "After gribapi_setup %s = %s", a_var, self.env.getvar(a_var)
            )

    def _eccodes_envsetup(
        self,
        eccodes_lib,
        envvar="ECCODES_DEFINITIONS_PATH",
        tgt_path="definitions",
    ):
        """Export envirionment variables required by ECCODES

        Value is

        /path/to/eccodes-X.Y.Z/share/eccodes/<target_path>

        eccodes_lib: Absolute path to the eccodes so file
        envvar: Name of the environment variable to export
        tgt_path: Name of the eccodes install subdirectory to appear
          in the value
        """
        if envvar in self.env:
            return envvar
        if envvar.replace("ECCODES", "GRIB") in self.env:
            logger.warning(
                (
                    "%s is left unconfigured because the old grib_api's"
                    "variable is defined. ",
                    "Please remove that!",
                ),
                envvar,
            )
            return envvar.replace("ECCODES", "GRIB")
        eccodes_root = Path(eccodes_lib).parent.parent
        self.env.setgenericpath(
            envvar,
            str(eccodes_root / "share" / "eccodes" / tgt_path),
        )
        return envvar

    def eccodes_setup(self, rh, opts, compat=False, fatal=True):
        """Setup the grib_api related stuff.

        If **compat** is ``True`` and ecCodes is not found, the old grib_api
        will be set-up. Otherwise, it will just return (if **fatal** is ``False``)
        or raise an exception (if **fatal** is ``True``).
        """
        # Detect the library's path and setup appropriate variables
        eccodes_lib, gribapi_lib = self._ecgrib_libs_detext(rh)
        if eccodes_lib is not None:
            defvar = self._eccodes_envsetup(
                eccodes_lib,
                envvar="ECCODES_DEFINITIONS_PATH",
                tgt_path="definitions",
            )
            subdir = Path("ifs_samples") / (
                "grib1" if rh.resource.cycle < "cy49" else "grib1_mlgrib2"
            )
            samplevar = self._eccodes_envsetup(
                eccodes_lib,
                envvar="ECCODES_SAMPLES_PATH",
                tgt_path=subdir,
            )
        elif compat:
            defvar, samplevar = self._gribapi_envsetup(gribapi_lib)
        else:
            if fatal:
                raise RuntimeError(
                    "No suitable configuration found for ecCodes."
                )
            else:
                logger.error("ecCodes was not found !")
                return
        # Then, inspect the context to look for customised search paths
        self._ecgrib_additional_config(
            ("AdditionalGribAPIDefinitions", "AdditionalEcCodesDefinitions"),
            defvar,
        )
        self._ecgrib_additional_config(
            ("AdditionalGribAPISamples", "AdditionalEcCodesSamples"), samplevar
        )
        # Recap
        for a_var in (defvar, samplevar):
            logger.info(
                "After eccodes_setup (compat=%s) : %s = %s",
                str(compat),
                a_var,
                self.env.getvar(a_var),
            )

    def _ecgrib_mixin_setup(self, rh, opts):
        self.eccodes_setup(
            rh,
            opts,
            compat=self._ECGRIB_SETUP_COMPAT,
            fatal=self._ECGRIB_SETUP_FATAL,
        )

    _MIXIN_PREPARE_HOOKS = (_ecgrib_mixin_setup,)


class GRIBAPI_Tool(addons.Addon):
    """
    Interface to gribapi commands (designed as a shell Addon).
    """

    _footprint = dict(
        info="Default GRIBAPI system interface",
        attr=dict(
            kind=dict(
                values=["gribapi"],
            ),
        ),
    )

    def __init__(self, *args, **kw):
        """Addon initialisation."""
        super().__init__(*args, **kw)
        # Additionaly, check for the GRIB_API_ROOTDIR key in the config file
        if self.path is None and self.cfginfo is not None:
            addon_rootdir = get_from_config_w_default(
                section=self.cfginfo,
                key="grib_api_rootdir",
                default=None,
            )
            if addon_rootdir is not None:
                self.path = addon_rootdir

    def _spawn_wrap(self, cmd, **kw):
        """Internal method calling standard shell spawn."""
        cmd[0] = "bin" + self.sh.path.sep + cmd[0]
        return super()._spawn_wrap(cmd, **kw)

    def _actual_diff(self, grib1, grib2, skipkeys, **kw):
        """Run the actual GRIBAPI command."""
        cmd = ["grib_compare", "-r", "-b", ",".join(skipkeys), grib1, grib2]
        kw["fatal"] = False
        kw["output"] = False
        return self._spawn_wrap(cmd, **kw)

    def grib_diff(
        self, grib1, grib2, skipkeys=("generatingProcessIdentifier",), **kw
    ):
        """
        Difference between two GRIB files (using the GRIB-API)

        :param grib1: first file to compare
        :param grib2: second file to compare
        :param skipkeys: List of GRIB keys that will be ignored

        GRIB messages may not be in the same order in both files.

        If *grib1* or *grib2* are multipart files, they will be concatenated
        prior to the comparison.
        """

        # Are multipart GRIB suported ?
        xgrib_support = "grib" in self.sh.loaded_addons()
        grib1_ori = grib1
        grib2_ori = grib2
        if xgrib_support:
            if self.sh.is_xgrib(grib1):
                grib1 = self.sh.safe_fileaddsuffix(grib1_ori) + "_diffcat"
                self.sh.xgrib_pack(grib1_ori, grib1)
            if self.sh.is_xgrib(grib2):
                grib2 = self.sh.safe_fileaddsuffix(grib2_ori) + "_diffcat"
                self.sh.xgrib_pack(grib2_ori, grib2)

        rc = self._actual_diff(grib1, grib2, skipkeys, **kw)

        if xgrib_support and grib1 != grib1_ori:
            self.sh.grib_rm(grib1)
        if xgrib_support and grib2 != grib2_ori:
            self.sh.grib_rm(grib2)

        return rc
