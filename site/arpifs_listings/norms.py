#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import six
import sys
import collections

from .util import diverging_digit, get_maxint, find_line_containing

#: Automatic export
__all__ = ['Norms', 'Norm', 'NormComparison', 'compare_norms']

patterns = {'norms': 'NORMS AT NSTEP CNT4',
            'spectral norms': 'SPECTRAL NORMS -',
            'gpnorms partA': 'GPNORM',
            'gpnorms partB': 'GPNORMS OF FIELDS TO BE WRITTEN OUT ON FILE :',
            'fullpos gpnorms': 'FULL-POS GPNORMS', }


class Norms(object):
    """
    Handling several Norm objects at different step/substep.
    """

    def __init__(self, source):
        """

        :param source: may be either a filename or a list of lines.
        """
        self.norms = collections.OrderedDict()
        self._parse_listing(source)

    def __getitem__(self, item):
        return self.norms[item]

    def __len__(self):
        return len(self.norms)

    def __eq__(self, other):
        return (list(self.norms.keys()) == list(other.norms.keys()) and
                all([self[k] == other[k] for k in self.norms.keys()])
                )

    def subset_equal(self, other):
        """Check if all of the steps in self are equals to the one in other."""
        return (set(other.norms.keys()) >= set(self.norms.keys()) and
                all([self[k] == other[k] for k in self.norms.keys()])
                )

    def steps(self):
        return self.norms.keys()

    def get_first_and_last_norms_indexes(self, **kw):
        """Return the first and last indexes of norms."""
        if len(self.norms) == 0:
            self._parse_listing(**kw)
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

    def _parse_listing(self, source):
        """
        Parse a listing (either given as its filename or already read as a
        list of lines) looking for norms.
        """

        if isinstance(source, list):
            lines = source
        elif isinstance(source, six.string_types):
            with open(source, 'r') as listfh:
                lines = [l.rstrip("\n") for l in listfh]

        _indexes_of_found_norms = []
        for i, line in enumerate(lines):
            if patterns['norms'] in line:
                _indexes_of_found_norms.append(i)
        _indexes_of_found_norms.append(-1)  # for last interval

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

        # gridpoint norms
        def gpnorms_syntaxA(extract, norm):
            start = 0
            sub_extract = extract
            while True:
                sub_extract = sub_extract[start:]
                (idx, line) = find_line_containing(patterns['gpnorms partA'], sub_extract)
                if idx is not None and line.split()[0] == patterns['gpnorms partA']:  # signature of part A
                    fld = line.split()[1]
                    vals = {'average': sub_extract[idx + 1].split()[1],
                            'minimum': sub_extract[idx + 1].split()[2],
                            'maximum': sub_extract[idx + 1].split()[3]}
                    start = idx + 1
                    norm.gpnorms[fld] = vals
                else:
                    break

        def gpnorms_syntaxB(extract, norm, pattern, colon_position):
            start = 0
            sub_extract = extract
            while True:
                sub_extract = sub_extract[start:]
                (idx, _) = find_line_containing(pattern, sub_extract)
                if idx is not None:
                    idx += 2
                    while (len(sub_extract[idx]) > colon_position and
                           sub_extract[idx][colon_position] == ':'):
                        [fld, vals] = sub_extract[idx].split(':')
                        fld = fld.strip()
                        vals = {'average': vals.split()[0],
                                'minimum': vals.split()[1],
                                'maximum': vals.split()[2]}
                        norm.gpnorms[fld] = vals
                        idx += 1
                    start = idx
                else:
                    break

        # loop on nstep + substep
        for i in range(len(_indexes_of_found_norms) - 1):
            # extract of output in which to look for
            index = _indexes_of_found_norms[i]
            index_p_1 = _indexes_of_found_norms[i + 1]  # last interval finishes at index -1
            _extract = lines[index:index_p_1]
            # pattern line has syntax: "NORMS AT NSTEP CNT4 (<substep>)    <nstep>"
            # get nstep and substep
            nstep = int(lines[index].split()[-1])
            substep = None
            for ss in ('PREDICTOR', 'CORRECTOR'):
                if ss in lines[index]:
                    substep = ss
                    break
            _norm = Norm(nstep, substep=substep)

            # process
            for fld in ('LOG(PREHYDS)', 'OROGRAPHY', 'VORTICITY', 'DIVERGENCE',
                        'TEMPERATURE', 'KINETIC ENERGY', 'LOG(PRE/PREHYD)',
                        'd4 = VERT DIV + X'):
                _val = getspnorm(fld, _extract)
                if _val is not None:
                    _norm.spnorms[fld] = _val
            gpnorms_syntaxA(_extract, _norm)
            gpnorms_syntaxB(_extract, _norm, patterns['gpnorms partB'], 18)
            gpnorms_syntaxB(_extract, _norm, patterns['fullpos gpnorms'], 26)

            # save
            if _norm.nstep not in self.norms.keys():
                self.norms[_norm.nstep] = {_norm.substep: _norm}
            else:
                self.norms[_norm.nstep][_norm.substep] = _norm


class Norm(object):
    """
    Handling of fields norms at one time step.

    example:
    ::

        Norm.spnorms: {'TEMPERATURE':'0.256351366366780E+03',
                       ...}
        Norm.gpnorms: {'TEMPERATURE':{'average':'0.256351366366780E+03',
                                      'minimum': ...}
                       ...}
    """
    def __init__(self, nstep, substep=None):
        """
        **nstep**: number of the time step

        **substep**: in case, PREDICTOR or CORRECTOR substep
        """
        self.nstep = nstep
        self.substep = substep
        self.spnorms = {}
        self.gpnorms = {}

    def __eq__(self, other):
        return all([getattr(self, a) == getattr(other, a)
                    for a in ('nstep', 'substep', 'spnorms', 'gpnorms')])


class NormComparison(object):
    """
    Handling of the differences between two Norm objects.
    """

    def __init__(self, test_norm, ref_norm, only=None):
        """

        **test_norm** and **ref_norm** supposed to be of type Norm.

        If **only** among ('spectral', 'gridpoint'), only compare the requested
        type of norms.
        """
        assert isinstance(test_norm, Norm)
        assert isinstance(ref_norm, Norm)

        self.test_norm = test_norm
        self.ref_norm = ref_norm
        self.only = only

        self._compare()

    def _compare(self):
        """Compute comparisons."""
        self.sp_comp, self.gp_comp = compare_norms(self.test_norm,
                                                   self.ref_norm,
                                                   self.only)

    def get_worst(self, ntype='both'):
        """
        Get the worst of either 'spectral' or 'gridpoint' norm comparison.
        Or worst of the worst of 'both'.
        """
        if ntype == 'both':
            worst = get_maxint({'spectral': get_maxint(self.sp_comp),
                                'gridpoint': get_maxint(self.gp_comp)})
        elif ntype == 'spectral':
            worst = get_maxint(self.sp_comp)
        elif ntype == 'gridpoint':
            worst = get_maxint(self.gp_comp)
        return worst

    def write(self, out=sys.stdout, onlymaxdiff=False):
        """Write the NormComparison to **out**."""
        if len(self.sp_comp) > 0:
            out.write('### SPECTRAL NORMS ###\n')
            out.write('######################\n')
            if not onlymaxdiff:
                _write_normcomp(self.sp_comp, out)
            else:
                _write_normcomp_for_field('Worst norm comparison',
                                          self.get_worst('spectral'),
                                          out)
        if len(self.sp_comp) > 0:
            out.write('### GRIDPOINT NORMS ###\n')
            out.write('######################\n')
            if not onlymaxdiff:
                _write_normcomp(self.gp_comp, out)
            else:
                _write_normcomp_for_field('Worst norm comparison',
                                          self.get_worst('gridpoint'),
                                          out)


###################
# INNER FUNCTIONS #############################################################
###################
def compare_norms(test_norm, ref_norm, only=None):
    """Compare norms of two Norm objects.

    If **only** among ('spectral', 'gridpoint'), only compare the requested
    type of norms.
    """

    comp_spnorms = collections.OrderedDict()
    comp_gpnorms = collections.OrderedDict()
    if only != 'gridpoint':
        # spnorms
        common_flds = set(test_norm.spnorms.keys()).intersection(set(ref_norm.spnorms.keys()))
        for f in sorted(common_flds):
            comp_spnorms[f] = _compare_spnorm_for(f, test_norm, ref_norm)

    if only != 'spectral':
        # gpnorms
        common_flds = set(test_norm.gpnorms.keys()).intersection(set(ref_norm.gpnorms.keys()))
        for f in sorted(common_flds):
            comp_gpnorms[f] = _compare_gpnorm_for(f, test_norm, ref_norm)

    return (comp_spnorms, comp_gpnorms)


def _compare_spnorm_for(field, test_norm, ref_norm):
    """Compare spectral norms of two Norm objects for **field**."""
    assert isinstance(test_norm, Norm)
    assert isinstance(ref_norm, Norm)
    return diverging_digit(test_norm.spnorms[field],
                           ref_norm.spnorms[field])


def _compare_gpnorm_for(field, test_norm, ref_norm):
    """Compare gridpoint norms of two Norm objects for **field**."""
    assert isinstance(test_norm, Norm)
    assert isinstance(ref_norm, Norm)
    norms = {}
    for s in ('average', 'minimum', 'maximum'):
        norms[s] = diverging_digit(test_norm.gpnorms[field][s],
                                   ref_norm.gpnorms[field][s])
    if all([v is None for v in norms.values()]):
        digit = None
    elif '?' in norms.values():
        digit = '?'
    else:
        digit = min([v for v in norms.values() if v is not None])
    return digit


def _write_normcomp_for_field(fieldname, digit, out=sys.stdout):
    """Write **fieldname** and its degree of comparison *digit*."""
    fieldname_width = 30
    digits_len = 2
    arrow = ' --> '
    idupto = 'identical up to {:>{width}} digits'
    unable = '??? unable to compare, check manually ???'
    fmt = arrow + idupto
    fmtlen = len(idupto.format('', width=digits_len))
    if digit is None:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  ' --> {:=<{width}}'.format('', width=fmtlen))
    elif digit == '?':
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  ' --> {:<{width}}'.format(unable, width=len(unable)))
    else:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  fmt.format(str(digit), width=digits_len))
    out.write('\n')


def _write_normcomp(comp_norm, out=sys.stdout):
    assert isinstance(comp_norm, dict)
    for f, d in comp_norm.items():
        _write_normcomp_for_field(f, d, out)
