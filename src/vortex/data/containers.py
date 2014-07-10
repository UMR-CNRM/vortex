#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = [ 'Container' ]

import re, io, os
import tempfile

import footprints

from vortex.autolog import logdefault as logger
from vortex.syntax.stdattrs import a_actualfmt

CONTAINER_INCORELIMIT = 1048576 * 8
CONTAINER_MAXREADSIZE = 1048576 * 64


class DataSizeTooBig(Exception):
    pass


class Container(footprints.FootprintBase):

    _abstract  = True
    _collector = ('container',)
    _footprint = dict(
        info = 'Abstract Virtual Container',
        attr = dict(
            actualfmt = a_actualfmt,
            maxreadsize = dict(
                type = int,
                optional = True,
                default = CONTAINER_MAXREADSIZE
            ),
            mode = dict(
                optional = True,
                default = 'rb',
                values = ['a', 'ab', 'a+b', 'ab+', 'r', 'rb', 'rb+', 'r+b', 'w', 'wb', 'w+b', 'wb+'],
                remap = {'a+b': 'ab+', 'r+b': 'rb+', 'w+b': 'wb+'}
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Container %s init', self.__class__)
        self._iod = None
        self._iomode = None
        self._filled = False
        super(Container, self).__init__(*args, **kw)

    def __getattr__(self, key):
        """Gateway to undefined method or attributes if present in internal io descriptor."""
        iod = self.iodesc()
        if iod:
            return getattr(iod, key)
        else:
            raise AttributeError('Could not get an io descriptor')

    @property
    def realkind(self):
        return 'container'

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

    @property
    def totalsize(self):
        """Returns the complete size of the container."""
        iod = self.iodesc()
        if iod:
            pos = self._iod.tell()
            self._iod.seek(0, 2)
            ts = iod.tell()
            self._iod.seek(pos)
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
        Reads the next data line of the container. Returns a tuple with this line
        and a boolean to tell whether the end of container is reached.
        """
        iod = self.iodesc()
        line = iod.readline()
        return ( line, bool(iod.tell() == self.totalsize) )

    def read(self, n=-1):
        """Read in one jump all the data as long as the data is not too big."""
        iod = self.iodesc()
        if iod:
            if self.totalsize < self.maxreadsize or (n > 0 and n < self.maxreadsize):
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

    def amode(self, actualmode):
        """Upgrade the ``actualmode`` to a write-compatible mode."""
        am = re.sub('[rw]', 'a', actualmode)
        am = am.replace('+', '')
        return am + '+'

    def wmode(self, actualmode):
        """Upgrade the ``actualmode`` to a write-compatible mode."""
        wm = re.sub('r', 'w', actualmode)
        wm = wm.replace('+', '')
        return wm + '+'

    def write(self, data, mode=None):
        """Write the data content in container."""
        if mode is None:
            mode = self.wmode(self.mode)
        iod = self.iodesc(mode)
        iod.write(data)
        self._filled = True

    def append(self, data):
        """Write the data content at the end of the container."""
        iod = self.iodesc(self.amode(self.mode))
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
        logger.debug('InCore container init %s', self)
        self._tempo = False
        super(InCore, self).__init__(*args, incore=True, **kw)

    @property
    def realkind(self):
        return 'incore'

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
                type = bool,
                values = [ True ],
                alias = ('tempo', 'virtual')
            ),
            delete = dict(
                type = bool,
                optional = True,
                default = True,
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('MayFly container init %s', self)
        super(MayFly, self).__init__(*args, mayfly=True, **kw)

    @property
    def realkind(self):
        return 'mayfly'

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


class File(Container):
    """
    Default file container. Data is stored as a file object.
    """
    _footprint = dict(
        info = 'File container',
        attr = dict(
            file = dict(
                alias = ('filepath', 'filename', 'filedir', 'local')
            ),
            cwdtied = dict(
                type = bool,
                optional = True,
                default = False,
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('File container init %s', self)
        super(File, self).__init__(*args, **kw)
        if self.cwdtied:
            self._actualpath = os.path.realpath(self.file)
        else:
            self._actualpath = self.file

    @property
    def realkind(self):
        return 'file'

    def actualpath(self):
        """Returns the actual pathname of the file object."""
        return self._actualpath

    def _str_more(self):
        """Additional information to print representation."""
        return 'path=\'{0:s}\''.format(self._actualpath)

    def localpath(self):
        """Returns the actual name of the file object."""
        return self.actualpath()

    def iodesc(self, mode=None):
        """Returns an active (opened) file descriptor in binary read mode by default."""
        if mode is None:
            mode = self.actualmode
        if not self._iod or self._iod.closed or mode != self.actualmode:
            self.close()
            if not self.cwdtied:
                self._actualpath = os.path.realpath(self.file)
            self._iomode = mode
            self._iod = io.open(self._actualpath, self._iomode)
        return self._iod

    def iotarget(self):
        """File container's io target is a plain pathname."""
        return self.localpath()
