"""
Stream/File compression tools.

The user interface for such tools is the :class:`CompressionPipeline`.
"""

from contextlib import contextmanager
import io
import functools
import operator

import footprints
from bronx.fancies import loggers
from vortex.util.iosponge import IoSponge


#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class CompressionPipeline:
    """Main interface to data compression algorithms."""

    def __init__(self, system, compression=""):
        """
        :param System system: The system object that will be used to carry out
            the task.
        :param str compression: The description of the compression tools that
            will be used in this compression pipeline.
            (e.g. 'gzip' will just compress/uncompress using the gzip software,
            'gzip|bzip2' will use the gzip software piped to the bzip2 software
            (which is useless), 'gzip&complevel=5' will use the gzip software
            with a compression factor of 5.)

        :note: See the subclasses of :class:`CompressionUnit` for a description
            of available compression tools (and their options).
        """
        self._units = list()
        self._sh = system
        self.description_string = compression
        for c in [c for c in compression.split("|") if c]:
            c_raw = c.split("&")
            ckind = c_raw.pop(0)
            cargs = dict([arg.split("=", 1) for arg in c_raw])
            self.add_compression_unit(ckind, **cargs)

    def add_compression_unit(self, unit, **kwargs):
        """Add a new compression tool to the compression pipeline.

        :param str unit: The kind of the compression tool (see  :class:`CompressionUnit`
            subclases
        :param kwargs: Options that will be used during the compression tool
            initialisation
        """
        c_unit = footprints.proxy.compression_unit(kind=unit, **kwargs)
        if c_unit is None:
            raise ValueError(
                "The {:s} compression unit could not be found.".format(unit)
            )
        self._units.append(c_unit)

    @property
    def units(self):
        """The list of compression tools forming the compression pipeline."""
        return self._units

    @property
    def _rawftp_shell(self):
        """The name of the corresponding rawftp specialshell (if relevant)."""
        if len(self.units) == 1:
            return self.units[0].rawftp_shell(self._sh)
        else:
            return None

    @property
    def suffix(self):
        """The suffix usualy associated with this compression pipeline."""
        s = ".".join([s.suffix for s in self.units])
        return "." + s if s else ""

    @property
    def compression_factor(self):
        """The minimal compression factor expected with such a compression pipeline."""
        return functools.reduce(
            operator.mul, [s.cfactor for s in self.units], 1.0
        )

    @staticmethod
    def _inputstream_size(stream):
        """Find out the size of a seekable input stream."""
        estimated_size = 0
        try:
            stream.seek(0, io.SEEK_END)
            estimated_size = stream.tell()
            stream.seek(0)
        except AttributeError:
            logger.warning("Could not rewind <source:%s>", str(stream))
        except OSError:
            logger.debug("Seek trouble <source:%s>", str(stream))
        return estimated_size

    @contextmanager
    def _openstream(self, local, mode="rb"):
        """If *local* is not an opened file, open it..."""
        if isinstance(local, str):
            localfh = open(local, mode)
            yield localfh
            localfh.close()
        elif isinstance(local, io.IOBase):
            yield local
        else:
            raise ValueError("Unknown type for {!s}".format(local))

    def _genericstream_close(self, processes):
        """Close a list of Popen objects (and look for the returncode)."""
        for i, p in enumerate(processes):
            if not self._sh.pclose(p):
                logger.error(
                    "Abnormal return code for one of the processes (#%d)", i
                )

    @contextmanager
    def compress2stream(self, local, iosponge=False):
        """Compress *local* into a pipe or an :class:`IoSponge` object.

        *local* can be an opened file-like object or a filename.

        This method creates a context manager. Example::

            source='myfile'
            cp = CompressionPipeline(systemobj, 'gzip')
            ftp = systemobj.ftp('hendrix.meteo.fr')
            with cp.compress2stream(source) as csource:
                ftp.put(csource, 'remote_compressedfile')

        When leaving the context, the gzip process that compresses the data will
        be properly closed
        """
        with self._openstream(local) as stream:
            estimated_size = (
                self._inputstream_size(stream) * self.compression_factor
            )
            processes = list()
            lstream = stream
            for unit in self.units:
                p = unit.compress(self._sh, lstream)
                lstream = p.stdout
                processes.append(p)
            if iosponge:
                yield IoSponge(lstream, guessed_size=estimated_size)
            else:
                yield lstream
            self._genericstream_close(processes)

    def _xcopyfileobj(self, in_fh, out_fh):
        try:
            self._sh.copyfileobj(in_fh, out_fh)
        except OSError:
            return False
        else:
            return True

    def compress2file(self, local, destination):
        """Compress *local* into a file (named *destination*)

        *local* can be an opened file-like object or a filename.
        *destination* is a filename.
        """
        with open(destination, "wb") as fhout:
            with self.compress2stream(local) as fhcompressed:
                return self._xcopyfileobj(fhcompressed, fhout)

    def compress2rawftp(self, local):
        """
        Return the name of the rawftp's specialshell that can be used to
        compress the *local* data. It might return None.
        """
        return self._rawftp_shell

    @contextmanager
    def stream2uncompress(self, destination):
        """Uncompress piped data to *destination*.

        *destination* can be an opened file-like object or a filename.

        This method creates a context manager. Example::

            destination='mydownloadedfile'
            cp = CompressionPipeline(systemobj, 'gzip')
            ftp = systemobj.ftp('hendrix.meteo.fr')
            with cp.stream2uncompress(destination) as cdestination:
                ftp.get('remote_compressedfile', cdestination)

        When leaving the context, the gunzip process that uncompresses the data
        will be properly closed.
        """
        with self._openstream(destination, "wb") as dstream:
            processes = list()
            instream = True
            nunits = len(self.units)
            for i, unit in enumerate(reversed(self.units)):
                outstream = dstream if i == nunits - 1 else True
                p = unit.uncompress(self._sh, instream, outstream)
                instream = p.stdout
                processes.append(p)
            yield processes[0].stdin
            self._genericstream_close(processes)

    def file2uncompress(self, local, destination):
        """Uncompress *local* into *destination*.

        *local* is a filename.
        *destination* can be an opened file-like object or a filename.
        """
        with self.stream2uncompress(destination) as fhuncompressed:
            with open(local, "rb") as fhcompressed:
                return self._xcopyfileobj(fhcompressed, fhuncompressed)


class CompressionUnit(footprints.FootprintBase):
    """Defines compress/uncompress methods for a given compression tool."""

    _abstract = True
    _collector = ("compression_unit",)
    _footprint = dict(
        info="Abstract Compression Unit",
        attr=dict(
            kind=dict(
                info="The name of the compression tool.",
            ),
            suffix=dict(
                info="The usual file extension for this compression tool.",
                optional=True,
            ),
            cfactor=dict(
                info="The usual compression factor for this compression tool.",
                type=float,
                default=1.0,
                optional=True,
            ),
        ),
    )

    def rawftp_shell(self, sh):
        """The rawftp's speciall shell that may carry out a comparable compression."""
        return None

    def _run_in_pipe(self, sh, cmd, stream, outstream=True):
        """Run *cmd* with the piped input *stream*."""
        p = sh.popen(cmd, stdin=stream, stdout=outstream, bufsize=8192)
        return p

    def compress(self, sh, stream):
        """Compress the input *stream*. Returns a Popen object."""
        raise NotImplementedError()

    def uncompress(self, sh, stream, outstream=True):
        """Uncompress the input *stream*. Returns a Popen object."""
        raise NotImplementedError()


class GzipCompressionUnit(CompressionUnit):
    _footprint = dict(
        info="Compress/Uncompress a stream using gzip",
        attr=dict(
            kind=dict(values=["gzip", "gz"]),
            suffix=dict(
                default="gz",
            ),
            complevel=dict(
                info="The gzip algorithm compression level (see 'man gzip')",
                type=int,
                values=range(1, 10),
                default=6,
                optional=True,
            ),
            cfactor=dict(default=0.9),
        ),
    )

    def compress(self, sh, stream):
        """Compress the input *stream*. Returns a Popen object."""
        return self._run_in_pipe(
            sh, ["gzip", "--stdout", "-{!s}".format(self.complevel)], stream
        )

    def uncompress(self, sh, stream, outstream=True):
        """Uncompress the input *stream*. Returns a Popen object."""
        return self._run_in_pipe(sh, ["gunzip", "--stdout"], stream, outstream)


class Bzip2CompressionUnit(CompressionUnit):
    _footprint = dict(
        info="Compress/Uncompress a stream using bzip2",
        attr=dict(
            kind=dict(values=["bzip2", "bz2"]),
            suffix=dict(
                default="bz2",
            ),
            complevel=dict(
                info="The bzip2 algorithm compression level (see 'man bzip2')",
                type=int,
                values=range(1, 10),
                default=9,
                optional=True,
            ),
            cfactor=dict(
                default=0.85,
            ),
        ),
    )

    def compress(self, sh, stream):
        """Compress the input *stream*. Returns a Popen object."""
        return self._run_in_pipe(
            sh, ["bzip2", "--stdout", "-{!s}".format(self.complevel)], stream
        )

    def uncompress(self, sh, stream, outstream=True):
        """Uncompress the input *stream*. Returns a Popen object."""
        return self._run_in_pipe(
            sh, ["bunzip2", "--stdout"], stream, outstream
        )
