"""
Abstract and generic classes for any "Container". "Container" objects
describe where to store the data localy.

Roughly there are :class:`Virtual` and concrete containers. With :class:`Virtual`
containers such as :class:`InCore` or :class:`MayFly`, the data may lie in
memory. On the oposite, with concrete containers, data lie on disk within the
working directory.

The :class:`SingleFile` container is by far the most commonly used.
"""

import contextlib
import os
import re
import tempfile
import uuid

from bronx.fancies import loggers
from bronx.syntax.decorators import secure_getattr
import footprints

from vortex import sessions
from vortex.syntax.stdattrs import a_actualfmt

#: Automatic export
__all__ = ["Container"]

logger = loggers.getLogger(__name__)

CONTAINER_INCORELIMIT = 1048576 * 8
CONTAINER_MAXREADSIZE = 1048576 * 200


class DataSizeTooBig(IOError):
    """Exception raised when totasize is over the container MaxReadSize limit."""

    pass


class Container(footprints.FootprintBase):
    """Abstract class for any Container."""

    _abstract = True
    _collector = ("container",)
    _footprint = dict(
        info="Abstract Container",
        attr=dict(
            actualfmt=a_actualfmt,
            maxreadsize=dict(
                info="The maximum amount of data that can be read (in bytes).",
                type=int,
                optional=True,
                default=CONTAINER_MAXREADSIZE,
                doc_visibility=footprints.doc.visibility.GURU,
            ),
            mode=dict(
                info="The file mode used to open the container.",
                optional=True,
                values=[
                    "a",
                    "a+",
                    "ab",
                    "a+b",
                    "ab+",
                    "r",
                    "r+",
                    "rb",
                    "rb+",
                    "r+b",
                    "w",
                    "w+",
                    "wb",
                    "w+b",
                    "wb+",
                ],
                remap={"a+b": "ab+", "r+b": "rb+", "w+b": "wb+"},
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
            encoding=dict(
                info="When opened in text mode, the encoding that will be used.",
                optional=True,
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
        ),
    )

    _DEFAULTMODE = "rb"

    @property
    def realkind(self):
        return "container"

    def __init__(self, *args, **kw):
        """Preset to None or False hidden attributes ``iod``, ``iomode`` and ``filled``."""
        logger.debug("Container %s init", self.__class__)
        super().__init__(*args, **kw)
        self._iod = None
        self._iomode = None
        self._ioencoding = None
        self._acmode = None
        self._acencoding = None
        self._pref_byte = None
        self._pref_encoding = None
        self._pref_write = None
        self._filled = False

    def __getstate__(self):
        d = super().__getstate__()
        # Start from a clean slate regarding IO descriptors
        d["_iod"] = None
        d["_acmode"] = None
        d["_acencoding"] = None
        return d

    @secure_getattr
    def __getattr__(self, key):
        """Gateway to undefined method or attributes if present in internal io descriptor."""
        # It avoids to call self.iodesc() when footprint_export is called...
        if key.startswith("footprint_export") or key in (
            "export_dict",
            "as_dump",
            "as_dict",
            "_iod",
        ):
            raise AttributeError("Could not get an io descriptor")
        # Normal processing
        iod = self.iodesc()
        if iod:
            return getattr(iod, key)
        else:
            raise AttributeError("Could not get an io descriptor")

    @contextlib.contextmanager
    def iod_context(self):
        """Ensure that any opened IO descriptor is closed after use."""
        if self.is_virtual():
            # With virtual container, this is not a good idea since closing
            # the io descriptor might result in data losses
            yield
        else:
            try:
                yield
            finally:
                self.close()

    def localpath(self):
        """Abstract method to be overwritten."""
        raise NotImplementedError

    def iodesc(self, mode=None, encoding=None):
        """Returns the file object descriptor."""
        mode1, encoding1 = self._get_mode(mode, encoding)
        if not (
            self._iod
            and not self._iod.closed
            and mode1 == self._acmode
            and encoding1 == self._acencoding
        ):
            if self._iod and not self._iod.closed:
                self.close()
                mode1, encoding1 = self._get_mode(mode, encoding)
            self._iod = self._new_iodesc(mode1, encoding1)
            self._acmode = mode1
            self._acencoding = encoding1
        return self._iod

    def _new_iodesc(self, mode, encoding):
        """Returns a new file object descriptor."""
        raise NotImplementedError

    def iotarget(self):
        """Abstract method to be overwritten."""
        raise NotImplementedError

    @property
    def filled(self):
        """
        Returns a boolean value according to the fact that
        the container has been correctly filled with data.
        """
        return self._filled

    def updfill(self, getrc=None):
        """Change current filled status according to return code of the get command."""
        if getrc is not None and getrc:
            self._filled = True

    def clear(self, fmt=None):
        """Delete the container content."""
        self.close()
        self._filled = False
        return True

    @property
    def totalsize(self):
        """Returns the complete size of the container."""
        iod = self.iodesc()
        pos = iod.tell()
        iod.seek(0, 2)
        ts = iod.tell()
        iod.seek(pos)
        return ts

    def rewind(self):
        """Performs the rewind of the current io descriptor of the container."""
        self.seek(0)

    def endoc(self):
        """Go to the end of the container."""
        self.seek(0, 2)

    def read(self, n=-1, mode=None, encoding=None):
        """Read in one jump all the data as long as the data is not too big."""
        iod = self.iodesc(mode, encoding)
        if self.totalsize < self.maxreadsize or (0 < n < self.maxreadsize):
            return iod.read(n)
        else:
            raise DataSizeTooBig(
                "Input is more than {:d} bytes.".format(self.maxreadsize)
            )

    def dataread(self, mode=None, encoding=None):
        """
        Reads the next data line or unit of the container.
        Returns a tuple with this line and a boolean
        to tell whether the end of container is reached.
        """
        with self.preferred_decoding(byte=False):
            iod = self.iodesc(mode, encoding)
            line = iod.readline()
            return (line, bool(iod.tell() == self.totalsize))

    def head(self, nlines, mode=None, encoding=None):
        """Read in one *nlines* of the data as long as the data is not too big."""
        with self.preferred_decoding(byte=False):
            iod = self.iodesc(mode, encoding)
            self.rewind()
            nread = 0
            lines = list()
            lsize = 0
            while nread < nlines:
                lines.append(iod.readline())
                lsize += len(lines[-1])
                if lsize > self.maxreadsize:
                    raise DataSizeTooBig(
                        "Input is more than {:d} bytes.".format(
                            self.maxreadsize
                        )
                    )
                nread += 1
            return lines

    def readlines(self, mode=None, encoding=None):
        """Read in one jump all the data as a sequence of lines as long as the data is not too big."""
        with self.preferred_decoding(byte=False):
            iod = self.iodesc(mode, encoding)
            if self.totalsize < self.maxreadsize:
                self.rewind()
                return iod.readlines()
            else:
                raise DataSizeTooBig(
                    "Input is more than {:d} bytes.".format(self.maxreadsize)
                )

    def __iter__(self):
        with self.preferred_decoding(byte=False):
            iod = self.iodesc()
            iod.seek(0)
            yield from iod

    def close(self):
        """Close the logical io descriptor."""
        if self._iod:
            self._iod.close()
            self._iod = None
            self._iomode = None
            self._ioencoding = None
            self._acmode = None
            self._acencoding = None

    @property
    def defaultmode(self):
        return self._iomode or self.mode

    @property
    def defaultencoding(self):
        return self._ioencoding or self.encoding

    @property
    def actualmode(self):
        return self._acmode or self._get_mode(None, None)[0]

    @property
    def actualencoding(self):
        return self._acencoding or self._get_mode(None, None)[1]

    @staticmethod
    def _set_amode(actualmode):
        """Upgrade the ``actualmode`` to a append-compatible mode."""
        am = re.sub("[rw]", "a", actualmode)
        am = am.replace("+", "")
        return am + "+"

    @staticmethod
    def _set_wmode(actualmode):
        """Upgrade the ``actualmode`` to a write-compatible mode."""
        wm = re.sub("r", "w", actualmode)
        wm = wm.replace("+", "")
        return wm + "+"

    @staticmethod
    def _set_bmode(actualmode):
        """Upgrade the ``actualmode`` to byte mode."""
        if "b" not in actualmode:
            wm = re.sub(r"([arw])", r"\1b", actualmode)
            return wm
        else:
            return actualmode

    @staticmethod
    def _set_tmode(actualmode):
        """Upgrade the ``actualmode`` to a text-mode."""
        wm = actualmode.replace("b", "")
        return wm

    @contextlib.contextmanager
    def preferred_decoding(self, byte=True, encoding=None):
        assert byte in [True, False]
        prev_byte = self._pref_byte
        self._pref_byte = byte
        if encoding is not None:
            prev_enc = self._pref_encoding
            self._pref_encoding = encoding
        yield
        self._pref_byte = prev_byte
        if encoding is not None:
            self._pref_encoding = prev_enc

    @contextlib.contextmanager
    def preferred_write(self, append=False):
        assert append in [True, False]
        prev_write = self._pref_write
        self._pref_write = append
        yield
        self._pref_write = prev_write

    def _get_mode(self, mode, encoding):
        # Find out a mode
        if mode:
            tmode = mode
            self._iomode = mode
        else:
            tmode = self.defaultmode
            if tmode is None:
                tmode = self._acmode or self._DEFAULTMODE
                if self._pref_write is True:
                    tmode = self._set_amode(tmode)
                elif self._pref_write is False:
                    tmode = self._set_wmode(tmode)
                if self._pref_byte is True:
                    tmode = self._set_bmode(tmode)
                elif self._pref_byte is False:
                    tmode = self._set_tmode(tmode)
        # Find out the encoding
        if encoding:
            tencoding = encoding
            self._ioencoding = encoding
        else:
            tencoding = self.defaultencoding
            if tencoding is None:
                tencoding = self._acencoding
                if self._pref_encoding is not None:
                    tencoding = self._pref_encoding
        return tmode, tencoding

    def write(self, data, mode=None, encoding=None):
        """Write the data content in container."""
        with self.preferred_write():
            iod = self.iodesc(mode, encoding)
            iod.write(data)
            self._filled = True

    def append(self, data, mode=None, encoding=None):
        """Write the data content at the end of the container."""
        with self.preferred_write(append=True):
            iod = self.iodesc(mode, encoding)
            self.endoc()
            iod.write(data)
            self._filled = True

    def cat(self, mode=None, encoding=None):
        """Perform a trivial cat of the container."""
        if self.filled:
            with self.preferred_decoding(byte=False):
                iod = self.iodesc(mode, encoding)
                pos = iod.tell()
                iod.seek(0)
                for xchunk in iod:
                    print(xchunk.rstrip("\n"))
                iod.seek(pos)

    def is_virtual(self):
        """Check if the current container has some physical reality or not."""
        return False

    def __del__(self):
        self.close()


class Virtual(Container):
    _abstract = True
    _footprint = dict(
        info="Abstract Virtual Container",
        attr=dict(
            prefix=dict(
                info="Prefix used if a temporary file needs to be written.",
                optional=True,
                default="vortex.tmp.",
                doc_visibility=footprints.doc.visibility.GURU,
            )
        ),
    )

    _DEFAULTMODE = "wb+"

    def is_virtual(self):
        """
        Check if the current container has some physical reality or not.
        In that case, the answer is ``True``!
        """
        return True

    def exists(self):
        """In case of a virtual container, always true."""
        return self.filled

    def iotarget(self):
        """Virtual container's io target is an io descriptor."""
        return self.iodesc()


class InCore(Virtual):
    _footprint = dict(
        info="Incore container (data are kept in memory as long as possible).",
        attr=dict(
            incore=dict(
                info="Activate the incore container.",
                type=bool,
                values=[
                    True,
                ],
                alias=("mem", "memory"),
                doc_zorder=90,
            ),
            incorelimit=dict(
                info="If this limit (in bytes) is exceeded, data are flushed to file.",
                type=int,
                optional=True,
                default=CONTAINER_INCORELIMIT,
                alias=("memlimit", "spooledlimit", "maxsize"),
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
        ),
        fastkeys={"incore"},
    )

    def __init__(self, *args, **kw):
        logger.debug("InCore container init %s", self.__class__)
        kw.setdefault("incore", True)
        super().__init__(*args, **kw)
        self._tempo = False

    def actualpath(self):
        """Returns path information, if any, of the spooled object."""
        if self._iod:
            if self._tempo or self._iod._rolled:
                actualfile = self._iod.name
            else:
                actualfile = "MemoryResident"
        else:
            actualfile = "NotSpooled"
        return actualfile

    def _str_more(self):
        """Additional information to print representation."""
        return 'incorelimit={:d} tmpfile="{:s}"'.format(
            self.incorelimit, self.actualpath()
        )

    def _new_iodesc(self, mode, encoding):
        """Returns an active (opened) spooled file descriptor in binary read mode by default."""
        self.close()
        if self._tempo:
            iod = tempfile.NamedTemporaryFile(
                mode=mode,
                prefix=self.prefix,
                dir=os.getcwd(),
                delete=True,
                encoding=encoding,
            )
        else:
            iod = tempfile.SpooledTemporaryFile(
                mode=mode,
                prefix=self.prefix,
                dir=os.getcwd(),
                max_size=self.incorelimit,
                encoding=encoding,
            )
        return iod

    @property
    def temporized(self):
        return self._tempo

    def temporize(self):
        """Migrate any memory data to a :class:`NamedTemporaryFile`."""
        if not self.temporized:
            iomem = self.iodesc()
            self.rewind()
            self._tempo = True
            self._iod = tempfile.NamedTemporaryFile(
                mode=self._acmode,
                prefix=self.prefix,
                dir=os.getcwd(),
                delete=True,
                encoding=self._acencoding,
            )
            for data in iomem:
                self._iod.write(data)
            self._iod.flush()
            iomem.close()

    def unroll(self):
        """Replace rolled data to memory (when possible)."""
        if self.temporized and self.totalsize < self.incorelimit:
            iotmp = self.iodesc()
            self.rewind()
            self._tempo = False
            self._iod = tempfile.SpooledTemporaryFile(
                mode=self._acmode,
                prefix=self.prefix,
                dir=os.getcwd(),
                max_size=self.incorelimit,
                encoding=self._acencoding,
            )
            for data in iotmp:
                self._iod.write(data)
            iotmp.close()

    def localpath(self):
        """
        Roll the current memory file in a :class:`NamedTemporaryFile`
        and returns associated file name.
        """
        self.temporize()
        iod = self.iodesc()
        try:
            return iod.name
        except Exception:
            logger.warning(
                "Could not get local temporary rolled file pathname %s", self
            )
            raise


class MayFly(Virtual):
    _footprint = dict(
        info="MayFly container (a temporary file is created only when needed).",
        attr=dict(
            mayfly=dict(
                info="Activate the mayfly container.",
                type=bool,
                values=[
                    True,
                ],
                alias=("tempo",),
                doc_zorder=90,
            ),
            delete=dict(
                info="Delete the file when the container object is destroyed.",
                type=bool,
                optional=True,
                default=True,
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
        ),
        fastkeys={"mayfly"},
    )

    def __init__(self, *args, **kw):
        logger.debug("MayFly container init %s", self.__class__)
        kw.setdefault("mayfly", True)
        super().__init__(*args, **kw)

    def actualpath(self):
        """Returns path information, if any, of the spooled object."""
        if self._iod:
            return self._iod.name
        else:
            return "NotDefined"

    def _str_more(self):
        """Additional information to internal representation."""

        return 'delete={!s} tmpfile="{:s}"'.format(
            self.delete, self.actualpath()
        )

    def _new_iodesc(self, mode, encoding):
        """Returns an active (opened) temporary file descriptor in binary read mode by default."""
        self.close()
        return tempfile.NamedTemporaryFile(
            mode=mode,
            prefix=self.prefix,
            dir=os.getcwd(),
            delete=self.delete,
            encoding=encoding,
        )

    def localpath(self):
        """
        Returns the actual name of the temporary file object
        which is created if not yet defined.
        """
        iod = self.iodesc()
        try:
            return iod.name
        except Exception:
            logger.warning(
                "Could not get local temporary file pathname %s", self
            )
            raise


class _SingleFileStyle(Container):
    """
    Template for any file container. Data is stored as a file object.
    """

    _abstract = (True,)
    _footprint = dict(
        info="File container",
        attr=dict(
            cwdtied=dict(
                info="If *filename* is a relative path, replace it by its absolute path.",
                type=bool,
                optional=True,
                default=False,
                doc_visibility=footprints.doc.visibility.ADVANCED,
            ),
        ),
    )

    def __init__(self, *args, **kw):
        """Business as usual... but define actualpath according to ``cwdtied`` attribute."""
        logger.debug("_SingleFileStyle container init %s", self.__class__)
        super().__init__(*args, **kw)
        if self.cwdtied:
            self._actualpath = os.path.realpath(self.filename)
        else:
            self._actualpath = self.filename

    def actualpath(self):
        """Returns the actual pathname of the file object."""
        return self._actualpath

    @property
    def abspath(self):
        """Shortcut to realpath of the actualpath."""
        return os.path.realpath(self.actualpath())

    @property
    def absdir(self):
        """Shortcut to dirname of the abspath."""
        return os.path.dirname(self.abspath)

    @property
    def dirname(self):
        """Shortcut to dirname of the actualpath."""
        return os.path.dirname(self.actualpath())

    @property
    def basename(self):
        """Shortcut to basename of the abspath."""
        return os.path.basename(self.abspath)

    def _str_more(self):
        """Additional information to print representation."""
        return "path='{:s}'".format(self.actualpath())

    def localpath(self):
        """Returns the actual name of the file object."""
        return self.actualpath()

    def _new_iodesc(self, mode, encoding):
        """Returns an active (opened) file descriptor in binary read mode by default."""
        self.close()
        currentpath = (
            self._actualpath
            if self.cwdtied
            else os.path.realpath(self.filename)
        )
        return open(currentpath, mode, encoding=encoding)

    def iotarget(self):
        """File container's io target is a plain pathname."""
        return self.localpath()

    def clear(self, *kargs, **kw):
        """Delete the container content (in this case the actual file)."""
        rst = super().clear(*kargs, **kw)
        # Physically delete the file if it exists
        if self.exists():
            sh = kw.pop("system", sessions.system())
            rst = rst and sh.remove(self.localpath(), fmt=self.actualfmt)
        return rst

    def exists(self):
        """Check the existence of the actual file."""
        return os.path.exists(self.localpath())


class SingleFile(_SingleFileStyle):
    """
    Default file container. Data is stored as a file object.
    """

    _footprint = dict(
        attr=dict(
            filename=dict(
                info="Path to the file where data are stored.",
                alias=("filepath", "local"),
                doc_zorder=50,
            ),
        ),
        fastkeys={"filename"},
    )


class UnnamedSingleFile(_SingleFileStyle):
    """Unnamed file container. Data is stored as a file object.

    The filename is chosen arbitrarily when the object is created.
    """

    _footprint = dict(
        info="File container (a temporary filename is chosen at runtime)",
        attr=dict(
            shouldfly=dict(
                info="Activate the UnnamedSingleFile container",
                type=bool,
                values=[
                    True,
                ],
                doc_zorder=90,
            ),
            cwdtied=dict(
                default=True,
                doc_visibility=footprints.doc.visibility.GURU,
            ),
        ),
        fastkeys={"shouldfly"},
    )

    def __init__(self, *args, **kw):
        logger.debug("UnnamedSingleFile container init %s", self.__class__)
        self._auto_filename = None
        kw.setdefault("shouldfly", True)
        super().__init__(*args, **kw)

    @property
    def filename(self):
        if self._auto_filename is None:
            fh, fpath = tempfile.mkstemp(prefix="shouldfly-", dir=os.getcwd())
            os.close(fh)  # mkstemp opens the file but we do not really care...
            self._auto_filename = os.path.basename(fpath)
        return self._auto_filename

    def __getstate__(self):
        st = super().__getstate__()
        st["_auto_filename"] = None
        return st

    def exists(self, empty=False):
        """Check the existence of the actual file."""
        return os.path.exists(self.localpath()) and (
            empty or os.path.getsize(self.localpath())
        )


class Uuid4UnamedSingleFile(_SingleFileStyle):
    """Unamed file container created in a temporary diectory."""

    _footprint = dict(
        info="File container (a temporary filename is chosen at runtime)",
        attr=dict(
            uuid4fly=dict(
                info="Activate the Uuid4UnnamedSingleFile container",
                type=bool,
                values=[
                    True,
                ],
                doc_zorder=90,
            ),
            uuid4flydir=dict(
                info="The subdirectory where to create the unamed file",
                optional=True,
                default=".",
                doc_zorder=90,
            ),
        ),
        fastkeys={"uuid4fly"},
    )

    def __init__(self, *args, **kw):
        logger.debug(
            "UuidBasedUnamedSingleFile container init %s", self.__class__
        )
        self._auto_filename = None
        kw.setdefault("uuid4fly", True)
        super().__init__(*args, **kw)

    @property
    def filename(self):
        if self._auto_filename is None:
            self._auto_filename = os.path.join(
                self.uuid4flydir, uuid.uuid4().hex
            )
        return self._auto_filename

    def __getstate__(self):
        st = super().__getstate__()
        st["_auto_filename"] = None
        return st
