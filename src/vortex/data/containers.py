#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = [ 'Container' ]

import re, sys, io
import tempfile
from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface


class Container(BFootprint):

    def __init__(self, *args, **kw):
        logger.debug('Container %s init', self.__class__)
        self._filled = False
        self._totalsize = None
        super(Container, self).__init__(*args, **kw)


    @property
    def realkind(self):
        return 'container'

    @property
    def filled(self):
        """
        Returns a boolean value according to the fact that
        the container has been correctly filled with data.
        """
        return self._filled

    def updfill(self, getrc=None):
        """Change current filled status according to return code of the get command."""
        if getrc != None and getrc:
            self._filled = True

    def localpath(self):
        """Abstract method to be overwritten."""
        pass

    @property
    def totalsize(self):
        """Returns the complete size of the container."""
        if self._totalsize == None:
            self.rewind()
        return self._totalsize

    def rewind(self):
        """Performs the rewind of the current io descriptor of the container."""
        iod = self.iodesc()
        iod.seek(0, 2)
        self._totalsize = iod.tell()
        iod.seek(0)

    def dataread(self):
        """
        Reads the next data line of the container. Returns a tuple with this line
        and a boolean to tell whether the end of container is reached.
        """
        iod = self.iodesc()
        line = iod.readline()
        return ( line, bool(iod.tell() == self._totalsize) )

    def readall(self):
        """Read in one jump all the data as long as the data is not too big."""
        iod = self.iodesc()
        if self.totalsize < 4194304:
            return iod.read()

    def readlines(self):
        """Read in one jump all the data as a sequens of lines as long as the data is not too big."""
        iod = self.iodesc()
        if self.totalsize < 4194304:
            return iod.readlines()

    def iodesc(self):
        """Returns the file object descriptor."""
        raise NotImplementedError()

    def close(self):
        """Close the logical io descriptor."""
        pass

    def write(self, data):
        """Write the data in container."""
        pass


class Virtual(Container):

    _abstract = True
    _footprint = dict(
        info = 'Abstract Virtual Container',
        attr = dict(
            prefix = dict(
                optional = True,
                default = 'vortex.tmp.'
            )
        )
    )

    def iodesc(self):
        """Returns the file object descriptor."""
        return self._tmpfile

    def close(self):
        """Close the logical io descriptor."""
        iod = self.iodesc()
        iod.close()

    def cat(self):
        """Perform a trivial cat of the virtual container."""
        if self._filled:
            pos = self._tmpfile.tell()
            self._tmpfile.seek(0)
            for xchunk in self._tmpfile:
                print xchunk.rstrip('\n')
            self._tmpfile.seek(pos)


class InCore(Virtual):

    _footprint = dict(
        info = 'Incore container',
        attr = dict(
            incore = dict(
                type = bool,
                alias = ('mem', 'memory')
            ),
            maxsize = dict(
                type = int,
                optional = True,
                default = 65536,
                alias = ('memlimit',)
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Virtual container init %s', self)
        super(InCore, self).__init__(*args, incore = True, **kw)
        self._tmpfile = None

    @property
    def realkind(self):
        return 'incore'

    def localpath(self):
        """
        Returns the actual name of the spooled temporary file object
        which is created if not yet defined.
        """
        if not self._tmpfile:
            self._tmpfile = tempfile.SpooledTemporaryFile(prefix=self.prefix, max_size=self.maxsize)
        return self._tmpfile


class MayFly(Virtual):

    _footprint = dict(
        info = 'Virtual container',
        attr = dict(
            mayfly = dict(
                type = bool,
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
        logger.debug('Virtual container init %s', self)
        super(MayFly, self).__init__(*args, mayfly=True, **kw)
        self._tmpfile = None

    @property
    def realkind(self):
        return 'mayfly'

    def localpath(self):
        """
        Returns the actual name of the temporary file object
        which is created if not yet defined.
        """
        if not self._tmpfile:
            self._tmpfile = tempfile.NamedTemporaryFile(mode='w+b', prefix=self.prefix, delete=self.delete)
        return self._tmpfile

    def write(self, data):
        """Rewind and dump the data content in container."""
        self.rewind()
        self._tmpfile.write(data)


class File(Container):
    """
    Default file container. Data is stored as a file object.
    """
    _footprint = dict(
        info = 'File container',
        attr = dict(
            file = dict(
                alias = ('filepath', 'filename', 'filedir', 'local')
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('File container init %s', self)
        super(File, self).__init__(*args, **kw)
        self._iod = None

    @property
    def realkind(self):
        return 'file'

    def localpath(self):
        """Returns the actual name of the file object."""
        return self.file

    def iodesc(self):
        """Returns an active (opened) file descriptor in binary read mode by default."""
        if not self._iod:
            self._iod = io.open(self.localpath(), 'rb')
        return self._iod

    def close(self):
        """Close the logical io descriptor."""
        if self._iod:
            self._iod.close()
            self._iod = None

    def write(self, data):
        """Rewind and dump the data content in container."""
        self.close()
        with io.open(self.localpath(), 'wb') as fd:
            fd.write(data)
            fd.close()


class ContainersCatalog(ClassesCollector):

    def __init__(self, **kw):
        logger.debug('Containers catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.containers'),
            classes = [ Container ],
            itementry = 'container'
        )
        cat.update(kw)
        super(ContainersCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'containers'

cataloginterface(sys.modules.get(__name__), ContainersCatalog)

