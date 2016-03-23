#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = ['Container']

import re, io, os
import tempfile

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.syntax.stdattrs import a_actualfmt

CONTAINER_INCORELIMIT = 1048576 * 8
CONTAINER_MAXREADSIZE = 1048576 * 64


class DataSizeTooBig(IOError):
    """Exception raised when totasize is over the container MaxReadSize limit."""
    pass


class Container(footprints.FootprintBase):

    _abstract  = True
    _collector = ('container',)
    _footprint = dict(
        info = 'Abstract Virtual Container',
        attr = dict(
            actualfmt = a_actualfmt,
            maxreadsize = dict(
                type     = int,
                optional = True,
                default  = CONTAINER_MAXREADSIZE
            ),
            mode = dict(
                optional = True,
                default  = 'rb',
                values   = ['a', 'ab', 'a+b', 'ab+', 'r', 'rb', 'rb+', 'r+b', 'w', 'wb', 'w+b', 'wb+'],
                remap    = {'a+b': 'ab+', 'r+b': 'rb+', 'w+b': 'wb+'}
            )
        )
    )

    @property
    def realkind(self):
        return 'container'

    def __init__(self, *args, **kw):
        """Preset to None or False hidden attributes ``iod``, ``iomode`` and ``filled``."""
        logger.debug('Container %s init', self.__class__)
        super(Container, self).__init__(*args, **kw)
        self._iod    = None
        self._iomode = None
        self._filled = False

    def __getattr__(self, key):
        """Gateway to undefined method or attributes if present in internal io descriptor."""
        # It avoids to call self.iodesc() when footprint_export is called...
        if key.startswith('footprint_export') or key == 'export_dict':
            raise AttributeError('Could not get an io descriptor')
        # Normal processing
        iod = self.iodesc()
        if iod:
            return getattr(iod, key)
        else:
            raise AttributeError('Could not get an io descriptor')

    def localpath(self):
        """Abstract method to be overwritten."""
        raise NotImplementedError

    def iodesc(self, mode=None):
        """Returns the file object descriptor."""
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
        if iod:
            pos = iod.tell()
            iod.seek(0, 2)
            ts = iod.tell()
            iod.seek(pos)
            return ts
        else:
            return None

    def rewind(self, mode=None):
        """Performs the rewind of the current io descriptor of the container."""
        self.seek(0)

    def endoc(self):
        """Go to the end of the container."""
        self.seek(0, 2)

    def dataread(self):
        """
        Reads the next data line or unit of the container.
        Returns a tuple with this line and a boolean
        to tell whether the end of container is reached.
        """
        iod = self.iodesc()
        line = iod.readline()
        return ( line, bool(iod.tell() == self.totalsize) )

    def read(self, n=-1):
        """Read in one jump all the data as long as the data is not too big."""
        iod = self.iodesc()
        if iod:
            if self.totalsize < self.maxreadsize or (0 < n < self.maxreadsize):
                return iod.read(n)
            else:
                raise DataSizeTooBig('Input is more than {0:d} bytes.'.format(self.maxreadsize))
        else:
            return None

    def readlines(self):
        """Read in one jump all the data as a sequence of lines as long as the data is not too big."""
        iod = self.iodesc()
        if iod:
            if self.totalsize < self.maxreadsize:
                self.rewind()
                return iod.readlines()
            else:
                raise DataSizeTooBig('Input is more than {0:d} bytes.'.format(self.maxreadsize))
        else:
            return None

    def __iter__(self):
        iod = self.iodesc()
        iod.seek(0)
        for x in iod:
            yield x

    def close(self):
        """Close the logical io descriptor."""
        if self._iod:
            self._iod.close()
            self._iod = None
            self._iomode = None

    @property
    def actualmode(self):
        return self._iomode or self.mode

    def set_amode(self, actualmode):
        """Upgrade the ``actualmode`` to a append-compatible mode."""
        am = re.sub('[rw]', 'a', actualmode)
        am = am.replace('+', '')
        return am + '+'

    def set_wmode(self, actualmode):
        """Upgrade the ``actualmode`` to a write-compatible mode."""
        wm = re.sub('r', 'w', actualmode)
        wm = wm.replace('+', '')
        return wm + '+'

    def write(self, data, mode=None):
        """Write the data content in container."""
        if mode is None:
            mode = self.set_wmode(self.mode)
        iod = self.iodesc(mode)
        iod.write(data)
        self._filled = True

    def append(self, data):
        """Write the data content at the end of the container."""
        iod = self.iodesc(self.set_amode(self.mode))
        self.endoc()
        iod.write(data)
        self._filled = True

    def cat(self):
        """Perform a trivial cat of the container."""
        if self._filled:
            iod = self.iodesc()
            pos = iod.tell()
            iod.seek(0)
            for xchunk in iod:
                print xchunk.rstrip('\n')
            iod.seek(pos)

    def is_virtual(self):
        """Check if the current container has some physical reality or not."""
        return False

    def __del__(self):
        self.close()


class Virtual(Container):

    _abstract = True
    _footprint = dict(
        info = 'Abstract Virtual Container',
        attr = dict(
            mode = dict(
                default = 'wb+'
            ),
            prefix = dict(
                optional = True,
                default = 'vortex.tmp.'
            )
        )
    )

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
        info = 'Incore container',
        attr = dict(
            incore = dict(
                type = bool,
                values = [ True ],
                alias = ('mem', 'memory')
            ),
            incorelimit = dict(
                type = int,
                optional = True,
                default = CONTAINER_INCORELIMIT,
                alias = ('memlimit', 'spooledlimit', 'maxsize')
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('InCore container init %s', self.__class__)
        super(InCore, self).__init__(*args, incore=True, **kw)
        self._tempo = False

    def actualpath(self):
        """Returns path information, if any, of the spooled object."""
        if self._iod:
            if self._tempo or self._iod._rolled:
                actualfile = self._iod.name
            else:
                actualfile = 'MemoryResident'
        else:
            actualfile = 'NotSpooled'
        return actualfile

    def _str_more(self):
        """Additional information to print representation."""
        return 'incorelimit={0:d} tmpfile="{1:s}"'.format(self.incorelimit, self.actualpath())

    def iodesc(self, mode=None):
        """Returns an active (opened) spooled file descriptor in binary read mode by default."""
        if mode is None:
            mode = self.actualmode
        if not self._iod or self._iod.closed or mode != self.actualmode:
            self.close()
            self._iomode = mode
            if self._tempo:
                self._iod = tempfile.NamedTemporaryFile(
                    mode    = self._iomode,
                    prefix  = self.prefix,
                    dir     = os.getcwd(),
                    delete  = True
                )
            else:
                self._iod = tempfile.SpooledTemporaryFile(
                    mode     = self._iomode,
                    prefix   = self.prefix,
                    dir      = os.getcwd(),
                    max_size = self.incorelimit
                )

        return self._iod

    @property
    def rolled(self):
        iod = self.iodesc()
        return iod._rolled

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
                mode    = self._iomode,
                prefix  = self.prefix,
                dir     = os.getcwd(),
                delete  = True
            )
            for data in iomem:
                self._iod.write(data)
            iomem.close()

    def unroll(self):
        """Replace rolled data to memory (when possible)."""
        if ( self.temporized or self.rolled ) and self.totalsize < self.incorelimit:
            iotmp = self.iodesc()
            self.rewind()
            self._tempo = False
            self._iod = tempfile.SpooledTemporaryFile(
                mode     = self._iomode,
                prefix   = self.prefix,
                dir      = os.getcwd(),
                max_size = self.incorelimit
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
            logger.warning('Could not get local temporary rolled file pathname %s', self)
            raise


class MayFly(Virtual):

    _footprint = dict(
        info = 'Virtual container',
        attr = dict(
            mayfly = dict(
                type   = bool,
                values = [ True ],
                alias  = ('tempo',)
            ),
            delete = dict(
                type     = bool,
                optional = True,
                default  = True,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('MayFly container init %s', self.__class__)
        super(MayFly, self).__init__(*args, mayfly=True, **kw)

    def actualpath(self):
        """Returns path information, if any, of the spooled object."""
        if self._iod:
            return self._iod.name
        else:
            return 'NotDefined'

    def _str_more(self):
        """Additional information to internal representation."""

        return 'delete={0:s} tmpfile="{1:s}"'.format(str(self.delete), self.actualpath())

    def iodesc(self, mode=None):
        """Returns an active (opened) temporary file descriptor in binary read mode by default."""
        if mode is None:
            mode = self.actualmode
        if not self._iod or self._iod.closed or mode != self.actualmode:
            self.close()
            self._iomode = mode
            self._iod = tempfile.NamedTemporaryFile(
                mode    = self._iomode,
                prefix  = self.prefix,
                dir     = os.getcwd(),
                delete  = self.delete
            )
        return self._iod

    def localpath(self):
        """
        Returns the actual name of the temporary file object
        which is created if not yet defined.
        """
        iod = self.iodesc()
        try:
            return iod.name
        except Exception:
            logger.warning('Could not get local temporary file pathname %s', self)
            raise


class SingleFile(Container):
    """
    Default file container. Data is stored as a file object.
    """
    _footprint = dict(
        info = 'File container',
        attr = dict(
            filename = dict(
                alias    = ('filepath', 'local'),
            ),
            cwdtied = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Business as usual... but define actualpath according to ``cwdtied`` attribute."""
        logger.debug('SingleFile container init %s', self.__class__)
        super(SingleFile, self).__init__(*args, **kw)
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
        return 'path=\'{0:s}\''.format(self.actualpath())

    def localpath(self):
        """Returns the actual name of the file object."""
        return self.actualpath()

    def iodesc(self, mode=None):
        """Returns an active (opened) file descriptor in binary read mode by default."""
        if mode is None:
            mode = self.actualmode
        if not self._iod or self._iod.closed or mode != self.actualmode:
            self.close()
            currentpath = self._actualpath if self.cwdtied else os.path.realpath(self.filename)
            self._iomode = mode
            self._iod = io.open(currentpath, self._iomode)
        return self._iod

    def iotarget(self):
        """File container's io target is a plain pathname."""
        return self.localpath()

    def clear(self, *kargs, **kw):
        """Delete the container content (in this case the actual file)."""
        rst = super(SingleFile, self).clear(*kargs, **kw)
        # Physically delete the file if it exists
        if self.exists():
            sh = kw.pop('system', sessions.system())
            rst = rst and sh.remove(self.localpath(), fmt=self.actualfmt)
        return rst

    def exists(self):
        """Check the existence of the actual file."""
        return os.path.exists(self.localpath())
