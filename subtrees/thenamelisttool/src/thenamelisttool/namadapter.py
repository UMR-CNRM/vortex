"""
Adapter classes for namelist's parsers.

Set of adapter classes that uses external namelist's parsers to provide
functionalities that fit the needs of TNT utilities.
"""

import abc
import collections
import re

from bronx.fancies import loggers

tntlog = loggers.getLogger('tntlog')

# Macros List from vortex's common.data.namelists
#: TNT's predefined list of macros
KNOWN_NAMELIST_MACROS = {'NPROC', 'NBPROC', 'NBPROC_IO', 'NCPROC', 'NDPROC',
                         'NBPROCIN', 'NBPROCOUT', 'IDAT', 'CEXP',
                         'TIMESTEP', 'FCSTOP', 'NMODVAL', 'NBE', 'SEED',
                         'MEMBER', 'NUMOD', 'OUTPUTID', 'NRESX', 'PERTURB',
                         'JOUR', 'RES', 'LLADAJ', 'LLADMON', 'LLFLAG',
                         'LLARO', 'LLVRP', 'LLCAN'}
# Other known namelist's macros (not to be substituted)
KNOWN_NAMELIST_MACROS.update(['substr6', 'substrA', 'substrC', 'XMP_TYPE',
                              'XLOPT_SCALAR', 'XNCOMBFLEN', 'val_sitr', 'val_sipr',
                              '_lbias_', '_lincr_'])

#: Output namelist sorting option: NO_SORTING. Keep the initial ordering.
NO_SORTING = 0
#: Output namelist sorting option: FIRST_ORDER_SORTING. Sort all keys within blocks.
FIRST_ORDER_SORTING = 1
#: Output namelist sorting option: SECOND_ORDER_SORTING. Sort only between indexes.
SECOND_ORDER_SORTING = 2


class AbstractNamelistAdapter(collections.abc.Mapping, metaclass=abc.ABCMeta):
    """Every Namelist adapter must derive from this abstract class."""

    @abc.abstractmethod
    def __init__(self, namelistsfile, macros=None):  # @UnusedVariable
        """
        :param str namelistsfile: The namelist itself or a path to a namelist file.
        """
        self._parser = None

    @property
    def parser(self):
        """The internal namelist's parser."""
        return self._parser

    # Public methods that operates on namelist's blocks

    def add_blocks(self, blocks):
        """Add a set of new blocks in the present namelist's set.

        :param list[str] blocks: ['BLOCK1', 'BLOCK2', ...]
        """
        for b in blocks:
            if b not in self:
                self._actual_newblock(b)
            else:
                tntlog.info('block "%s" is already present.', b)

    def remove_blocks(self, blocks):
        """Remove a set of blocks from the present namelist's set.

        :param list[str] blocks: ['BLOCK1', 'BLOCK2', ...]
        """
        for b in blocks:
            if b in self:
                self._actual_rmblock(b)
            else:
                tntlog.info('block "%s" to be removed but already missing.', b)

    def move_blocks(self, blocks):
        """Move/Rename a set of blocks within the present namelist's set.

        :param dict[str] blocks: {'BLOCK_OLD':'BLOCK_NEW', ...}
        """
        for (old_b, new_b) in blocks.items():
            if old_b in self:
                if new_b not in self:
                    self._actual_mvblock(old_b, new_b)
                else:
                    raise ValueError('block "{:s} already present'.format(new_b))
            else:
                tntlog.warning('block "%s" to be moved but missing from namelist: ignored.',
                               old_b)

    def check_blocks(self, another, macros=None):
        """
        Check that the present namelist's set contains the same set of blocks as
        **another** does.

        **another** can be either the filename of a namelist to be read, or any
        kind of :class:`AbstractNamelistAdapter` instance.

        If **macros** is not None, it can contain the macros a.k.a. values to be
        replaced, e.g.: {'NPROC':8, 'substrA':None} will replace all NPROC values
        by 8 and will let substrA untouched.

        :return set: The set of blocks that differ.
        """
        if not isinstance(another, AbstractNamelistAdapter):
            another = self.__class__(another, macros=macros)
        return set(self.keys()).symmetric_difference(set(another.keys()))

    # Public methods that operates on namelist's keys

    def add_keys(self, keys, doctor=False, indexes=None):
        """Set a set of keys in the present namelist's set.

        :param dict[tuple] keys: {('BLOCK','KEY'):value, ...}
        :param bool doctor: if true, try to convert value to DOCTOR norm according type
        :param dict[tuple] indexes: if present, set the keys at given index in block
                                    {('BLOCK','KEY'):index, ...}
        """
        if indexes is None:
            indexes = {}
        for ((b, k), v) in keys.items():
            idx = indexes.get((b, k), None)
            if b in self:
                self._actual_newkey(b, k,
                                    self._DOCTOR_convert(k, v) if doctor else v,
                                    index=idx)
            else:
                raise KeyError('block "{:s}" is missing: cannot set its "{:s}" key'
                               .format(b, k))

    def remove_keys(self, keys):
        """Remove a set of keys from the present namelist's set.

        :param list[tuple] keys: [('BLOCK1','KEY1'), ('BLOCK2','KEY2'), ...]
        """
        for (b, k) in self._expand_keys(keys):
            if b in self:
                if k in self[b]:
                    self._actual_rmkey(b, k)
                else:
                    tntlog.info(('key "%s" to be removed but already missing from block "%s".',
                                 k, b))
            else:
                tntlog.info('block "%s" missing: cannot remove its "%s" key.',
                            b, k)

    def move_keys(self, keys, doctor=False, keep_index=False):
        """
        Move a set of keys within the present namelist's set.

        :param dict[tuple] keys: {('BLOCK_OLD','KEY_OLD'):('BLOCK_NEW','KEY_NEW'), ...}
        :param bool doctor: if True, try to convert value to DOCTOR norm according type
        :param bool keep_index: if True, moved keys in identical block keep the
                                original index of key in block (except a sorting
                                is requested later on.
        """
        origin_keys = self._expand_keys(keys.keys(), radics=True)
        expanded_keys = {}
        for (ob, o_r, ok) in origin_keys:
            (nb, n_r) = keys[(ob, o_r)]
            expanded_keys[(ob, ok)] = (nb, ok.replace(o_r, n_r, 1))
        for (ob, ok), (nb, nk) in expanded_keys.items():
            if ob in self:
                if ok in self[ob]:
                    if keep_index and ob == nb:
                        idx = list(self[ob].keys()).index(ok)
                    else:
                        idx = None
                    v = self[ob][ok]
                    self.remove_keys([(ob, ok)])
                    if nb in self:
                        if nk not in self[nb]:
                            self.add_keys({(nb, nk): v},
                                          doctor=doctor, indexes={(nb, nk): idx})
                        else:
                            raise ValueError(('key "{:s}" in block "{:s}" ' +
                                              'already exists: prevent moving from ' +
                                              'block "{:s}" key "{:s}".')
                                             .format(nk, nb, ob, ok))
                    else:
                        raise KeyError(('block "{:s}" missing: cannot move key "{:s}"' +
                                        'from block "{:s}" to it as key "{:s}.')
                                       .format(nb, ok, ob, nk))
                else:
                    tntlog.warning('key "%s" missing from block "%s": cannot move it.',
                                   ok, ob)
            else:
                tntlog.warning('block "%s" missing: cannot move its key "%s".', ob, ok)

    def squeeze(self):
        """Squeeze the namelist: remove empty blocks."""
        self._actual_squeeze()

    # Generic utility methods

    @staticmethod
    def _all_macros(arg_macros):
        macros = {k: None for k in KNOWN_NAMELIST_MACROS}
        if arg_macros is not None:
            macros.update(arg_macros)
        return macros

    def _expand_keys(self, keys, radics=False):
        """
        Find all entries corresponding to the given keys,
        due to attributes and/or indexes.

        :param list[tuple] keys: [('BLOCK1','KEY1'), ('BLOCK2','KEY2'), ...]
        :param bool radics: add the radical in the tuples
        :return list[tuple]: The expanded list of namelist keys
        """
        expanded_keys = []
        for (b, k) in keys:
            if b in self:
                ek = [(b, nk) for nk in self[b].keys()
                      if re.match(k.replace('(', r'\(').replace(')', r'\)') + r'(\(.+\)|%.+)*$', nk)]
                if radics:
                    ek = [(b, k, nk) for (b, nk) in ek]
                expanded_keys.extend(ek)
        return set(expanded_keys)

    @staticmethod
    def _DOCTOR_convert(key, value, fatal=False):
        """
        According to the DOCTOR norm, try to convert value to the adequate type.

        Cf. http://www.umr-cnrm.fr/gmapdoc/IMG/pdf/coding-rules.pdf
        """
        t = key.split('%')[-1][0]
        try:
            if t in ('I', 'J', 'K', 'M', 'N'):
                try:
                    value = int(value)
                except ValueError:
                    raise ValueError('unable to convert variable {} from {} to int'.
                                     format(key, str(value)))
            elif t in ('L',):
                try:
                    value = bool(value)
                except ValueError:
                    raise ValueError('unable to convert variable {} from {} to bool'.
                                     format(key, str(value)))
            elif t in ('C',):
                try:
                    value = str(value)
                except ValueError:
                    raise ValueError('unable to convert variable {} from {} to str'.
                                     format(key, str(value)))
            else:
                try:
                    value = float(value)
                except ValueError:
                    raise ValueError('unable to convert variable {} from {} to float'.
                                     format(key, str(value)))
        except ValueError:
            if fatal:
                raise
        return value

    # Abstract methods that should be made available by concrete classes

    @abc.abstractmethod
    def __contains__(self, item):
        """Check if a block exists in the present namelist's set."""
        pass

    @abc.abstractmethod
    def __getitem__(self, item):
        """Retrieve the content of a namelist block.

        :return: The namelist block content
        :rtype: any subclass of collections_abc.Mapping
        """
        pass

    @abc.abstractmethod
    def __iter__(self):
        """Iterate through namelist blocks."""
        pass

    @abc.abstractmethod
    def __len__(self):
        """The number of namelist blocks."""
        pass

    @abc.abstractmethod
    def _actual_newblock(self, item):
        """Add a new block into the present namelist's set."""
        pass

    @abc.abstractmethod
    def _actual_rmblock(self, item):
        """Remove a block from the present namelist's set."""
        pass

    @abc.abstractmethod
    def _actual_mvblock(self, item, targetitem):
        """Move/Rename a block within the present namelist's set."""
        pass

    @abc.abstractmethod
    def _actual_newkey(self, block, key, value, index=None):
        """Set a new key in the present namelist's set."""
        pass

    @abc.abstractmethod
    def _actual_rmkey(self, block, key):
        """Remove a namelist keys from the present namelist's set."""
        pass

    @abc.abstractmethod
    def _actual_squeeze(self):
        """Squeeze the namelist: remove empty blocks."""
        pass

    @abc.abstractmethod
    def dumps(self, sorting=NO_SORTING):
        """
        Returns a string that represent the namelist's set (i.e. something
        readable by Fortran !)

        :param int sorting: The kind of sorting to apply within blocks
        """
        pass

    @abc.abstractmethod
    def merge(self, other):
        """Merge another namelist in the current one.

        :param AbstractNamelistAdapter other: Another namelist to merge in.
        """
        pass


class AbstractMapableNamelistAdapter(AbstractNamelistAdapter):
    """
    A generic NamelistAdapter that presumes that self._parser is itself some
    kind of Mapping object.
    """

    @staticmethod
    def _assert_mapping(obj):
        assert isinstance(obj, collections.abc.Mapping), \
            'The "{!r}" must be some kind of Mapping.'

    def __contains__(self, item):
        """Check if a block exists in the present namelist's set."""
        self._assert_mapping(self._parser)
        return item in self._parser

    def __getitem__(self, item):
        """Retrieve the content of a namelist block.

        :return: The namelist block content
        :rtype: any subclass of collections_abc.Mapping
        """
        self._assert_mapping(self._parser)
        value = self._parser[item]
        self._assert_mapping(value)
        return value

    def __iter__(self):
        """Iterate through namelist blocks."""
        self._assert_mapping(self._parser)
        return self._parser.__iter__()

    def __len__(self):
        """The number of namelist blocks."""
        self._assert_mapping(self._parser)
        return len(self._parser)


class BronxNamelistAdapter(AbstractMapableNamelistAdapter):
    """
    A NamelistAdapter that relies on the namelist parser provided by the
    :mod:`bronx` package.
    """

    def __init__(self, namelistsfile, macros=None):
        super().__init__(namelistsfile)
        # Delay the import of the bronx library since one may want to use another backend
        from bronx.datagrip import namelist
        actual_macros = self._all_macros(macros)
        self._parser = namelist.namparse(namelistsfile, macros=actual_macros)
        for macro, value in actual_macros.items():
            self._parser.setmacro(macro, value)

    def _actual_newblock(self, item):
        self.parser.newblock(item)

    def _actual_rmblock(self, item):
        del self.parser[item]

    def _actual_mvblock(self, item, targetitem):
        self.parser.mvblock(item, targetitem)

    def _actual_newkey(self, block, key, value, index=None):
        self[block].setvar(key, value, index=index)

    def _actual_rmkey(self, block, key):
        del self[block][key]

    def _actual_squeeze(self):
        for b in list(self.parser.keys()):
            if len(self.parser[b]) == 0:
                self._actual_rmblock(b)

    def dumps(self, sorting=NO_SORTING):
        """Returns a string that represent the namelist's set."""
        from bronx.datagrip import namelist as bnamelists
        sorting_map = dict(NO_SORTING=bnamelists.NO_SORTING,
                           FIRST_ORDER_SORTING=bnamelists.FIRST_ORDER_SORTING,
                           SECOND_ORDER_SORTING=bnamelists.SECOND_ORDER_SORTING)
        return self.parser.dumps(sorting=sorting_map.get(sorting, sorting))

    def merge(self, other):
        """Merge another namelist in the current one.

        :param AbstractNamelistAdapter other: Another namelist to merge in.
        """
        assert isinstance(other, self.__class__)
        self.parser.merge(other.parser)
