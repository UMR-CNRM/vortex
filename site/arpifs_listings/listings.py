#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from .norms import Norm, NormComparison


class OutputListing(object):
    """Handling of a model configuration output listing."""
    
    patterns = {'end_is_reached':'*** END CNT0 ***',
                'norms':'NORMS AT NSTEP CNT4',
                'spectral norms':'SPECTRAL NORMS -',
                'gpnorms partA':'GPNORM',
                'gpnorms partB':'GPNORMS OF FIELDS TO BE WRITTEN OUT ON FILE :',
                'fullpos gpnorms':'FULL-POS GPNORMS',
                'Jo-tables':None
                }
    
    def __init__(self, filename, pattern_type):
        """
        **filename**: name of the file to read in
        
        **pattern_type**: type of pattern to compare,
                          among ('norms', 'Jo-tables')
        """
        assert pattern_type in ('norms', 'Jo-tables')
        
        # init
        self.filename = filename
        self.pattern_type = pattern_type
        self.end_is_reached = False
        self.norms = {}
        self.jo_tables = {}
            
        # read listing in file
        with open(self.filename, 'r') as f:
            lines = f.readlines()
        self.lines = [l[:-1] for l in lines]  # :-1 to remove trailing '\n'
        del lines
    
    def __len__(self):
        return len(self.lines)
    
    def look_for_end(self):
        """Is the end reached in listing ?""" 
        for line in self.lines:
            if self.patterns['end_is_reached'] in line:
                self.end_is_reached = True
                break
        return self.end_is_reached
    
    @property
    def patterns_number(self):
        if self.pattern_type == 'norms':
            n = len(self.norms)
        elif self.pattern_type == 'Jo-tables':
            n = len(self.jo_tables)
        return n
    
    def parse_patterns(self, flush_after_reading=False):
        """
        Look for and read each pattern instance.
        
        If **flush_after_reading**, get rid of listing after reading patterns.
        """
        if self.pattern_type == 'norms':
            self.parse_norms(flush_after_reading=flush_after_reading)
        elif self.pattern_type == 'Jo-tables':
            self.parse_jo_tables(flush_after_reading=flush_after_reading)
    
    def flush_listing(self):
        """Get rid of the text listing, which may take some memory."""
        self.lines = ['' for _ in range(len(self))]
    
    # norms
    def parse_norms(self, flush_after_reading=False):
        """
        Look for and read each norms instance.
        The recognition of Norms patterns and parsing of their values is the
        most tricky part of this class.
        The most subject to maintenance too...
        
        If **flush_after_reading**, get rid of listing after reading norms.
        """
        from .util import find_line_containing
        
        _indexes_of_found_norms = []
        for i in range(len(self)):
            if self.patterns['norms'] in self.lines[i]:
                _indexes_of_found_norms.append(i)
        _indexes_of_found_norms.append(-1)  # for last interval

        #loop on nstep+substep
        for i in range(len(_indexes_of_found_norms) - 1):
            # extract of output in which to look for
            index = _indexes_of_found_norms[i]
            index_p_1 = _indexes_of_found_norms[i + 1]  # last interval finishes at index -1
            _extract = self.lines[index:index_p_1]
            # pattern line has syntax: "NORMS AT NSTEP CNT4 (<substep>)    <nstep>"
            # get nstep and substep
            nstep = int(self.lines[index].split()[-1])
            substep = None
            for ss in ('PREDICTOR', 'CORRECTOR'):
                if ss in self.lines[index]:
                    substep = ss
                    break
            _norm = Norm(nstep, substep=substep)

            # spectral norms
            def getspnorm(fld, extract):
                val = None
                (idx, line) = find_line_containing(fld, extract)
                line = line.split()
                if fld in ('LOG(PREHYDS)', 'OROGRAPHY'):
                    # special case syntax
                    if idx is not None:  # fld is found
                        try:
                            val = line[line.index(fld) + 1]
                        except ValueError:
                            val = None
                else:
                    if idx is not None:  # fld is found
                        if extract[idx + 1].split()[0] != 'AVE':
                            raise NotImplementedError
                        else:
                            val = extract[idx + 1].split()[line.index(fld.split()[0])]  # .split()[0] necessary for KINETIC ENERGY

                return val
            for fld in ('LOG(PREHYDS)', 'OROGRAPHY', 'VORTICITY', 'DIVERGENCE',
                        'TEMPERATURE', 'KINETIC ENERGY', 'LOG(PRE/PREHYD)',
                        'd4 = VERT DIV + X'):
                _val = getspnorm(fld, _extract)
                if _val is not None:
                    _norm.spnorms[fld] = _val

            # gridpoint norms
            def gpnorms_syntaxA():
                start = 0
                sub_extract = _extract
                while True:
                    sub_extract = sub_extract[start:]
                    (idx, line) = find_line_containing(self.patterns['gpnorms partA'], sub_extract)
                    if idx is not None and line.split()[0] == self.patterns['gpnorms partA']:  # signature of part A
                        fld = line.split()[1]
                        vals = {'average':sub_extract[idx + 1].split()[1],
                                'minimum':sub_extract[idx + 1].split()[2],
                                'maximum':sub_extract[idx + 1].split()[3]}
                        start = idx + 1
                        _norm.gpnorms[fld] = vals
                    else:
                        break
            def gpnorms_syntaxB(pattern, colon_position):
                start = 0
                sub_extract = _extract
                while True:
                    sub_extract = sub_extract[start:]
                    (idx, _) = find_line_containing(pattern, sub_extract)
                    if idx is not None:
                        idx += 2
                        while len(sub_extract[idx]) > colon_position and \
                              sub_extract[idx][colon_position] == ':':
                            [fld, vals] = sub_extract[idx].split(':')
                            fld = fld.strip()
                            vals = {'average':vals.split()[0],
                                    'minimum':vals.split()[1],
                                    'maximum':vals.split()[2]}
                            _norm.gpnorms[fld] = vals
                            idx += 1
                        start = idx
                    else:
                        break
            gpnorms_syntaxA()
            gpnorms_syntaxB(self.patterns['gpnorms partB'], 18)
            gpnorms_syntaxB(self.patterns['fullpos gpnorms'], 26)

            # save
            if _norm.nstep not in self.norms.keys():
                self.norms[_norm.nstep] = {_norm.substep:_norm}
            else:
                self.norms[_norm.nstep][_norm.substep] = _norm
        if flush_after_reading:
            self.flush_listing()
    
    def get_first_and_last_norms(self, **kw):
        """Return the first and last indexes of norms."""
        if len(self.norms) == 0:
            self.read_norms(**kw)
        if 'PREDICTOR' in self.norms[0].keys():
            first = (0, ['PREDICTOR'])
        else:
            first = (0, [None])
        last = max(self.norms.keys())
        if 'CORRECTOR' in self.norms[last].keys():
            last = (last, ['CORRECTOR'])
        elif 'PREDICTOR' in self.norms[last].keys():
            last = (last, ['PREDICTOR'])
        else:
            last = (last, [None])
        first_and_last = [first, last]
        return first_and_last
    
    # Jo-tables
    def parse_jo_tables(self, flush_after_reading=False):
        """
        Look for and read each Jo-tables instance.
        The recognition of Jo-tables patterns and parsing of their values is the
        most tricky part of this class.
        The most subject to maintenance too...
        
        If **flush_after_reading**, get rid of listing after reading Jo-tables.
        """
        raise NotImplementedError('not yet.')
    
#############
# FUNCTIONS #
#############
def compare(test, ref, **kwargs):
    """
    Compare two output listings.
    """
    assert test.pattern_type == ref.pattern_type
    if test.pattern_type == 'norms':
        result = compare_norms(test, ref, **kwargs)
    elif test.pattern_type == 'Jo-tables':
        result = compare_jo_tables(test, ref, **kwargs)
    return result

def compare_norms(test, ref,
                  mode='first_and_last',
                  out=sys.stdout,
                  onlymaxdiff=False,
                  printmode='standalone'):
    """
    Compare two 'norms' pattern-type output listings.
    
    **mode**: either 'all' to compare norms for all steps found in listings,
    or 'first_and_last' (default) for the first and last only.
    
    **onlymaxdiff**: only max difference is printed for each step.
    
    **printmode**: if 'standalone', prints the comparison to file;
                   if 'jobs_manager', return the worst digits comparison.
    """

    assert ref.end_is_reached
    assert test.end_is_reached
    assert len(ref.norms) > 0
    assert len(test.norms) > 0

    if mode == 'first_and_last':
        ref_set = ref.get_first_and_last_norms()
        test_set = test.get_first_and_last_norms()
    elif mode == 'all':
        ref_set = [(nstep, sorted(ref.norms[nstep].keys(), reverse=True)) \
                    for nstep in sorted(ref.norms.keys())]
        test_set = [(nstep, sorted(test.norms[nstep].keys(), reverse=True)) \
                    for nstep in sorted(test.norms.keys())]
    assert ref_set == test_set, "set of norms differ between ref and test."

    if printmode == 'jobs_manager':
        worstdigits = []
    for (nstep, subsets) in ref_set:
        for subset in subsets:
            norm_comp = NormComparison(test.norms[nstep][subset],
                                       ref.norms[nstep][subset])
            if printmode == 'standalone':
                nstepline = 'NSTEP = ' + str(nstep)
                if subset is not None:
                    nstepline += ' (' + subset + ')'
                out.write(nstepline + '\n')
                norm_comp.write(out, onlymaxdiff)
                out.write('-' * 80 + '\n')
            elif printmode == 'jobs_manager':
                assert mode == 'first_and_last'
                assert onlymaxdiff is True
                worstdigits.append(norm_comp.get_worst('both'))
    if printmode == 'jobs_manager':
        return worstdigits
    
def compare_jo_tables(test, ref, **kwargs):
    """
    Compare two 'Jo-tables' pattern-type output listings.
    """
    raise NotImplementedError('not yet.')
