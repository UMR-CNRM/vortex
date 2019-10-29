#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utility classes to read write and convert VarBC FILES"""

from __future__ import print_function, absolute_import, unicode_literals, division
import numpy as np
from collections import namedtuple
import re
from vortex.tools.date import Date

#: No automatic export
__all__ = []

_MyMatchElement = namedtuple('_MyMatchElement', ('element', 'regex'))

class _MyMatchList(object):
    def __init__(self, matches):
        self._matches = matches
        self._reset()
        self._lastmatch = None

    def __get_init(self):
        return self._icurrent == 0
    init = property(__get_init)

    def __get_flush(self):
        return self._icurrent == len(self._matches) - 1
    flush = property(__get_flush)

    def _reset(self):
        self._icurrent = 0
        self._current = self._matches[0]

    def _jump(self):
        self._icurrent += 1
        self._current = self._matches[self._icurrent]

    def match(self, line):
        # New entry starting ?
        self._lastmatch = self._matches[0].regex.match(line)
        if self._lastmatch:  # I'm new: reset
            self._reset()
        else:  # Still procesing the same entry: go on...
            self._lastmatch = self._current.regex.match(line)
        return self._lastmatch

    def assign(self, entry):
        if self._current.element:
            setattr(entry, self._current.element, self._lastmatch.group(1))
        if self.flush:
            self._reset()
        else:
            self._jump()
            
class _ObsVarbcEntry(object):
    '''
    One entry of a VarBC file
    '''
    def __init__(self):
        self.type = ''
        self.key = ''
        self.ix=''
        self.__ndata = -9999
        self.__npred = 0
        self.__predcs = np.array((), dtype=np.uint8)
        self.__params = np.array((), dtype=np.float32)

    def __set_ndata(self, string):
        self.__ndata = int(string)

    def __get_ndata(self):
        return self.__ndata
    ndata = property(__get_ndata, __set_ndata, "Number of data")

    def __set_npred(self, string):
        self.__npred = int(string)

    def __get_npred(self):
        return self.__npred
    npred = property(__get_npred, __set_npred, "Number of predictors")

    def __set_predcs(self, input1):
        if isinstance(input1, str):
            self.__predcs = [np.uint8(st) for st in input1.split()]
            self.__predcs = np.array(self.__predcs, dtype=np.uint8)
        else:
            self.__predcs = input1

    def __get_predcs(self):
        return self.__predcs
    predcs = property(__get_predcs, __set_predcs, "Predictors list")

    def __set_params(self, input1):
        if isinstance(input1, str):
            self.__params = [np.float32(st) for st in input1.split()]
            self.__params = np.array(self.__params, dtype=np.float32)
        else:
            self.__params = input1

    def __get_params(self):
        return self.__params
    params = property(__get_params, __set_params, "Coefficient list")

    def __repr__(self):
        return '%s(type: %s, ix= %s, key= %s, ndata= %d, npred= %d)' % (
            self.__class__.__name__,
            self.type, self.ix, self.key, self.ndata, self.npred)

    def __str__(self):
        return ('%s\n  preds = %s\n  params= %s' %
                (self.__repr__(),
                 ' '.join(['%7d' % (n,) for n in self.predcs]),
                 ' '.join(['%7.3f' % (x,) for x in self.params])))

    def __eq__(self, other):
        return (self.key == other.key and self.type == other.type and
                self.ndata == other.ndata and self.npred == other.npred and
                np.alltrue(self.predcs == other.predcs) and
                np.alltrue(self.params == other.params))

    def __ne__(self, other):
        return not self == other

    def valid(self):
        return (len(self.__predcs) == self.npred and
                len(self.__params) == self.npred and
                self.key and self.type)
        
        
class ObsVarbcFileContent(object):      
        
    def __init__(self,asciiDatas=None,filepath=None):
        self.metadata = {}
        self.datalist=[] #datalist[i] for entry ix=i+1
        self.keyToIx={}  #keyToIx[222 3 9] return the ix of the line
        
        if filepath is not None and asciiDatas is None:
            f=open(filepath,'r')
            asciiDatas=f.readlines()
            f.close()
            
        elif filepath is None and asciiDatas is not None:
            print("ascii data is given")
        else:
            raise Exception("only one argument between asciiDatas or filepath must be provided. Stop")
        
            
        
        mobj = re.match(r'\w+\.version(\d+)', asciiDatas[0])
        if mobj:
            self.metadata['version'] = int(mobj.group(1))
            # Then we fetch the date of the file
            mobj = re.match(r'\s*\w+\s+(\d{8})\s+(\d+)', asciiDatas[1])
            if mobj:
                self.metadata['date'] = Date('{:s}{:06d}'.format(mobj.group(1),
                                                         int(mobj.group(2))))
                         
        mymatchlist = _MyMatchList([
            _MyMatchElement('ix', re.compile('^ix=0*(\d+)$')),
            _MyMatchElement('type', re.compile('^class=(\w+)$')),
            _MyMatchElement('key', re.compile('^key=\s*([^=]+)\n$')),
            _MyMatchElement('ndata', re.compile('^ndata=(\d+)$')),
            _MyMatchElement('npred', re.compile('^npred=(\d+)$')),
            _MyMatchElement('predcs', re.compile('^predcs=([\d ]+)$')),
            _MyMatchElement('params',re.compile('^params=([\dEe+-. ]+)$')), ])
        
        for myline in asciiDatas:
            if mymatchlist.match(myline):
                # New entry ?
                if mymatchlist.init:
                    myentry = _ObsVarbcEntry()
                # Save the entry end save it if appropriate
                flush = mymatchlist.flush
                mymatchlist.assign(myentry)
                if flush and myentry.valid():
                    if myentry.ix == len(self.datalist)+1:
                        raise Exception('problem!! varbcfile unordered',myentry.ix,len(self.datalist)+1)
                    else:
                        self.datalist.append(myentry)
                        self.keyToIx[myentry.key]=int(myentry.ix)
        
    def getIx(self,ix):
        return self.datalist[ix-1]

    def getKey(self,key):
        return self.getIx(self.keyToIx[key])       
