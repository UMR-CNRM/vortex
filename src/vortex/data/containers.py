#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = [ 'Container' ]

import logging, re, sys, io
import tempfile

from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface


class Container(BFootprint):

    def __init__(self, *args, **kw):
        logging.debug('Container %s init', self.__class__)
        self._filled = False
        self._totalsize = None
        super(Container, self).__init__(*args, **kw)

    def localpath(self):
        """Abstract method to be overwritten."""
        pass

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
        
    
    @property
    def filled(self):
        """
        Returns a boolean value according to the fact that
        the container has been correctly filled with data.
        """
        return self._filled

    def updfill(self, getrc=None):
        if getrc != None and getrc:
            self._filled = True
        
    @classmethod
    def realkind(cls):
        return 'container'

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
        """Returns the file object descripteur."""
        return self._tmpfile

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
        logging.debug('Virtual container init %s', self)
        super(InCore, self).__init__(*args, incore = True, **kw)
        self._tmpfile = None

    def localpath(self):
        """
        Returns the actual name of the spooled temporary file object
        which is created if not yet defined.
        """
        if not self._tmpfile:
            self._tmpfile = tempfile.SpooledTemporaryFile(prefix=self.prefix, max_size=self.maxsize)
        return self._tmpfile


    @classmethod
    def realkind(cls):
        return 'incore'


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
        logging.debug('Virtual container init %s', self)
        super(MayFly, self).__init__(*args, mayfly = True, **kw)
        self._tmpfile = None

    def localpath(self):
        """
        Returns the actual name of the temporary file object
        which is created if not yet defined.
        """
        if not self._tmpfile:
            self._tmpfile = tempfile.NamedTemporaryFile(prefix=self.prefix, delete=self.delete)
        return self._tmpfile.name


    @classmethod
    def realkind(cls):
        return 'mayfly'


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
        logging.debug('File container init %s', self)
        super(File, self).__init__(*args, **kw)
        self._iod = None

    @classmethod
    def realkind(cls):
        return 'file'

    def localpath(self):
        """Returns the actual name of the file object."""
        return self.file

    def iodesc(self):
        """Returns an active (opened) file descripteur in binary read mode by default."""
        if not self._iod:
            self._iod = io.open(self.localpath(), 'rb')
        return self._iod


class ContainersCatalog(ClassesCollector):

    def __init__(self, **kw):
        logging.debug('Containers catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.containers'),
            classes = [ Container ],
            itementry = Container.realkind()
        )
        cat.update(kw)
        super(ContainersCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'containers'

cataloginterface(sys.modules.get(__name__), ContainersCatalog)

