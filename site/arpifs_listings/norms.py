#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import sys
import collections
import re

from .util import (read_listing,
                   number_of_different_digits,
                   find_line_containing,
                   re_for_fortran_scientific_format,
                   re_for_nan,
                   ParsingError,
                   PARSING_ERROR_CODE,
                   FOUND_NAN_ERROR_CODE,
                   get_worst)

#: Automatic export
__all__ = ['Norms', 'Norm', 'NormsComparison', 'compare_norms']

patterns = {'spectral norms': 'SPECTRAL NORMS -',
            'gpnorms partA': 'GPNORM',
            'gpnorms partB': 'GPNORMS OF FIELDS TO BE WRITTEN OUT ON FILE :',
            'fullpos gpnorms': 'FULL-POS GPNORMS', }
_re_openfa = '(?P<subroutine>OPENFA)'
_re_cnt34 = '(?P<subroutine>CNT[3-4]((TL)|(AD))*)'
_re_comment = '(?P<comment>(\s\w+)+)'
_re_unit = '(?P<unit>\d+)'
_re_filename = '(?P<filename>(\w|\+)+)'
_re_nstep = '(?P<nstep>\d+)'
_re_stepo = '(?P<subroutine>STEPO((TL)|(AD))*)'
_re_scan2m = '(?P<subroutine>SCAN2M((TL)|(AD))*)'
_re_nsim4d = '(?P<nsim4d>\d+)'
_re_cdconf = '(?P<cdconf>\w+)'
_re_pcstep = '(\((?P<pc_step>(PREDICTOR)|(CORRECTOR))\)\s+)?'
_re_dfi = '(?P<dfi>DFI STEP)'
_re_dfistep = '(?P<dfi_step>(\+|\-)\d+\/\s*\d+)'
CNT_steps = {'openfa_info': '\s*' + _re_openfa + ':' + _re_comment + '\s*$',
             'openfa': '\s*' + _re_openfa + ':\s+' + _re_unit + '\s+' + _re_filename + '\s*$',
             'nstep_stepo': '\s*NSTEP =\s+' + _re_nstep + '\s+' + _re_stepo + '\s+' + _re_cdconf + '\s*$',
             'nstep_scan2m': '\s*NSTEP =\s+' + _re_nstep + '\s+' + _re_scan2m + '\s+' + _re_cdconf + '\s*$',
             'norms_at_nstep': '\s*NORMS AT NSTEP\s+' + _re_cnt34 + '\s+' + _re_pcstep + _re_nstep + '\s*$',
             'start_cnt4_nsim4d': '\s*START\s+' + _re_cnt34 + ', NSIM4D=\s+' + _re_nsim4d + '\s*$',
             'end_cnt3': '\s*END\s+' + _re_cnt34 + '\s*$',
             'dfi_step': '\s*(\d|:)*\s+' + _re_dfi + '\s+' + _re_dfistep + '\s*\+CPU=.*\s*$',
             }
CNT_steps = {k: re.compile(v) for k, v in CNT_steps.items()}


class NormsSet(object):
    """
    Handling several Norm objects at different steps.
    """

    def __init__(self, source):
        """
        :param source: may be either a filename or a list of lines.
        """
        self.norms_at_each_step = []
        self.steps_linerecord = []
        self._parse_listing(source)

    def __getitem__(self, item):
        return self.norms_at_each_step[item]

    def __len__(self):
        return len(self.norms_at_each_step)

    def __iter__(self):
        for n in self.norms_at_each_step:
            yield n

    def __eq__(self, other):
        return (len(self) == len(other) and
                all([self.norms_at_each_step[i] == other.norms_at_each_step[i]
                     for i in range(len(self))])
                )

    def pop(self, i):
        self.norms_at_each_step.pop(i)
        self.steps_linerecord.pop(i)

    def steps(self):
        return [self.norms_at_each_step[i].step for i in range(len(self))]

    def steps_equal(self, other):
        """Check if all of the steps in self are equals to the one in other."""
        return (len(self) == len(other) and
                all([self.norms_at_each_step[i].step == other.norms_at_each_step[i].step
                     for i in range(len(self))])
                )

    def _parse_listing(self, source):
        """
        Parse a listing (either given as its filename or already read as a
        list of lines) looking for norms.
        """
        lines = read_listing(source)
        # find CNT steps
        steps = []
        for i, l in enumerate(lines):
            for v in CNT_steps.values():
                _re = v.match(l)
                if _re:
                    s = _re.groupdict()
                    s['line'] = _re.string
                    s['lineno'] = i
                    steps.append(s)
                    break
        nsim4d = None
        nstep = None
        for s in steps:
            nsim4d = s.get('nsim4d', nsim4d)
            nstep = s.get('nstep', nstep)
            s['nsim4d'] = nsim4d
            s['nstep'] = nstep

        # look for norms at each step
        for i in range(len(steps)):
            lineno = steps[i].pop('lineno')
            i0 = lineno
            if i == len(steps) - 1:  # last one
                i1 = -1
            else:
                i1 = steps[i + 1]['lineno']
            extract = lines[i0:i1]
            norm = Norms(steps[i], extract)
            if not norm.empty:
                self.norms_at_each_step.append(norm)
                self.steps_linerecord.append(lineno)


class Norms(object):
    """
    Handling of fields norms at one moment/step.
    """

    def __init__(self, step, lines):
        """
        **step**: identification of the step of norms printing
        """
        self.step = step
        self.spnorms = {}
        self.gpnorms = {}
        self._parse_norms(lines)

    @property
    def empty(self):
        """Return True if no norm has been found."""
        return self.spnorms == self.gpnorms == {}

    @property
    def found_NaN(self):
        return (any([re_for_nan.match(str(v)) for v in self.spnorms.values()]) or
                any([re_for_nan.match(str(v)) for v in self.gpnorms.values()]))

    def format_step(self, complete=False):
        """Return a formatted string describing the step."""
        if complete:
            line = ''
            for k in sorted(self.step.keys()):
                line += '{}: {}\n'.format(k, self.step[k])
            line.rstrip('\n')
        else:
            if self.step.get('dfi'):
                line = '{}={}'.format(self.step.get('dfi'),
                                      self.step.get('dfi_step'))
            else:
                line = '(NSIM4D={}, subroutine={}, NSTEP={}'.format(self.step['nsim4d'],
                                                                    self.step['subroutine'],
                                                                    self.step['nstep'])
                if 'cdconf' in self.step.keys():
                    line += ', CDCONF={})'.format(self.step['cdconf'])
                elif 'pc_step' in self.step.keys():
                    line += ' ({}))'.format(self.step['pc_step'])
                elif 'filename' in self.step.keys():
                    line += ', FILENAME={})'.format(self.step['filename'])
                else:
                    line += ')'
        return line

    def _parse_norms(self, lines):
        self._parse_spectral_norms(lines)
        self._parse_gridpoint_norms(lines)

    def _parse_spectral_norms(self, lines):
        """Parse spectral norms from the subset of lines of the listing."""
        (index, line) = find_line_containing(patterns['spectral norms'], lines)
        if index is not None:  # check that the header for spectral norms is found
            lines = lines[index:index + 5]
            for fld in ('LOG(PREHYDS)', 'OROGRAPHY', 'VORTICITY', 'DIVERGENCE',
                        'TEMPERATURE', 'KINETIC ENERGY', 'LOG(PRE/PREHYD)',
                        'd4 = VERT DIV + X'):
                (idx, line) = find_line_containing(fld, lines)
                if idx is not None:  # fld is found
                    line = line.split()
                    if fld in ('LOG(PREHYDS)', 'OROGRAPHY'):
                        # special case syntax, in line: LOG(PREHYDS)    0.114714299839506E+02
                        val = line[line.index(fld) + 1]
                    else:  # other fields, line below
                        if lines[idx + 1].split()[0] != 'AVE':
                            print(lines[idx])
                            print(lines[idx + 1])
                            raise NotImplementedError('spectral norms level by level.')
                        else:
                            val = lines[idx + 1].split()[line.index(fld.split()[0])]  # .split()[0] necessary for KINETIC ENERGY
                    self.spnorms[fld] = val

    def _parse_gridpoint_norms(self, lines):
        """Parse gridpoint norms from the subset of lines of the listing."""
        self._parse_gridpoint_normsA(lines)
        self._parse_gridpoint_normsB(lines, patterns['gpnorms partB'])
        self._parse_gridpoint_normsB(lines, patterns['fullpos gpnorms'])

    def _parse_gridpoint_normsA(self, lines):
        """
        Parse gridpoint norms (syntax A) from the subset of lines of the
        listing.
        <
         GPNORM INPRRTOT3D           AVERAGE               MINIMUM               MAXIMUM
         AVE   0.000000000000000E+00 0.000000000000000E+00 0.000000000000000E+00
        >
        or
        <
         VCLIA
         GPNORM OUTPUT               AVERAGE               MINIMUM               MAXIMUM
                 AVE   0.284677941566266E-01 0.708309967491275E-04 0.383371754876028E+00
                     1 0.479979959947617E-02 0.227016440704539E-03 0.156422521457101E-01
                     2 0.472130217943848E-01 0.288189754479976E-02 0.162924497411374E+00
                     3 0.444286625411190E-02 0.708309967491275E-04 0.330966742800443E-01
                     4 0.574154889785337E-01 0.458164762144005E-03 0.383371754876028E+00
        >
        """
        start = 0
        sub_extract = lines
        while True:
            sub_extract = sub_extract[start:]
            (idx, line) = find_line_containing(patterns['gpnorms partA'], sub_extract)
            if idx is not None and line.split()[0] == patterns['gpnorms partA']:  # signature of part A
                fld = line.split()[1]
                if fld == 'OUTPUT':
                    if idx <= 0:
                        raise NotImplementedError()
                    else:
                        fld = sub_extract[idx - 1].strip()
                vals = {'average': sub_extract[idx + 1].split()[1],
                        'minimum': sub_extract[idx + 1].split()[2],
                        'maximum': sub_extract[idx + 1].split()[3]}
                start = idx + 1
                self.gpnorms[fld] = vals
            else:
                break

    def _parse_gridpoint_normsB(self, lines, pattern):
        """
        Parse gridpoint norms (syntax B) from the subset of lines of the
        listing.
        <
         **pattern**
                                           AVERAGE               MINIMUM               MAXIMUM
         SURFTEMPERATURE /FRANX01 : 0.282008581801065E+03 0.264749393516486E+03 0.293120673364284E+03
         >
        """
        re_float = re_for_fortran_scientific_format.pattern
        re_pattern = re.compile('\s+(?P<fldname>([\w\.\/\s])+) :' +
                                ' (?P<ave>' + re_float + ')' +
                                ' (?P<min>' + re_float + ')' +
                                ' (?P<max>' + re_float + ')' + '$')
        start = 0
        sub_extract = lines
        while True:
            sub_extract = sub_extract[start:]
            (idx, _) = find_line_containing(pattern, sub_extract)
            if idx is not None:
                idx += 2
                while idx < len(sub_extract):
                    re_ok = re_pattern.match(sub_extract[idx])
                    if re_ok:
                        fld = re_ok.group('fldname').rstrip()
                        vals = {'average': re_ok.group('ave'),
                                'minimum': re_ok.group('min'),
                                'maximum': re_ok.group('max')}
                        self.gpnorms[fld] = vals
                        idx += 1
                    else:
                        break
                start = idx
            else:
                break

    def __eq__(self, other):
        return all([getattr(self, a) == getattr(other, a)
                    for a in ('step', 'spnorms', 'gpnorms')])


class NormsComparison(object):
    """
    Handling of the differences between two Norm objects.
    """

    def __init__(self, test_norm, ref_norm, only=None):
        """

        **test_norm** and **ref_norm** supposed to be of type Norm.

        If **only** among ('spectral', 'gridpoint'), only compare the requested
        type of norms.
        """
        assert isinstance(test_norm, Norms)
        assert isinstance(ref_norm, Norms)

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
            all_ = list(self.sp_comp.values()) + list(self.gp_comp.values())
        elif ntype == 'spectral':
            all_ = list(self.sp_comp.values())
        elif ntype == 'gridpoint':
            all_ = list(self.gp_comp.values())
        return get_worst(all_)

    def write(self, out=sys.stdout, onlymaxdiff=False):
        """Write the NormsComparison to **out**."""
        if len(self.sp_comp) > 0:
            out.write('### SPECTRAL NORMS ###\n')
            out.write('######################\n')
            if not onlymaxdiff:
                _write_normcomp(self.sp_comp, out)
            else:
                _write_normcomp_for_field('Worst norm comparison',
                                          self.get_worst('spectral'),
                                          out)
        if len(self.gp_comp) > 0:
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
    """Compare norms of two Norms objects.

    If **only** among ('spectral', 'gridpoint'), only compare the requested
    type of norms.
    """

    comp_spnorms = collections.OrderedDict()
    comp_gpnorms = collections.OrderedDict()
    if only != 'gridpoint':
        # spnorms
        common_flds = set(test_norm.spnorms.keys()).intersection(set(ref_norm.spnorms.keys()))
        for f in sorted(common_flds):
            try:
                comp_spnorms[f] = _compare_spnorm_for(f, test_norm, ref_norm)
            except ParsingError:
                comp_spnorms[f] = PARSING_ERROR_CODE

    if only != 'spectral':
        # gpnorms
        common_flds = set(test_norm.gpnorms.keys()).intersection(set(ref_norm.gpnorms.keys()))
        for f in sorted(common_flds):
            try:
                comp_gpnorms[f] = _compare_gpnorm_for(f, test_norm, ref_norm)
            except ParsingError:
                comp_gpnorms[f] = PARSING_ERROR_CODE

    return (comp_spnorms, comp_gpnorms)


def _compare_spnorm_for(field, test_norm, ref_norm):
    """Compare spectral norms of two Norm objects for **field**."""
    assert isinstance(test_norm, Norms)
    assert isinstance(ref_norm, Norms)
    return number_of_different_digits(test_norm.spnorms[field],
                                      ref_norm.spnorms[field])


def _compare_gpnorm_for(field, test_norm, ref_norm):
    """Compare gridpoint norms of two Norm objects for **field**."""
    assert isinstance(test_norm, Norms)
    assert isinstance(ref_norm, Norms)
    norms = {}
    for s in ('average', 'minimum', 'maximum'):
        norms[s] = number_of_different_digits(test_norm.gpnorms[field][s],
                                              ref_norm.gpnorms[field][s])
    digit = max(norms.values())
    return digit


def _write_normcomp_for_field(fieldname, digit, out=sys.stdout):
    """Write **fieldname** and its degree of comparison *digit*."""
    fieldname_width = 30
    digits_len = 2
    arrow = ' --> '
    diffdigits = '{:>{width}} last digits differ'
    unable = '??? unable to compare, check manually ???'
    nan = '!!! Found NaN in norms !!!'
    fmt = arrow + diffdigits
    fmtlen = len(diffdigits.format('', width=digits_len))
    if digit is None or digit == 0:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  ' --> {:=<{width}}'.format('', width=fmtlen))
    elif digit == PARSING_ERROR_CODE:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  ' --> {:<{width}}'.format(unable, width=len(unable)))
    elif digit == FOUND_NAN_ERROR_CODE:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  ' --> {:<{width}}'.format(nan, width=len(nan)))
    else:
        out.write('{:>{width}}'.format(fieldname, width=fieldname_width) +
                  fmt.format(str(digit), width=digits_len))
    out.write('\n')


def _write_normcomp(comp_norm, out=sys.stdout):
    assert isinstance(comp_norm, dict)
    for f, d in comp_norm.items():
        _write_normcomp_for_field(f, d, out)
