"""
Various utility classes and functions to be used with the taylorism package.
"""

import multiprocessing
from multiprocessing import sharedctypes


class SharedNumpyArray:
    """
    Wrapper to multiprocessing.Array, for it to be shared in memory among
    Workers, while being handled as a numpy.ndarray or numpy.ma.masked_array.
    """

    def __init__(self, array):
        """

        :param array: initialize the SharedNumpyArray with this one, supposed
            to be either a multiprocessing.Array, a numpy.ndarray or a
            numpy.ma.masked_array.

        * constructing a SharedNumpyArray from a multiprocessing.Array will
          not duplicate data but make the SharedArray be a pointer to the
          initial array;
        * constructing from a numpy array will duplicate data, and so the
          initial array will no longer be consistent with this one.

        The process-safetiness of the shared array is ensured
        (cf. multiprocessing.Array) through the use of
        SharedNumpyArray.acquire() and .release(),
        but this is of the responsability of the user implementing the
        Worker's inner task.
        """
        import numpy
        if isinstance(array, sharedctypes.SynchronizedArray):
            self._mp_array = array
            self._np_array = numpy.frombuffer(array.get_obj())
        elif (isinstance(array, numpy.ndarray) or
              isinstance(array, numpy.ma.masked_array)):
            if array.dtype in (float, numpy.float64):
                typecode = 'd'
            elif array.dtype in (int, numpy.int64):
                typecode = 'l'
            elif array.dtype in (numpy.int32,):
                typecode = 'i'
            elif array.dtype in (numpy.float32,):
                typecode = 'f'
            else:
                raise NotImplementedError('array.dtype==' + str(array.dtype))
            self._mp_array = multiprocessing.Array(typecode, array.size)
            np_array = numpy.frombuffer(self._mp_array.get_obj(), dtype=array.dtype)
            self._np_array = np_array.reshape(array.shape)
            self._np_array[...] = array[...]
            if isinstance(array, numpy.ma.masked_array):
                self._np_array = numpy.ma.masked_where(array.mask, self._np_array, copy=False)

    # redefinition of implicit methods: hash because of Footprints, eq to be
    # redefined together with hash in Python3 and transitivity of numpy arrays
    # methods from the inner numpy array layer
    def __hash__(self):
        return hash(self._mp_array)

    def __eq__(self, other):
        if isinstance(other, SharedNumpyArray):
            return self._np_array == other._np_array
        else:
            return False

    def __getattribute__(self, attr):
        if attr in ('_np_array', '_mp_array'):
            return super().__getattribute__(attr)
        elif attr in ('get_lock', 'acquire', 'release'):
            return self._mp_array.__getattribute__(attr)
        else:
            if hasattr(self._np_array, attr):
                return self._np_array.__getattribute__(attr)
            else:
                raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if attr in ('_np_array', '_mp_array'):
            super().__setattr__(attr, value)
        else:
            self._np_array.__setattr__(attr, value)

    def __getitem__(self, *args):
        return self._np_array.__getitem__(*args)

    def __setitem__(self, *args):
        self._np_array.__setitem__(*args)

    def __setslice(self, *args):
        self._np_array.__setslice__(*args)

    def __getslice__(self, *args):
        return self._np_array.__getslice__(*args)
