"""
Module that deals with part of the Arpege/IFS listings related to the
processing of observations (JO-tables).
"""

import re
import sys
from collections import OrderedDict

from .util import read_listing

#: Automatic export
__all__ = ['JoTables', 'JoTable']

# Default thresholds for the check
DEFAULT_N_THRESHOLD = 0.0005
DEFAULT_JO_THRESHOLD = 0.0003


class JoTablesMismatchError(Exception):
    """Items from Experiment and Reference JoTables do not match."""
    pass


def _compute_diff(exp, ref):
    """Internal function to compute difference and relative difference.

    :param exp: Value to test (float or int)
    :param ref: Ref value
    """
    diff = exp - ref
    if ref != 0:
        reldiff = float(diff) / float(ref)
    else:
        if exp != 0:
            reldiff = 1
        else:
            reldiff = 0
    return diff, reldiff


def _chk_diff(exp, ref, thres, bw=False):
    """Internal function to check if the relative difference is within bounds.

    :param exp: Value to test (float or int)
    :param ref: Ref value
    :param thres: Threshold
    :param bw: Black & White flag
    """
    diff, reldiff = _compute_diff(exp, ref)
    # Set colors
    if abs(reldiff) > thres and not bw:
        colstart = '\x1b[31m'
        colend = '\x1b[0m'
    else:
        colstart = ''
        colend = ''
    # Go back
    return (exp, ref, diff, colstart, reldiff, colend)


def _write_n(out, sthg):
    r"""Write a string into **out**, ending with '\n'."""
    out.write(sthg + '\n')


class _JoMixin:
    """Some internal method common to all of the Jo classes."""

    _ChildClass = object  # Define the basic child class
    _re_begin = None
    _re_end = None

    def __init__(self, name):
        self.name = name.upper()
        self._content = OrderedDict()
        self._cur_child = None

    def __len__(self):
        return len(self._content)

    def __getitem__(self, item):
        return self._content[item]

    def __contains__(self, item):
        return item in self._content

    def keys(self):
        """Return the list of keys of all elements contained in this object."""
        return self._content.keys()

    def values(self):
        """Return the list of elements contained in this object."""
        return self._content.values()

    def end_of_group(self, *kargs):
        """Action to be performed when the current object is reaching its end."""
        pass

    def _results_hook(self, groups):
        """Tweak the regex results in order to satisfy the child constructor."""
        return reversed(groups)

    def parse_line(self, line):
        """Recursively process one line of the listing file."""
        if self._cur_child is not None:
            # Pass the input line to the child object
            mres = self._re_end.match(line)
            if mres:
                self._cur_child.parse_line(line)
                self._cur_child.end_of_group(* mres.groups())
                self._cur_child = None
            else:
                self._cur_child.parse_line(line)
        # Look for the start of a new child object
        mres = self._re_begin.match(line)
        if mres:
            self._cur_child = self._ChildClass(* self._results_hook(mres.groups()))
            self._content[self._cur_child.name] = self._cur_child


class _JoMixinPlus(_JoMixin):
    """Some internal method common to all of the Jo classes."""

    def __getitem__(self, item):
        """If the element is missing, return a dummy thing"""
        if item in self:
            return self._content[item]
        else:
            return self._ChildClass(item, dummy=True)

    def _diff_superset(self, ref):
        """Union between elements of the reference and self list."""
        keys = list(ref.keys())
        # New keys are appended to the reference list
        keys.extend([k for k in self.keys() if k not in keys])
        return keys


class JoVariable:
    """Object containing data on a given variable."""

    def __init__(self, name, n=0, jo=0, obserr=0, bgerr=0, dummy=False):
        """

        :param name: Name of the variable
        :param n: Number of obs
        :param jo: Jo
        :param obserr: Observation Error
        :param bgerr: Background Error
        """
        self.name = name.upper()
        self.n = int(n)
        self.jo = float(jo)
        self.obserr = float(obserr)
        if bgerr == 'RMDI':
            self.bgerr = 1 - 1e10
        else:
            self.bgerr = float(bgerr)
        self.dummy = dummy

    def __str__(self):
        return ('  %8d  %15.2f  %10.4f  %10.2e %10.2e    %3s' %
                (self.n, self.jo, self.jo / self.n, self.obserr, self.bgerr,
                 self.name))

    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return all([self.__getattribute__(a) == other.__getattribute__(a)
                    for a in ('name', 'n', 'jo', 'obserr', 'bgerr')])

    @property
    def jon(self):
        """Jo/N"""
        return self.jo / float(self.n) if self.n else 0

    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        return {'n': dict(zip(('diff', 'reldiff'),
                              _compute_diff(self.n, ref.n))),
                'jo': dict(zip(('diff', 'reldiff'),
                               _compute_diff(self.jo, ref.jo))),
                'jo/n': dict(zip(('diff', 'reldiff'),
                                 _compute_diff(self.jon, ref.jon))),
                'nref': ref.n,
                'nxp': self.n,
                'jo/nref': 0 if (ref.n == 0) else ref.jo / ref.n,
                'jo/nxp': 0 if (self.n == 0) else self.jo / self.n, }

    def as_dict(self):
        """Return this entry data as a dictionary."""
        return {'n': self.n,
                'jo': self.jo,
                'jon': 0 if (self.n == 0) else self.jo / self.n, }

    def _item_write(self, ref, out, bw, item, item_l, item_t=0, item_f='%15.6g'):
        _write_n(out,
                 ('    %-9s  Exp: ' + item_f + '  Ref: ' + item_f + '  Diff: ' + item_f +
                  '  RelDiff: %s%12.9f%s  (Var: %s)') %
                 ((item_l,) + _chk_diff(getattr(self, item), getattr(ref, item), item_t, bw) +
                  (self.name,)))

    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout):
        """Print the summary of the difference between two variables.

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        """
        self._item_write(ref, out, bw, 'n', 'ObsCount', nthres, item_f='%15d')
        self._item_write(ref, out, bw, 'jo', 'Jo', jothres)
        if self.obserr != ref.obserr:
            self._item_write(ref, out, bw, 'obserr', 'ObsErr')
        if self.bgerr != ref.bgerr:
            self._item_write(ref, out, bw, 'bgerr', 'BgErr')

    def end_of_group(self, *kargs):
        pass

    def parse_line(self, line):
        pass


class JoSensor(_JoMixinPlus):
    """Object enclosing data for a given Sensor."""

    _re_begin = re.compile(r'^\s+([a-zA-Z0-9_]+)\s+' +
                           r'(\d+)\s+' +
                           r'([\d.E+]+)\s+' +
                           r'[*\d.E+-]+\s+' +
                           r'([\d.E+-]+)\s+' +
                           r'([\d.E+-]+|RMDI)\s*$')
    _re_end = re.compile(r'^\s*(Obs|Code)type')
    _ChildClass = JoVariable

    def __init__(self, name, idnum=-9999, dummy=False):
        """

        :param idnum: Codetype Id
        :param name: Name of the sensor
        """
        super().__init__(name)
        self.id = int(idnum)
        self.dummy = dummy

    def __str__(self):
        return "\n".join(['{}: {}'.format(var, self.name) for var in self.values()]) + "\n"

    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return (self.name == other.name and
                set(self.keys()) == set(other.keys()) and
                all([self[k] == other[k] for k in self.keys()]))

    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        diff = OrderedDict()
        for v in self._diff_superset(ref):
            diff[v] = self[v].compute_diff(ref[v])
        return diff

    def as_dict(self):
        """Return this entry data as a dictionary."""
        dico = OrderedDict()
        for v in self.keys():
            dico[v] = self[v].as_dict()
        return dico

    def maxdiff(self, ref):
        """Compute and sort out the maximum difference."""
        diff = self.compute_diff(ref)
        return {p: {sp: max([0.] + [abs(diff[v][p][sp]) for v in self._diff_superset(ref)])
                    for sp in ('diff', 'reldiff')}
                for p in ('n', 'jo', 'jo/n')}

    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout):
        """
        Print the summary of the difference between two sensors

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        """
        _write_n(out, '  %s' % self.name)
        for vname in self._diff_superset(ref):
            self[vname].print_diff(ref[vname],
                                   bw=bw,
                                   nthres=nthres,
                                   jothres=jothres)

    def _results_hook(self, groups):
        return groups


class JoObstype(_JoMixinPlus):
    """Object enclosing data for a given Obstype."""

    _re_begin = re.compile(r'^\s*Codetype\s+(\d+)\s+===\s+(.+)\s*$')
    _re_end = re.compile(r'^\s*(Obs|Code)type')
    _ChildClass = JoSensor

    def __init__(self, name, idnum=-9999, dummy=False):
        """

        :param idnum: Obstype Id
        :param name: Name of the Obstype
        """
        super().__init__(name)
        self.id = int(idnum)
        self.ntotal = 0
        self.jo = 0
        self.dummy = dummy

    def __str__(self):
        ret = 'Obstype %3d: %s\n\n' % (self.id, self.name)
        ret += '  %8s  %15s  %10s  %10s %10s    %3s: %s\n' % \
            ('ObsCount', 'Jo', 'Jo/n', 'ObsErr', 'BgErr',
             'Var', 'Sensor Name')
        for sensor in self.values():
            ret += str(sensor)
        ret += '\n'
        ret += '  %8d  %15.2f  %10.4f                           TOTAL\n' % \
            (self.ntotal, self.jo, self.jo / self.ntotal)
        return ret + '\n'

    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return (self.name == other.name and
                set(self.keys()) == set(other.keys()) and
                all([self[k] == other[k] for k in self.keys()]))

    @property
    def jon(self):
        """Jo/N"""
        return self.jo / float(self.ntotal) if self.ntotal else 0

    def compute_general(self, ref):
        """Compute difference and relative difference for n, jo, jo/n for the whole obstype."""
        diff = OrderedDict()
        ndiff, nreldiff = _compute_diff(self.ntotal, ref.ntotal)
        jodiff, joreldiff = _compute_diff(self.jo, ref.jo)
        jondiff, jonreldiff = _compute_diff(self.jon, ref.jon)
        diff["GLOBAL"] = {
            'n': {'diff': ndiff, 'reldiff': nreldiff, },
            'jo': {'diff': jodiff, 'reldiff': joreldiff, },
            'jo/n': {'diff': jondiff, 'reldiff': jonreldiff, },
            'nref': ref.ntotal,
            'nxp': self.ntotal,
            'jo/nref': 0 if (ref.ntotal == 0) else ref.jo / ref.ntotal,
            'jo/nxp': 0 if (self.ntotal == 0) else self.jo / self.ntotal, }

        return diff

    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        diff = OrderedDict()
        diff[self.name] = self.compute_general(ref)
        for s in self._diff_superset(ref):
            diff[s] = self[s].compute_diff(ref[s])
        return diff

    def as_dict(self):
        """Compute difference and relative difference for n, jo, jo/n."""
        dico = OrderedDict()
        dico[self.name] = {'n': self.ntotal, 'jo': self.jo,
                           'jon': 0 if (self.ntotal == 0) else self.jo / self.ntotal, }

        for s in self.keys():
            dico[s] = self[s].as_dict()
        return dico

    def maxdiff(self, ref):
        """Compute and sort out the maximum difference."""
        return {p: {sp: max([0.] + [self[s].maxdiff(ref[s])[p][sp]
                                    for s in self._diff_superset(ref)])
                    for sp in ('diff', 'reldiff')}
                for p in ('n', 'jo', 'jo/n')}

    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout):
        """Print the summary of the difference between two obstypes.

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        """
        _write_n(out, 'Obstype %3d: %s' % (self.id, self.name))
        _write_n(out, '')
        for sname in self._diff_superset(ref):
            self[sname].print_diff(ref[sname],
                                   bw=bw,
                                   nthres=nthres,
                                   jothres=jothres)
        _write_n(out, '')
        _write_n(out, '  TOTAL')
        _write_n(out, ('    Obscount   Exp: %15d  Ref: %15d  ' +
                       'Diff: %15d  RelDiff: %s%12.9f%s') %
                 _chk_diff(self.ntotal, ref.ntotal, nthres, bw))
        _write_n(out, ('    Jo         Exp: %15.2f  Ref: %15.2f  ' +
                       'Diff: %15.2f  RelDiff: %s%12.9f%s') %
                 _chk_diff(self.jo, ref.jo, jothres, bw))
        _write_n(out, '')

    def end_of_group(self, *kargs):
        """Record the obstype ObsCount and Jo.

        :param ntotal: obstype ObsCount
        :param jo: obstype Jo
        """
        self.ntotal = int(kargs[0])
        self.jo = float(kargs[1])


class JoTable(_JoMixinPlus):
    """Object containing one JO-table."""

    _re_begin = re.compile(r'^\s*Obstype\s+(\d+)\s+===\s*(.*)$')
    _re_end = re.compile(r'^\s*ObsType\s+\d+\s+Total:\s+(\d+)\s+' +
                         r'([\d.E+-]+)\s+[\d.E+-]+\s*$')
    _ChildClass = JoObstype

    def __init__(self, name):
        super().__init__(name)
        self.ntotal = 0
        self.jo = 0

    def __str__(self):
        ret = '=====================\n'
        ret += 'Begining of JO-table: %s\n\n' % self.name
        for obstype in self.values():
            if obstype.ntotal > 0:
                ret += str(obstype)
        ret += '\n'
        ret += ('  %8d  %15.2f  %10.4f' +
                '                           GRAND TOTAL\n') % \
            (self.ntotal, self.jo, self.jo / self.ntotal)
        return ret + '\n'

    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return (set(self.keys()) == set(other.keys()) and
                all([self[k] == other[k] for k in self.keys()]))

    @property
    def jon(self):
        """Jo/N"""
        return self.jo / float(self.ntotal)

    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        diff = OrderedDict()
        for o in self._diff_superset(ref):
            if len(self[o]) or len(ref[o]):
                diff[o] = self[o].compute_diff(ref[o])
        return diff

    def as_dict(self):
        """Return this entry data as a dictionary."""
        dico = OrderedDict()
        for o in self.keys():
            dico[o] = self[o].as_dict()
        return dico

    def maxdiff(self, ref):
        """Compute and sort out the maximum difference."""
        return {p: {sp: max([0.] + [self[o].maxdiff(ref[o])[p][sp]
                                    for o in self._diff_superset(ref) if len(self[o]) or len(ref[o])])
                    for sp in ('diff', 'reldiff')}
                for p in ('n', 'jo', 'jo/n')}

    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout,
                   onlymaxdiff=False):
        """Print the summary of the difference between two JO-tables.

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        :param onlymaxdiff: Only max difference is printed for each table
        """
        _write_n(out, '=====================')
        if onlymaxdiff:
            maxdiff = self.maxdiff(ref)
            _write_n(out, 'Jo-table: %s' % self.name)
            _write_n(out, '(Worst differences)')
            _write_n(out, 'Obscount: {:10d} ({:5.2f}%)'.format(int(maxdiff['n']['diff']),
                                                               100. * maxdiff['n']['reldiff']))
            _write_n(out, 'Jo:       {:10.2f} ({:5.2f}%)'.format(maxdiff['jo']['diff'],
                                                                 100. * maxdiff['jo']['reldiff']))
            _write_n(out, 'Jo/n:     {:10.2f} ({:5.2f}%)'.format(maxdiff['jo/n']['diff'],
                                                                 100. * maxdiff['jo/n']['reldiff']))
        else:
            _write_n(out, 'Begining of JO-table: %s' % self.name)
            _write_n(out, '')
            for otype in self._diff_superset(ref):
                if len(self[otype]) or len(ref[otype]):
                    self[otype].print_diff(ref[otype],
                                           bw=bw,
                                           nthres=nthres,
                                           jothres=jothres)
            _write_n(out, 'GRAND TOTAL')
            _write_n(out, ('    Obscount   Exp: %15d  Ref: %15d  ' +
                           'Diff: %15d  RelDiff: %s%12.9f%s') %
                     _chk_diff(self.ntotal, ref.ntotal, nthres, bw))
            _write_n(out, ('    Jo         Exp: %15.2f  Ref: %15.2f  ' +
                           'Diff: %15.2f  RelDiff: %s%12.9f%s') %
                     _chk_diff(self.jo, ref.jo, jothres, bw))
        _write_n(out, '')

    def end_of_group(self, *kargs):
        """Record the global ObsCount and Jo.

        :param ntotal: Global ObsCount
        :param jo: Global Jo
        """
        self.ntotal = int(kargs[0])
        self.jo = float(kargs[1])


class JoTables(_JoMixin):
    """Object enclosing one or more JO-table."""

    _ChildClass = JoTable
    _re_begin = re.compile(r'^\s*Diagnostic JO-table \(JOT\) (.*)$')
    _re_end = re.compile(r'^\s*Jo Global\s+:\s+(\d+)\s+' +
                         r'([\d.E+-]+)\s+[\d.E+-]+\s*$')

    def __init__(self, filename, fcontent=None):
        """The constructor call triggers the reading of the file.

        :param filename: Name of the file where the Jo-tables are read
        :param fcontent: Array of listing lines (if not provided, **filename** is
            opened and read it.
        """
        super().__init__(filename)
        self.filename = filename

        if fcontent is None:
            lines = read_listing(self.filename)
        else:
            lines = fcontent

        for line in lines:
            self.parse_line(line)

    def __str__(self):
        ret = 'Jo Tables read from file: %s\n' % self.filename
        ret += '\n'
        for table in self.values():
            ret += str(table)
        return ret

    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return (set(self.keys()) == set(other.keys()) and
                all([self[k] == other[k] for k in self.keys()]))

    def print_head(self, ref, out=sys.stdout):
        """Print very useful generic informations."""
        _write_n(out, 'Experiment Jo Tables read from file: %s' % self.filename)
        _write_n(out, 'Reference  Jo Tables read from file: %s' % ref.filename)
        _write_n(out, '')

    def _allow_diff(self, ref):
        """Check if it's possible to compute a diff."""
        todolist = list()
        if len(self) == len(ref) == 1:
            t = list(self.keys())[0]
            tref = list(ref.keys())[0]
            todolist.append(('{} vs. {}'.format(t, tref), t, tref))
        elif (not isinstance(ref, self.__class__) or
                set(self.keys()) != set(ref.keys())):
            raise JoTablesMismatchError('Jo tables names don\'t match')
        else:
            for t in self.keys():
                todolist.append((t, t, t))
        return todolist

    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        todolist = self._allow_diff(ref)
        diff = OrderedDict()
        for label, t, tref in todolist:
            diff[label] = self[t].compute_diff(ref[tref])
        return diff

    def as_dict(self):
        """As dict"""
        dico = OrderedDict()
        for t in self.keys():
            dico[t] = self[t].as_dict()
        return dico

    def maxdiff(self, ref):
        """Compute and sort out the maximum difference."""
        todolist = self._allow_diff(ref)
        maxdiff = {p: {sp: max([0.] + [self[t].maxdiff(ref[tref])[p][sp]
                                       for _, t, tref in todolist])
                       for sp in ('diff', 'reldiff')}
                   for p in ('n', 'jo', 'jo/n')}
        return maxdiff

    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout,
                   onlymaxdiff=False):
        """Print the summary of the differences between JO-tables.

        The :class:`JoTablesMismatchError` exception may be raised if the
        object to compare to (ref) doesn't have the same structure.

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        :param onlymaxdiff: Only max difference is printed for each table
        """
        todolist = self._allow_diff(ref)
        for _, tname, tref in todolist:
            self[tname].print_diff(ref[tref],
                                   nthres=nthres, jothres=jothres,
                                   bw=bw,
                                   out=out,
                                   onlymaxdiff=onlymaxdiff)
