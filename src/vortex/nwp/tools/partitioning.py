"""
Compute simple domain partitionings.

The partitioning classes can be used on their own. Alternatively, the
:meth:`setup_partitioning_in_namelist` method can be used to interact with
namelist's Content objects.
"""

import functools
import math
import re

from bronx.syntax import iterators as b_iter
from bronx.fancies import loggers


logger = loggers.getLogger(__name__)

__all__ = [
    "PartitioningError",
    "Rectangular2DPartitioner",
    "setup_partitioning_in_namelist",
]


class PartitioningError(ValueError):
    """Any error raised during domain partitionings."""

    pass


class AbstratctPartitioner:
    """The base class for any concrete partitioning class.

    Provides the mechanism to filter the partitioning methods and
    cache the results.
    """

    _REGISTERED_METHODS = ()

    def __init__(self, p_method_specification):
        """
        :param p_method_specification: The partitioning method definition
        """
        # Process the partitioning method specification string
        p_method_parts = p_method_specification.lower().split("_")
        self.p_method_name = None
        self.p_method_args = ()
        for a_method, a_method_n_args in self._REGISTERED_METHODS:
            if p_method_parts[0] == a_method:
                self.p_method_name = p_method_parts[0]
                if len(p_method_parts) - 1 != a_method_n_args:
                    raise ValueError(
                        "Erroneous number of interger args "
                        + "for the {:s} p_method ({:d} required)".format(
                            a_method, a_method_n_args
                        )
                    )
                self.p_method_args = tuple(
                    [int(s) for s in p_method_parts[1:]]
                )
        # Unknown method -> crash
        if self.p_method_name is None:
            raise PartitioningError(
                "Unknown partitioning method ({:s}).".format(
                    p_method_specification
                )
            )
        # The actual class' method that will be used to compute a and b
        self.p_method = functools.partial(
            getattr(self, "_" + self.p_method_name), *self.p_method_args
        )
        # Implement a caching mechanism
        self._p_cache = dict()

    def __call__(self, ntasks):
        """Return the appropriate partitioning given **ntasks**."""
        if ntasks not in self._p_cache:
            self._p_cache[ntasks] = self.p_method(ntasks)
        return self._p_cache[ntasks]


class Rectangular2DPartitioner(AbstratctPartitioner):
    """Find an adequat 2D simple partitioning given the number of tasks.

    Here is a description of the problem :

    * Let ``D`` be a 2D array/field;
    * Let ``N`` be the number of partitions you want to create;
    * What are ``x`` and ``x`` that satisfies ``x * y = N`` (so that the
      ``D`` array can be partitionned in ``x`` (reps. ``y``) chunks
      in its first (resp. second) dimension ?

    For exemple, with N=16, an array can be split in 4 chunks in each
    dimension. It can also be partitioned in 2 chunks in the first
    dimension and 8 in the second...  There is no unique solution.
    Consequently, the user needs to provide a partitioning method.

    Example::

        # Look for a partitioning around a given fixed value
        # e.g with xcloseto_16, the x value will be close to 16
        >>> Rectangular2DPartitioner('xcloseto_16')(128)
        (16, 8)
        >>> Rectangular2DPartitioner('xcloseto_16')(990)
        (15, 66)
        >>> Rectangular2DPartitioner('xcloseto_16')(500)
        (20, 25)

        # e.g with ycloseto_16, the y value will be close to 16
        >>> Rectangular2DPartitioner('ycloseto_16')(128)
        (8, 16)
        >>> Rectangular2DPartitioner('ycloseto_16')(990)
        (66, 15)
        >>> Rectangular2DPartitioner('ycloseto_16')(500)
        (25, 20)

        # Squar-est partition of the domain: y and y as close
        # as possible
        >>> Rectangular2DPartitioner('square')(16)
        (4, 4)
        >>> Rectangular2DPartitioner('square')(12)
        (3, 4)
        >>> Rectangular2DPartitioner('square')(7)
        (1, 7)

        # Try to find x and y so that a given aspect ratio is preserved
        # e.g with aspect_16_9, x / y should roughly be equal to 16 / 9
        >>> Rectangular2DPartitioner('aspect_2_1')(32)
        (8, 4)
        >>> Rectangular2DPartitioner('aspect_2_1')(27)
        (9, 3)
        >>> Rectangular2DPartitioner('aspect_16_9')(28)  # roughly 16/9e like a TV...
        (7, 4)

    """

    _REGISTERED_METHODS = (
        ("xcloseto", 1),
        ("ycloseto", 1),
        ("square", 0),
        ("aspect", 2),
    )

    @staticmethod
    def _test_and_return(ntasks, guesses):
        found = 1
        for i_guess in guesses:
            if ntasks % i_guess == 0:
                found = i_guess
                break
        return found, ntasks // found

    def _xcloseto(self, close_to_what, ntasks):
        """Find ``x`` as the closest possible value to **close_to_what**."""
        guesses = b_iter.interleave(
            range(close_to_what, 0, -1),
            range(close_to_what + 1, min(close_to_what * 2, ntasks)),
        )
        return self._test_and_return(ntasks, guesses)

    def _ycloseto(self, close_to_what, ntasks):
        """Find ``y`` as the closest possible value to **close_to_what**."""
        y_value, x_value = self._xcloseto(close_to_what, ntasks)
        return x_value, y_value

    def _square(self, ntasks):
        """Find ``x`` and ``y`` so that they are close to the square root of ``N``.

        With this method, ``x`` is always the smalest value.
        """
        guesses = range(int(math.sqrt(ntasks)), 0, -1)
        return self._test_and_return(ntasks, guesses)

    def _aspect(self, x_spec, y_spec, ntasks):
        """Find ``x`` and ``y`` so that ``x / y =~ x_spec / y_spec``."""
        aspect_ratio = x_spec / y_spec
        return self._xcloseto(int(math.sqrt(ntasks * aspect_ratio)), ntasks)


_PARTITIONERS_CACHE = dict()


def setup_partitioning_in_namelist(
    namcontents, effective_tasks, effective_threads, namlocal=None
):
    """Look in a namelist Content object and replace the macros related to partitioning.

    :param nwp.data.namelists.NamelistContent namcontents: The namelist's Content
                                                              object to work with
    :param int effective_tasks: The number of tasks that will be used when computing
                                the partitioning
    :param int effective_threads: The number of threads that will be used when computing
                                  the partitioning
    :param str namlocal: The namelist's file name
    :return: ``True`` if the namelist's Contents object has been modified
    :rtype: bool

    This function will detect namelist macros like ``PART_TASKS2D_X_SQUARE`` where:

    * ``TASKS`` tells that **effective_tasks** will be used to compute the
      decomposition (alternatively, ``THREADS`` can be used.
    * ``2D`` tells that the :class:`Rectangular2DPartitioner` class will be used
      to compute the partitioning. For now, ``2D`` is the only available option.
    * ``X`` tells that the user wants to get the X value of the computed partioning.
      Alternatively, ``Y`` can be used.
    * ``SQUARE`` refers to the partitioning method that will be used by the
      partitioning class. Any value that is accepted by the partitioning class is
      fine.
    """
    macrovalid = re.compile(
        "PART_"
        + "(?P<what>TASKS|THREADS)(?P<cls>2D)_"
        + "(?P<dim>[XY])_(?P<def>.*)$"
    )
    partitioning_classes = {"2D": Rectangular2DPartitioner}
    namw = False
    # Find the list of existing macros
    all_macros = set()
    for nam in namcontents.values():
        all_macros.update(nam.macros())
    # Consider only relevant macros
    for macroname in all_macros:
        macroname_re = macrovalid.match(macroname)
        if macroname_re:
            cache_key = (macroname_re.group("cls"), macroname_re.group("def"))
            if cache_key not in _PARTITIONERS_CACHE:
                partitioning_class = partitioning_classes[
                    macroname_re.group("cls")
                ]
                _PARTITIONERS_CACHE[cache_key] = partitioning_class(
                    macroname_re.group("def")
                )
            effective_n = dict(
                TASKS=effective_tasks, THREADS=effective_threads
            )[macroname_re.group("what")]
            part_x, part_y = _PARTITIONERS_CACHE[cache_key](effective_n)
            final_result = (
                part_x if macroname_re.group("dim") == "X" else part_y
            )
            if namlocal:
                logger.info(
                    "Setup macro %s=%s in %s",
                    macroname,
                    final_result,
                    namlocal,
                )
            else:
                logger.info("Setup macro %s=%s", macroname, final_result)
            namcontents.setmacro(macroname, final_result)
            namw = True
    return namw


if __name__ == "__main__":
    import doctest

    doctest.testmod()
