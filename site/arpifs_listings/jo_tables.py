#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

__all__ = ['Jo_tables', 'Jo_table']

import sys
import collections

import re

# Default thresholds for the check
DEFAULT_N_THRESHOLD = 0.0005
DEFAULT_JO_THRESHOLD = 0.0003


class JoTablesMismatchError(Exception):
    ''' Items from Experiment and Reference JoTables don't match '''
    pass


class JoTableNotFoundError(IndexError):
    ''' The required Jo-Table doesn't exist '''
    pass


def _compute_diff(exp, ref):
    """
    Internal function to compute difference and relative difference.

    :param exp: Value to test (float or int)
    :param ref: Ref value
    """
    diff = exp - ref
    if ref != 0:
        reldiff = float(diff) / float(ref)
    else:
        reldiff = 9.999
    return diff, reldiff

def _chk_diff(exp, ref, thres, bw=False):
    '''
    Internal function to check if the relative difference is within bounds.
    If not trigger the use of the red color

    :param exp: Value to test (float or int)
    :param ref: Ref value
    :param thres: Threshold
    :param bw: Black & White flag
    '''

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
    """Write a string into **out**, ending with '\n'."""
    out.write(sthg + '\n')


class JoTables(object):
    def __init__(self, filename, debug=0):
        '''
        Object containing several JO-tables.

        The constructor call trigger the reading of the file.

        :param filename: Name of the file where the Jo-tables are read
        '''
        self.filename = filename
        self.__debug = debug
        self.tables = collections.OrderedDict()

        self._re_t_begin = re.compile('^\s*Diagnostic JO-table \(JOT\) (.*)$')
        self._re_t_end = re.compile('^\s*Jo Global\s+:\s+(\d+)\s+' +
                                    '([\d.E+-]+)\s+[\d.E+-]+\s*$')

        self._parse_listing()

    def __str__(self):
        ret = 'Jo Tables read from file: %s\n' % self.filename
        ret += '\n'
        for table in self.tables.values():
            ret += str(table)
        return ret

    def __getitem__(self, item):
        '''
        Return the Jo-table object designated by item

        The JoTableNotFoundError exception may be raised if the requested table
        doesn't exist

        :param item: the table name you are looking for.
        '''

        for table in self.tables.values():
            if table.name == item:
                return table
        raise JoTableNotFoundError
    
    def __len__(self):
        return len(self.tables)
    
    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return set(self.tables.keys()) == set(other.tables.keys()) \
               and all([self.tables[k] == other.tables[k]
                        for k in self.tables.keys()])
    
    def print_head(self, ref, out=sys.stdout):
        '''
        Print very usefull generic informations
        '''
        _write_n(out, 'Experiment Jo Tables read from file: %s' % self.filename)
        _write_n(out, 'Reference  Jo Tables read from file: %s' % ref.filename)
        _write_n(out, '')
    
    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        return {t:self.tables[t].compute_diff(ref.tables[t])
                for t in self.tables.keys()}
    
    def maxdiff(self, ref):
        """Compute and sort out the maximum difference."""
        return {p:{sp:max([0.] + [self.tables[t].maxdiff(ref.tables[t])[p][sp]
                                  for t in self.tables.keys()])
                   for sp in ('diff', 'reldiff')}
                for p in ('n', 'jo', 'jo/n')}
    
    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout,
                   onlymaxdiff=False):
        '''

        Print the summary of the difference between JO-tables

        The JoTablesMismatchError exception may be raised if the reference
        object to compare to (ref) doesn't have the same structure.

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        :param onlymaxdiff: Only max difference is printed for each table
        '''
        if set(self.tables.keys()) != set(ref.tables.keys()):
            raise JoTablesMismatchError('Jo tables names don\'t match')
        for tname in self.tables.keys():
            self.tables[tname].print_diff(ref.tables[tname],
                                          nthres=nthres, jothres=jothres,
                                          bw=bw,
                                          out=out,
                                          onlymaxdiff=onlymaxdiff)

    def _parse_listing(self):
        '''

        Read the listing file

        '''
        # Read in the listing
        fh = open(self.filename, 'r')
        myfile = fh.readlines()
        fh.close()
        cur_table = None
        for line in myfile:
            # Pass the input line to the table object
            if cur_table:
                mres = self._re_t_end.match(line)
                if mres:
                    cur_table.end_of_table(*mres.groups())
                    if self.__debug:
                        print('End of table:      ' + cur_table.name)
                    cur_table = None
                else:
                    cur_table.parse_line(line)
            # Look for the start of a new table
            else:
                mres = self._re_t_begin.match(line)
                if mres:
                    cur_table = JoTable(mres.group(1), self.__debug)
                    self.tables[cur_table.name] = cur_table
                    if self.__debug:
                        print('Begining of table: ' + cur_table.name)


class JoTable(object):
    def __init__(self, name, debug=0):
        '''
        Object containing one JO-table

        :param name: Name of the Jo-table
        '''
        self.name = name
        self.__debug = debug
        self.obstypes = collections.OrderedDict()

        self._re_ot_begin = re.compile('^\s*Obstype\s+(\d+)\s+===\s*(.*)$')
        self._re_ot_end = re.compile('^\s*ObsType\s+\d+\s+Total:\s+(\d+)\s+' +
                                     '([\d.E+-]+)\s+[\d.E+-]+\s*$')

        self.__cur_obstype = None
    
    def __str__(self):
        ret = '=====================\n'
        ret += 'Begining of JO-table: %s\n\n' % self.name
        for obstype in self.obstypes.values():
            if obstype.ntotal > 0:
                ret += str(obstype)
        ret += '\n'
        ret += ('  %8d  %15.2f  %10.4f' + \
                '                           GRAND TOTAL\n') % \
            (self.ntotal, self.jo, self.jo / self.ntotal)
        return ret + '\n'
    
    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return set(self.obstypes.keys()) == set(other.obstypes.keys()) \
               and all([self.obstypes[k] == other.obstypes[k]
                        for k in self.obstypes.keys()])
    
    @property
    def jon(self):
        """Jo/N"""
        return self.jo / float(self.ntotal)
    
    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        return {o:self.obstypes[o].compute_diff(ref.obstypes[o])
                for o in self.obstypes.keys()}
    
    def maxdiff(self, ref):
        """Compute and sort out the maximum difference."""
        return {p:{sp:max([0.] + [self.obstypes[o].maxdiff(ref.obstypes[o])[p][sp]
                                  for o in self.obstypes.keys()])
                   for sp in ('diff', 'reldiff')}
                for p in ('n', 'jo', 'jo/n')}
    
    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout,
                   onlymaxdiff=False):
        '''

        Print the summary of the difference between two JO-tables

        The JoTablesMismatchError exception may be raised if the reference
        object to compare to (ref) doesn't have the same structure.

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        :param onlymaxdiff: Only max difference is printed for each table
        '''
        _write_n(out, '=====================')
        if onlymaxdiff:
            maxdiff = self.maxdiff(ref)
            _write_n(out, 'JO-table: %s' % self.name)
            _write_n(out, '(Worst differences)')
            _write_n(out, 'Obscount: %15d (diff) %15.2f (reldiff)' % (maxdiff['n']['diff'],
                                                                      maxdiff['n']['reldiff']))
            _write_n(out, 'Jo: %15.2f (diff) %15.2f (reldiff)' % (maxdiff['jo']['diff'],
                                                                  maxdiff['jo']['reldiff']))
            _write_n(out, 'Jo/n: %15.2f (diff) %15.2f (reldiff)' % (maxdiff['jo/n']['diff'],
                                                                    maxdiff['jo/n']['reldiff']))
        else:
            _write_n(out, '=====================')
            _write_n(out, 'Begining of JO-table: %s' % self.name)
            _write_n(out, '')
            if set(ref.obstypes.keys()) != set(self.obstypes.keys()):
                raise JoTablesMismatchError('Incompatible set of obstypes')
            for otype in self.obstypes.keys():
                if self.obstypes[otype].ntotal > 0:
                    if self.obstypes[otype].id == ref.obstypes[otype].id:
                        self.obstypes[otype].print_diff(ref.obstypes[otype],
                                                        bw=bw,
                                                        nthres=nthres,
                                                        jothres=jothres)
                    else:
                        raise JoTablesMismatchError('Obstype numbers don\'t match')
            _write_n(out, 'GRAND TOTAL')
            _write_n(out, ('    Obscount   Exp: %15d  Ref: %15d  ' + \
                           'Diff: %15d  RelDiff: %s%12.9f%s') % \
                           _chk_diff(self.ntotal, ref.ntotal, nthres, bw))
            _write_n(out, ('    Jo         Exp: %15.2f  Ref: %15.2f  ' + \
                           'Diff: %15.2f  RelDiff: %s%12.9f%s') % \
                           _chk_diff(self.jo, ref.jo, jothres, bw))
        _write_n(out, '')

    def parse_line(self, line):
        '''

        Process one line of the listing file

        :param line: One line of the listing (as a string)
        '''
        mres = self._re_ot_begin.match(line)
        if mres:
            self.__cur_obstype = JoObstype(*mres.groups(),
                                            debug=self.__debug)
            self.obstypes[self.__cur_obstype.name] = self.__cur_obstype
            if self.__debug:
                print('Begining of obstype %d: %s' % \
                      (self.__cur_obstype.id, self.__cur_obstype.name))
        # Pass the input line to the codetype object
        if self.__cur_obstype:
            mres = self._re_ot_end.match(line)
            if mres:
                self.__cur_obstype.end_of_obstype(*mres.groups())
                self.__cur_obstype = None
            else:
                self.__cur_obstype.parse_line(line)

    def end_of_table(self, ntotal, jo):
        '''

        Record the global ObsCount and Jo

        :param ntotal: Global ObsCount
        :param jo: Global Jo
        '''
        self.ntotal = int(ntotal)
        self.jo = float(jo)
        if self.__debug:
            print('Finalizing table   %s: N=%d and Jo=%d' % \
                  (self.name, self.ntotal, self.jo))


class JoObstype(object):
    def __init__(self, idnum, name, debug=0):
        '''
        Object containing one Obstype

        :param idnum: Obstype Id
        :param name: Name of the Obstype
        '''
        self.id = int(idnum)
        self.name = name
        self.__debug = debug
        self.sensors = collections.OrderedDict()
        self.ntotal = 0

        self._re_s_begin = re.compile('^\s*Codetype\s+(\d+)\s+===\s+(.+)\s*$')

        self.__cur_sensor = None
    
    def __str__(self):
        ret = 'Obstype %3d: %s\n\n' % (self.id, self.name)
        ret += '  %8s  %15s  %10s  %10s %10s    %3s: %s\n' % \
            ('ObsCount', 'Jo', 'Jo/n', 'ObsErr', 'BgErr',
             'Var', 'Sensor Name')
        for sensor in self.sensors.values():
            ret += str(sensor)
        ret += '\n'
        ret += '  %8d  %15.2f  %10.4f                           TOTAL\n' % \
            (self.ntotal, self.jo, self.jo / self.ntotal)
        return ret + '\n'
    
    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return self.name == other.name \
               and set(self.sensors.keys()) == set(other.sensors.keys()) \
               and all([self.sensors[k] == other.sensors[k]
                        for k in self.sensors.keys()])
    
    @property
    def jon(self):
        """Jo/N"""
        return self.jo / float(self.ntotal)
    
    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        return {s:self.sensors[s].compute_diff(ref.sensors[s])
                for s in self.sensors.keys()}
    
    def maxdiff(self, ref):
        """Compute and sort out the maximum difference."""
        return {p:{sp:max([0.] + [self.sensors[s].maxdiff(ref.sensors[s])[p][sp]
                                  for s in self.sensors.keys()])
                   for sp in ('diff', 'reldiff')}
                for p in ('n', 'jo', 'jo/n')}
    
    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout):
        '''
        Print the summary of the difference between two obstypes

        The JoTablesMismatchError exception may be raised if the reference
        object to compare to (ref) doesn't have the same structure.

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        '''
        _write_n(out, 'Obstype %3d: %s' % (self.id, self.name))
        _write_n(out, '')
        if set(self.sensors.keys()) != set(ref.sensors.keys()):
            raise JoTablesMismatchError('Incompatible set of sensors')
        for sname in self.sensors.keys():
            self.sensors[sname].print_diff(ref.sensors[sname],
                                           bw=bw,
                                           nthres=nthres,
                                           jothres=jothres)
        _write_n(out, '')
        _write_n(out, '  TOTAL')
        _write_n(out, ('    Obscount   Exp: %15d  Ref: %15d  ' + \
                       'Diff: %15d  RelDiff: %s%12.9f%s') % \
                       _chk_diff(self.ntotal, ref.ntotal, nthres, bw))
        _write_n(out, ('    Jo         Exp: %15.2f  Ref: %15.2f  ' + \
                       'Diff: %15.2f  RelDiff: %s%12.9f%s') % \
                       _chk_diff(self.jo, ref.jo, jothres, bw))
        _write_n(out, '')

    def parse_line(self, line):
        '''

        Process one line of the listing file

        :param line: One line of the listing (as a string)
        '''
        mres = self._re_s_begin.match(line)
        if mres:
            self.__cur_sensor = JoSensor(*mres.groups())
            self.sensors[self.__cur_sensor.name] = self.__cur_sensor
            if self.__debug:
                print('Begining of sensor. Codetype=%d: %s' % \
                      (self.__cur_sensor.id, self.__cur_sensor.name))
        # Pass the input line to the sensor object
        if self.__cur_sensor:
            self.__cur_sensor.parse_line(line)

    def end_of_obstype(self, ntotal, jo):
        '''

        Record the obstype ObsCount and Jo

        :param ntotal: obstype ObsCount
        :param jo: obstype Jo
        '''
        self.ntotal = int(ntotal)
        self.jo = float(jo)
        if self.__debug:
            print('Finalizing obstype  %d: N=%d and Jo=%d' % \
                  (self.id, self.ntotal, self.jo))


class JoSensor(object):
    def __init__(self, idnum, name):
        '''
        Object containing one sensor

        :param idnum: Codetype Id
        :param name: Name of the sensor
        '''
        self.id = int(idnum)
        self.name = name
        self.variables = collections.OrderedDict()

        self._re_var = re.compile('^\s+([a-zA-Z0-9_]+)\s+' +
                                  '(\d+)\s+' +
                                  '([\d.E+]+)\s+'+
                                  '([\d.E+-]+)\s+' +
                                  '([\d.E+-]+)\s+'+
                                  '([\d.E+-]+)\s*$')

    def __str__(self):
        ret = ''
        for var in self.variables.values():
            ret += '%s: %s\n' % (var, self.name)
        return ret
    
    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return self.name == other.name \
               and set(self.variables.keys()) == set(other.variables.keys()) \
               and all([self.variables[k] == other.variables[k]
                        for k in self.variables.keys()])
    
    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        return {v:self.variables[v].compute_diff(ref.variables[v])
                for v in self.variables.keys()}
    
    def maxdiff(self, ref):
        """Compute and sort out the maximum difference."""
        diff = self.compute_diff(ref)
        return {p:{sp:max([0.] + [abs(diff[v][p][sp])
                                  for v in self.variables.keys()])
                   for sp in ('diff', 'reldiff')}
                for p in ('n', 'jo', 'jo/n')}
    
    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout):
        '''
        Print the summary of the difference between two sensors

        The JoTablesMismatchError exception may be raised if the reference
        object to compare to (ref) doesn't have the same structure.

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        '''
        _write_n(out, '  %s' % (self.name))
        if set(self.variables.keys()) != set(ref.variables.keys()):
            raise JoTablesMismatchError('Incompatible set of variables')
        for vname in self.variables.keys():
            self.variables[vname].print_diff(ref.variables[vname],
                                             bw=bw,
                                             nthres=nthres,
                                             jothres=jothres)

    def parse_line(self, line):
        '''
        Process one line of the listing file

        :param line: One line of the listing (as a string)
        '''
        mres = self._re_var.match(line)
        if mres:
            var = JoVariable(*mres.groups())
            self.variables[var.name] = var


class JoVariable(object):
    def __init__(self, name, n, jo, jon, obserr, bgerr):
        '''
        Object containing one variable

        :param name: Name of the variable
        :param n: Number of obs
        :param jo: Jo
        :param jon: Jo/N
        :param obserr: Observation Error
        :param bgerr: Background Error
        '''
        self.name = name
        self.n = int(n)
        self.jo = float(jo)
        self.obserr = float(obserr)
        self.bgerr = float(bgerr)
    
    def __str__(self):
        return '  %8d  %15.2f  %10.4f  %10.2e %10.2e    %3s' % \
                (self.n, self.jo, self.jo / self.n, self.obserr, self.bgerr,
                 self.name)
    
    def __eq__(self, other):
        assert isinstance(other, self.__class__)
        return all([self.__getattribute__(a) == other.__getattribute__(a)
                    for a in ('name', 'n', 'jo', 'obserr', 'bgerr')])

    @property
    def jon(self):
        """Jo/N"""
        return self.jo / float(self.n)
    
    def compute_diff(self, ref):
        """Compute difference and relative difference for n, jo, jo/n."""
        return {'n':dict(zip(('diff', 'reldiff'),
                             _compute_diff(self.n, ref.n))),
                'jo':dict(zip(('diff', 'reldiff'),
                             _compute_diff(self.jo, ref.jo))),
                'jo/n':dict(zip(('diff', 'reldiff'),
                             _compute_diff(self.jon, ref.jon)))}
    
    def print_diff(self, ref,
                   nthres=DEFAULT_N_THRESHOLD,
                   jothres=DEFAULT_JO_THRESHOLD,
                   bw=False,
                   out=sys.stdout):
        '''

        Print the summary of the difference between two variables

        :param ref: Reference objet (to be compared to)
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag
        '''
        _write_n(out, ('    Obscount   Exp: %15d  Ref: %15d  ' + \
                       'Diff: %15d  RelDiff: %s%12.9f%s  (Var: %s)') % \
                       (_chk_diff(self.n, ref.n, nthres, bw) + (self.name,))
                 )
        _write_n(out, ('    Jo         Exp: %15.2f  Ref: %15.2f  ' + \
                       'Diff: %15.2f  RelDiff: %s%12.9f%s  (Var: %s)') % \
                       (_chk_diff(self.jo, ref.jo, jothres, bw) + (self.name,))
                 )
        if self.obserr != ref.obserr:
            _write_n(out, ('    ObsErr     Exp: %15.6e  Ref: %15.6e  ' + \
                           'Diff: %15.6e  RelDiff: %s%12.9f%s  (Var: %s)') % \
                           (_chk_diff(self.obserr, ref.obserr, 0, bw) + (self.name,))
                     )
        if self.bgerr != ref.bgerr:
            _write_n(out, ('    BgErr      Exp: %15.6e  Ref: %15.6e  ' + \
                           'Diff: %15.6e  RelDiff: %s%12.9f%s  (Var: %s)') % \
                           (_chk_diff(self.bgerr, ref.bgerr, 0, bw) + (self.name,))
                     )
