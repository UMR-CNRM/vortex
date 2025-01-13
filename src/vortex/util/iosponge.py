"""
Provide a File-Like object that reads in the first N bytes in order to count
them precisely.
"""

import io

#: No automatic export
__all__ = []

IOSPONGE_DEFAULT_SIZECHECK = 33 * 1024 * 1024  # 33Mb


class IoSponge(io.BufferedIOBase):
    """Buffer the first bytes in order to compute an accurate size for the
    underlying stream.

    This class just acts as a buffer. It looks like a file object and should
    be used as such.

    If the size of the underlying stream is <= *size_check* bytes : the **size**
    property will return an exact estimate of the file-like object size. Passed
    that limit the maximum of *size_check* and *guessed_size* is returned.
    """

    def __init__(
        self, rawio, size_check=IOSPONGE_DEFAULT_SIZECHECK, guessed_size=0
    ):
        """
        :param file rawio: Any kind of file-like object
        :param int size_check: The first size_check bytes will be buffered in
            order to be properly accounted for.
        :param int gressed_size: An estimate of the file-like object size (in
            bytes)
        """
        self._rawio = rawio
        self._size_check = size_check
        self._guessed_size = int(guessed_size)
        self._first_bytes = self._rawio.read(size_check)
        self._seek = 0

    @property
    def size(self):
        """The (exact or estimated)  size of the underlying file-like object."""
        if len(self._first_bytes) < self._size_check:
            return len(self._first_bytes)
        else:
            return max(len(self._first_bytes), self._guessed_size)

    def tell(self):
        """The amount of bytes read in this strem."""
        return self._seek

    def _generic_read(self, size, raw_read_cb):
        ret = b""
        if self._seek < len(self._first_bytes):
            if size is None:
                ret = self._first_bytes[self._seek :]
            else:
                ret = self._first_bytes[
                    self._seek : min(self._size_check, self._seek + size)
                ]
        if size is None:
            ret += raw_read_cb(None)
        elif len(ret) < size:
            ret += raw_read_cb(size - len(ret))
        self._seek += len(ret)
        return ret

    def read(self, size=None):
        """Read *size* bytes from the file."""
        return self._generic_read(size, self._rawio.read)

    def read1(self, size=None):
        """Read *size* bytes from the file (at once)."""
        return self._generic_read(size, self._rawio.read1)

    def readable(self):
        """Is this file-like object readable ?"""
        return True
